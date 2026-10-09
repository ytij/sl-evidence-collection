# Thumbnail preservation — analysis & stealth plan

Preserving the CDN-cached thumbnails of the **610 orphaned works** is
time-sensitive (they can be purged at any time) and is the most
detectability-sensitive collection task in this project. This document
examines it and records the stealth design. Tool: [`preserve_thumbs.py`](preserve_thumbs.py).

**Navigate:** [`README`](README.md) · [`REPO_MAP`](REPO_MAP.md) · [`HANDOVER`](HANDOVER.md) · [`TODO`](TODO.md)

## 1. Objective
Of the 624 matching works, only 14 still stream; **610 have been removed from
the media library** (HLS 404). For those, the database row (already preserved in
`evidence/video_meta.json`) and the **CDN-cached thumbnail** are the only
remaining proof that the work existed at that URL. Preserve the thumbnail bytes
with provenance and hashes.

## 2. Scope (measured, no network)
- Targets: **610** unique guids.
- URL pattern: uniform `https://vz-e81debcf-c73.b-cdn.net/{guid}/thumbnail.jpg?width=480`.
- Fetchable at last probe: ~607–610 (2 returned 404, 1 connection error).
- Size: ~37–95 KB each (observed); **≈30–55 MB total**.
- Live works (14) use hashed filenames (`thumbnail_XXXX.jpg`); the orphans all
  use `thumbnail.jpg`.

## 3. Why this is the hardest stealth case
The orphans are **unreferenced**: because the publish pages were delisted from
the site's grid, *no legitimate visitor ever requests these thumbnails*. There
is no browsing pattern we can blend into — **any** request for an orphaned
asset is anomalous at the origin. Stealth here cannot mean "look normal"; it can
only mean:

1. **Tiny, one-time footprint.** Fetch each orphan exactly once; subsequent runs
   make **zero** requests (incremental manifest).
2. **Spread thin.** No burst; the average rate stays at roughly one image per
   several seconds, and the whole set is split across days.
3. **Individually unremarkable.** Each request carries the headers a real front
   end would send for that image, so a per-request log line looks like an
   ordinary image load — only the *aggregate* could ever look odd.

## 4. Detectability analysis / who sees what
| Party | Sees | Notes |
| --- | --- | --- |
| Bunny CDN edge | Aggregate hits/bandwidth in the dashboard; **per-request logs only if logging is enabled** (log forwarding to S3/third parties is off by default). | The main exposure. 610 extra image requests are trivial in aggregate; risk rises only if detailed logs are on *and* someone reviews orphan-asset access. |
| Netlify (origin) | Nothing — thumbnails never touch the origin. | — |
| Supabase | Nothing. | — |
| Client-side | Nothing (we don't run JS). | — |
| Our IP correlation | The same collector IP also probed the catalog/URLs and captured pages earlier. | Low-and-slow from the start; no bursts. |

**Conclusion:** primary risk is a single-IP burst of orphan-thumbnail requests
if the operator has CDN logging on and reviews it. Mitigate by volume + pacing +
one-time footprint; optionally offload (§7).

## 5. Stealth controls implemented (`preserve_thumbs.py`)
- **Serial** (`workers=1`), per-host pacing `--delay 4.0` s + `--jitter 1.5`
  (up to +150%), and a **30–120 s pause every 20 requests** → effective rate
  ≈ 1 image / 7–12 s (~1.7 h if run in one go).
- Browser-real image request: image `Accept`, `Sec-Fetch-Dest: image`,
  `Sec-Fetch-Mode: no-cors`, `Sec-Fetch-Site: cross-site`, and a
  `Referer` of the work's own page (`https://abdlhub.com/?v={guid}`).
- **Incremental & resumable**: a thumbnail already stored (status 200 + file
  present + hash) is skipped, so re-runs cost **0 requests**.
- **Randomized order** (no sequential pattern); `--max-requests` hard cap.
- `--dry-run` (no traffic) and `--verify` (re-hash stored files).

## 6. Recommended rollout (do NOT run 610 at once)
```
python preserve_thumbs.py --dry-run          # 0 requests
python preserve_thumbs.py --limit 60         # ~10 min; repeat ~once/day for ~10 days
python preserve_thumbs.py --verify           # confirm hashes at any time
python preserve_thumbs.py --include-live     # also snapshot the 14 live works
```
Each run fetches only what remains; total ≈ 610 requests over ~10 short sessions.

## 7. Residual risk & the offload alternative
Because orphan fetches are inherently anomalous, **there is no way to make them
invisible**; the plan minimizes and spreads the footprint. The only way to keep
our IP off these assets entirely is to have a **third party** fetch them:
submitting the thumbnail URLs to the Internet Archive via `archive.py`
(`https://web.archive.org/save/{url}`) makes the **`archive.org_bot`** perform
the fetch; the operator sees ordinary crawler traffic. Caveats: IA may decline
adult imagery or not retain the binary; it is less reliable than a direct
fetch; and we would then retrieve the bytes from IA. Treat as an option, not a
replacement.

## 8. Integrity
Each stored thumbnail gets a SHA-256 in `captures/thumbs/manifest.json`
(`file`, `url`, `status`, `content_type`, `bytes`, `sha256`, `etag`,
`fetched_at`, `live`). Files live under `captures/thumbs/` and are pinned
`-text` via the existing `captures/**` `gitattributes` rule; git history keeps
every prior state. There is no RFC 3161 token over the thumbnail manifest yet —
add one with `python timestamp.py captures/thumbs/manifest.json` after the set
is complete.
