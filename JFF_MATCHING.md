# JFF matching & Notion integration — analysis & plan

How to (a) open our data in the client's Notion collection and (b) build the
system that links a **JFF original** to an **abdlhub rehost** by media ID,
thumbnail, caption/body text, and frame fingerprint.

**Navigate:** [`README`](README.md) · [`REPO_MAP`](REPO_MAP.md) · [`HANDOVER`](HANDOVER.md) · [`TODO`](TODO.md)

---

## 1. What the client's manual sheet actually is
Two files ([`manual/abdlhub_stolen_videos_manual.csv`](manual/abdlhub_stolen_videos_manual.csv)
and [`…_all.csv`](manual/abdlhub_stolen_videos_manual_all.csv)) — **same 74 rows**,
just reordered columns/rows; `_all` is not a superset.

| Field | Meaning |
| --- | --- |
| `ABDL Hub Title ` | The title as shown on abdlhub — the operator reused the **original filename** (ends `.mp4`, keeps emoji). |
| `JFF Video ID` | **JustForFans video id** — 24-hex ObjectId (e.g. `67ca7831dbb928eaec22eea4`). The anchor to the original. |
| `Fingerprinted?` | Whether the client already fingerprinted that JFF video. **10 Yes / 63 No / 1 blank.** |
| `Site screenshot` | PNG she saved of the abdlhub page; filename = title (non-alnum → `_`, wrapped in `()`) + `.png`. |
| `Line #` | Sequence from her source; observed **1–77** for 74 rows (3 gaps). |

Measured facts:
- **74 rows → 58 unique JFF IDs** (16 duplicate ids ⇒ **one original rehosted multiple times** — relevant to damages).
- **Data quality:** the `JFF Video ID` column is not clean — at least one row holds a free-text note ("Couldnt find it") instead of an id; the matcher must validate `^[0-9a-f]{24}$` and treat non-matches as unresolved.
- **Only 1 of 74** titles still exists in today's Bunny catalog ⇒ **73 are already delisted** (consistent with our 610/624 orphan rate).
- JFF ids cluster into two ObjectId eras (`...b873869643...`, `...4f57e2ef26...`, `...95c787876f...`), i.e. uploads spanning time.

## 2. Reconciliation with our automated dataset
| | Ours | Hers |
| --- | --- | --- |
| Key | abdlhub **guid** | **JFF Video ID** + title |
| Count | 624 (610 delisted / 14 live) | 74 (73 delisted) |
| Has | URLs (page/media/thumb), captures, uploader attribution, thumbnails | original title, JFF id, fingerprint flag, page screenshots |
| Lacks | JFF id, original caption | guid, URLs |

They are **complementary, not overlapping on titles** — our delisted rows lost
their titles, so a title join fails (0 exact, 1 catalog hit). The **bridge must be
visual/medial**, not textual:

```
her JFF id  ──(JFF media)──►  frame fingerprint  ┐
her title/caption, screenshot ──(pHash/text)──►  ├──► abdlhub guid  ──► our page/media/thumb URLs
                                                ┘
```

So the artifact she brings (JFF id + originals) and the artifact we bring
(guid + rehost URLs) meet in the middle via content matching. A confirmed pair is
the **proof of copying**; the JFF id + original establishes **ownership**.

## 3. Notion integration (fresh import)
Notion maps CSV headers → database properties by name. Her database uses:
`ABDL Hub Title` (Title), `JFF Video ID` (Text), `Fingerprinted?`
(Select/Checkbox), `Site screenshot` (Files), `Line #` (Number).

`notion_export.py` emits [`notion/abdlhub_stolen_videos.csv`](notion/abdlhub_stolen_videos.csv)
— a **union of both datasets in one schema** for a **fresh import** (not an
append), keeping her exact property names for shared fields and adding ours:

| Column | Type | From |
| --- | --- | --- |
| `ABDL Hub Title` | Title | ours (may be blank if delisted) / hers |
| `JFF Video ID` | Text | hers |
| `Fingerprinted?` | Select (Yes/No) | hers |
| `Site screenshot` | Text (filename) | hers |
| `Line #` | Number | hers |
| `GUID` | Text | ours |
| `Abdlhub Page URL` / `Media URL` / `Thumbnail URL` | URL | ours |
| `Upload Date` | Date (ISO) | ours |
| `Uploader` | Text | ours |
| `Status` | Select (Live/Delisted) | ours |
| `Duration (s)` / `Views` | Number | ours |
| `Normalized Title` | Text | derived (dedupe/group key) |
| `Record Source` | Select (Automated/Manual-JFF) | derived |
| `Match Confidence` | Number | filled by the matcher (blank today) |

Schema/import notes are in [`notion/NOTION_SCHEMA.md`](notion/NOTION_SCHEMA.md).
Row count = 624 (ours) + 74 (hers) = 698 initially; duplicates reconcile in
Notion by `Normalized Title` / `GUID` once the matcher fills the GUID column.

## 4. Matching system design
### 4.1 Inputs (staging)
- **JFF originals** (client, authenticated): `jff_video_id`, `caption` (post
  text/body), `published_at`, `thumbnail` (file/url), `media` (file).
- **Her sheet** (this CSV): JFF id ↔ abdlhub title + screenshot.
- **Our evidence**: 624 works with `guid`, page/media/thumbnail URLs, captures,
  and the preserved orphan thumbnails (`captures/thumbs/`).

### 4.2 Signals (weak → strong)
1. **Temporal gate** — JFF `published_at` must precede the abdlhub upload date (hard constraint, reused from `match.py`).
2. **Title / caption text** — normalize (strip `.mp4`, emoji, punctuation) → `SequenceMatcher` ratio + token overlap between (her abdlhub title / JFF caption) and (our catalog title / `video_submissions.description`).
3. **Thumbnail pHash** — compare her site screenshot **and** the JFF thumbnail against our preserved abdlhub thumbnails (DCT pHash, Hamming distance; reuse `match.py`).
4. **Media frame fingerprint (strongest)** — sample frames from the JFF `media` (OpenCV) and from the rehost HLS (downloadable — the AES-128 key is public, see `HANDOVER.md` §4), pHash each, and require a high matched-frame fraction. Survives re-encoding/rescaling.
5. **Duration** — ±2 s agreement (rehost duration is in our catalog).

A pair is **confirmed** when (frame match ≥ threshold) OR (duration + thumbnail + title all strong); otherwise it is a **candidate** for review.

### 4.3 Architecture
```
staging/                 JFF media + thumbnails downloaded (client side)
jff/originals.json       {jff_video_id, caption, published_at, thumbnail, media}
notion/*.csv             client sheet + our union
match.py (existing)      text/duration/pHash primitives  ──► reused
jff_match.py (new)       ingest originals + sheet; fingerprint; emit matches
matches/matches.json     jff_id ↔ guid, confidence, per-signal scores, evidence refs
notion/… (re-export)     GUID / Match Confidence columns filled back in
```
`matches.json` feeds both Notion (fill `GUID`, `Match Confidence`) and the legal
package (Exhibit: matched original ↔ rehost, with hash references).

### 4.4 Frame-matching detail
- Sample ~1 frame/second (or on scene change) from the original; build a pHash set per work.
- Download the rehost HLS to `staging/` (public key) and sample the same way.
- Compare sets by pairwise Hamming distance; report `matched_fraction` and `median_distance`.
- Threshold calibrated on the 10 already-fingerprinted works (ground truth).

### 4.5 Stealth & legality
- Any abdlhub/CDN fetch reuses `PoliteSession`/`HostRateLimiter` (low-and-slow).
- JFF fetches use the client's authenticated session only.
- Staging media is stored with hashes in `evidence/` (or `staging/`, gitignored if large) and timestamped.

## 5. Outputs / data model
```
originals.json  { "works": [ { "jff_video_id", "title", "caption", "published_at",
                               "thumbnail", "media", "sha256" }, … ] }
matches.json    { "results": [ { "jff_video_id", "abdlhub_guid", "confidence",
                                 "signals": {text, thumb, frame, duration},
                                 "evidence": [ … ] }, … ] }
```

## 6. Rollout
1. **Notion import now** — generate [`notion/`](notion/) and import fresh (both datasets in one schema).
2. **Export JFF originals** (client) → `jff/originals.json` (+ media/thumbnails).
3. **Text pass** — coarse candidates (title/caption/description).
4. **Thumbnail pass** — add her screenshots + JFF thumbnails → pHash.
5. **Frame pass** — download rehosts, fingerprint, confirm (calibrate on the 10 fingerprinted works).
6. **Write-back** — fill `GUID`/`Match Confidence`; package matched pairs as an exhibit.

## 7. Open questions
- Does JFF offer bulk metadata/media export, or is it per-post download?
- Will her **site screenshots** be provided as files (needed for the thumbnail pass)?
- Do we download the infringing HLS for frame evidence (adds ~GBs + a preservation decision)?
