# HANDOVER — ABDL-HUB copyright evidence project

_Authored for the next agent/model taking over. Read this top to bottom before
touching anything. It records the situation, hard constraints, architecture,
findings, tooling, and open work. Pair it with `TODO.md` (live plan) and
`osint/PUBLIC_EXPOSURE.md` (findings)._

---

## 0. First 10 minutes
1. `git log --oneline` — each commit is a discrete milestone. The **git history is itself evidence**; do not rewrite it.
2. Read this file, then `TODO.md`, then `osint/PUBLIC_EXPOSURE.md`.
3. `python evidence_store.py evidence` — verifies the SHA-256 manifest. It should print all `OK`. If anything says `MISMATCH`, stop and investigate (checkout EOL corruption — see §9).
4. Do **not** run anything that hits the target until you have re-read §2 (rules of engagement).

---

## 1. Situation & objective
A creator (referred to in-project as **"Sophie Little"**) had her adult content
**stolen and rehosted on `abdlhub.com`**. The client (the creator's side) is
building a US copyright case — likely filed in **Florida** (the alleged
operator's location), with the client based in **BC, Canada**, intending to use
a **US LLC** as plaintiff. A DMCA agent has been retained (~$2,500); litigation
counsel is still being located. A third party, **"Dominic"**, is assisting the
client and has intel on the offender's location.

This repository: discover the rehosts, **preserve and authenticate evidence**,
attribute the uploads, quantify damages, and produce a **lawyer-ready package**
plus automated takedown notices.

---

## 2. Rules of engagement (non-negotiable)
1. **Legality gate.** The client confirmed the content is **plain, consensual
   adult age-play with no depiction of a minor (real or simulated)**. The
   project is premised on that. If any evidence ever suggests otherwise,
   **stop** — that is criminal material, not a civil-case input; route to
   NCMEC/IC3/RCMP instead. Do not collect, download, or preserve such material.
2. **Read-only public access only.** All backend reads use the Supabase **anon
   JWT that the site itself ships in its HTML** — i.e. exactly what any
   visitor's browser holds. Do **not**: bypass authentication, use a
   `service_role` key, write/modify data, invoke action endpoints
   (`request-upload`, `set-title`, `upload-avatar`), or test/attack partner
   infrastructure (`AbdlMatch.com` runs legacy Apache — do not probe it).
3. **Be invisible.** Keep collection low-profile: per-host rate limiting,
   browser-realistic headers, caching so re-runs hit the network ~0 times, and
   never burst. See §8.
4. **Never alter evidence.** Originals are immutable; every fetch is logged with
   timestamp/provenance in the manifests. Append, don't overwrite.
5. **This is not legal advice.** Legal reasoning in §11 is analysis to hand to
   counsel, not advice.

---

## 3. Quick start (Windows / pwsh, Python 3.11)
```powershell
# deps already installed in this environment: requests, bs4, PIL, numpy, cv2, playwright (+ chromium)
pip install -r requirements.txt

# refresh the scrape (mostly cache hits; see §8)
python sophie_scrape.py --verify --out sophie_little_all_videos.csv --live-out sophie_little_live_videos.csv

# reproduce OSINT
python osint_recon.py                  # tech catalog      -> osint/
python osint/public_exposure.py        # attribution       -> osint/ + evidence/

# evidence integrity
python evidence_store.py evidence

# legal artifacts
python timestamp.py                    # RFC 3161 over evidence/manifest.json
python capture.py                      # page captures (Playwright)
python archive.py                      # Wayback snapshots
python takedown.py                     # DMCA notices
python damages.py                      # damages workbook
python match.py --originals <jff>.json --thumbnails
python package.py --include-media --zip
```
Environment notes: `openssl` and `ots` are **not** installed; `playwright` and
Chromium **are**. Everything is plain `requests` unless noted.

---

## 4. Site architecture & API map
The site is a **vanilla-JS SPA** over public SaaS. Full detail in
`osint/SITE_CATALOG.md` / `.json`. Essentials:

| Piece | Value |
| --- | --- |
| Site | `https://abdlhub.com` (Netlify edge + 4 serverless functions) |
| Supabase project | `https://hbvwlzjxsmhreeqwypwp.supabase.co` (PostgREST + GoTrue) |
| Supabase anon JWT | embedded in page source; hardcoded in `sophie_scrape.py` (`SUPA_KEY`) |
| Bunny Stream library | `621930` |
| Bunny pull zone | `vz-e81debcf-c73.b-cdn.net` (needs `Referer: https://abdlhub.com/`) |
| Catalog endpoint | `/.netlify/functions/bunny-videos?page=N&perPage=500` (3215 items) |
| Video page | `https://abdlhub.com/?v={guid}` |
| Stream (HLS) | `https://vz-e81debcf-c73.b-cdn.net/{guid}/playlist.m3u8` (AES-128; key public) |
| Thumbnail | `https://vz-e81debcf-c73.b-cdn.net/{guid}/{thumbnailFileName}?width=480` |
| Other functions | `request-upload`, `set-title`, `upload-avatar` (auth-gated; DO NOT call) |

**Ads/monetization:** ExoClick (`a.magsrv.com` banners, `s.magsrv.com` VAST,
`a.pemsrv.com` popunder); zones `6009644`, `6016956`, `6011096`, `6012920`.
**Analytics:** Umami (`cloud.umami.is`, configurable). **Sponsor/affiliate:**
`AbdlMatch.com` (images on second Bunny zone `abdlhub-images.b-cdn.net`).
**Discord invite:** `kbnJTj2DB` (expired). **Bitcoin donation address:**
`bc1qmw0zehsntqj0ckwsw4mm44flhcqm7tvzu0xu4h`.

### Supabase tables (15)
Readable with the anon key: `comments`, `poll_votes`, `site_config`,
`user_profiles`, `video_dislikes`, `video_likes`, `video_meta`,
`video_reactions`, `video_submissions`, `video_views`.
RLS-protected (return no rows to anon — recorded as **negative evidence**):
`favorites`, `watch_history`, `video_reports`, `model_requests`,
`title_suggestions`. Admin API `/auth/v1/admin/*` needs the service key
(not exposed anywhere in the client). Public RPC `count_users` → ~727.

**Tags** live in `video_meta.tags` (`text[]`). The creator appears in the site's
`settings.models` list as **"Sophie Little"**. Tag application is inconsistent:
most current rehosts are titled "Sofia"/"princess Sofia" but only 1–4 carry the
tag. Hence the matcher uses **tag OR title**.

---

## 5. Domain findings (the "so what")
- **Uploader attribution (the smoking gun):** all **12** subject rehosts were
  submitted by Supabase account **`Creator1`** = `a89bb9dc-d09f-4475-b9ed-ae398edf928b`
  (submission ids **9, 10, 33, 34, 70, 71, 72, 73, 80, 86, 87, 88**; 2026-07-15
  → 2026-09-29; up to 1.66 GB each). `video_submissions` publicly exposes
  `user_id` + title + description + embed URL.
- **Operator/staff:** `Admin` = `46a556ca-1789-4dd9-a72d-bbe6df94e5c9`;
  mods `babycakesabdl` = `5c86b4b8-5f02-4d6a-a649-aebac3d99a78` (also the
  **top uploader**, 44 submissions) and `LightSwitch` = `0b607c1d-5bb3-4ee3-a26e-e7180ed7af13`.
- **Descriptions leak the original creator's other identities** (a Reddit
  handle, a ThisVid account) and file provenance (2015 Samsung captures).
- **Repeat infringer evidence:** another rights-holder, `lkxentertainmentltd`,
  posted a takedown/sue threat on 2026-09-29 — the operator ignored it.
- **No secrets leaked** in `site_config`.

### Scrape counts
- Tagged "Sophie Little": **612** rows historically.
- Present in current catalog: **4**; with **live stream: 2** (tag-only).
- **610 delisted** (thumbnails cached, streams 404 → deleted/private).
- Current matching (`tag=exact "Sophie Little"` OR title `/sofia/`, minus
  `/kiki cali|sophie ladder|sophiaquin/`): **624 all** / **14 live**.
- `sophie_little_videos.csv` is **superseded** (old tag-only, 612 rows) — kept
  only for history; ignore it.

---

## 6. Repository layout
```
sophie_scrape.py        main scraper (discovery, join, URL build, verify, caches)
evidence_store.py       EvidenceStore + SHA-256 manifest + `verify` CLI
timestamp.py            RFC 3161 (FreeTSA) timestamper; .tsq/.tsr + index
capture.py              Playwright page capture (HTML+PNG+PDF), age-gate aware
archive.py              Wayback Machine submission
osint_recon.py          tech-stack OSINT -> osint/site_catalog.{json,md}
osint/public_exposure.py  attribution/public-exposure review -> osint/ + evidence/
takedown.py             DMCA §512(c) notice generator -> takedowns/
damages.py              damages inputs & §504(c) matrix -> damages/
match.py                JFF originals <-> rehosts matcher -> matches/
package.py              lawyer-ready bundle -> case_package/ (+ zip)
TODO.md                 live plan/priorities
HANDOVER.md             this document

evidence/               raw table snapshots + manifest.json + timestamps/   (tracked, gitattributes -text)
osint/                  SITE_CATALOG.*, PUBLIC_EXPOSURE.*, SUBPOENA_TARGETS.md
captures/<run>/         per-guid .html/.png/.pdf + manifest.json + archive.json
takedowns/              takedown_index.csv + 4 DMCA notices
damages/                damages.json + damages.md
case_package*/          assembled bundle (text-only unless --include-media) + .zip
sophie_little_*.csv     scrape outputs
.cache/                 sources.json, probes.json, cookies.json, thumbs/   (GITIGNORED)
```

### Tool reference (one-liners)
- **sophie_scrape.py** — fetches `video_meta` + Bunny catalog, joins on guid,
  builds `page_url`/`thumbnail_url`/`stream_url`/`variant_playlists`, verifies
  URLs (Referer), writes CSVs. `--tag/--match/--title/--exclude/--verify/
  --refresh/--recheck/--seed-probes/--delay/--workers`.
- **evidence_store.py** — `EvidenceStore.save(name, rows, url, note, sanitize_data)`;
  `python evidence_store.py [dir]` verifies hashes.
- **timestamp.py** — `python timestamp.py [file]` (default evidence/manifest.json);
  `--verify` lists.
- **capture.py** — `--limit N --headed`; dismisses `#ageGate .btn-enter`.
- **archive.py** — `--limit N`; writes `captures/archive.json`.
- **takedown.py** — no args; uses `ATTRIBUTED_UPLOADER`, `TITLE_PATTERN`.
- **damages.py** — no args; RPM scenarios editable at top.
- **match.py** — `--originals FILE [--thumbnails]`; see §7.
- **package.py** — `--include-media --zip`.

---

## 7. JFF matching (pending client access)
The client will export the creator's originals from **JustForFans**. Feed
`match.py` a manifest (`originals.json` or `.csv`) with any of:
`id, title, published_at, duration_seconds, thumbnail (path|url), media (path),
sha256, source_url`.

Signals: duration (±2 s), fuzzy title (`SequenceMatcher`), optional **perceptual
thumbnail hash** (cv2 DCT pHash, `--thumbnails` downloads rehost thumbs into
`.cache/thumbs/`), gated by "rehost must postdate original". Accept ≥ 0.60.
Output `matches/{matches.json,matches.csv}` → feeds `works_of_authorship.csv`.

**Enhancement available (not built):** video-frame fingerprinting — sample
frames from the JFF original (`media`) and the rehosted HLS (downloadable via
the public AES key) and compare pHashes. Strongest proof of copying through
re-encodes. Add if originals include media files.

---

## 8. Stealth & caching design
Implemented in `sophie_scrape.py` (`HostRateLimiter`, `PoliteSession`) and
reused everywhere:
- **Per-host pacing** (base `--delay 0.6s`, +0–100% jitter) + a 4–12 s pause
  every 50 requests; exponential backoff on 429/5xx (`urllib3.Retry`).
- **Browser-realistic headers** (UA, `sec-ch-ua`, `Sec-Fetch-*`, `Accept-Language`)
  plus `Referer: https://abdlhub.com/` (required by the CDN).
- **Persistent session** — one cached warm-up page load; the site sets no
  cookies.
- **Caches** (`.cache/`, gitignored): `sources.json` (catalog+meta, 12 h TTL),
  `probes.json` (per-URL status, 24 h TTL). **Incremental catalog check** skips
  the other 6 pages when page 1 is unchanged.
- Result: a repeat `sophie_scrape.py --verify` run = **0 network requests**;
  a forced full refresh ≈ 16 requests.

---

## 9. Evidence integrity — patterns that must not be broken
- `evidence_store.py` writes JSON with `newline=""` and hashes the **exact
  bytes**. `.gitattributes` pins `evidence/*.json -text` and `captures/** -text`
  so **git never rewrites line endings** (Windows `core.autocrlf` would
  otherwise break every hash on checkout).
- If you add a new hashed artifact directory, **add it to `.gitattributes` as
  `-text`** and hash the on-disk bytes.
- The capture manifest (`captures/<run>/manifest.json`) is timestamped
  separately from `evidence/manifest.json`. Both tokens are under
  `evidence/timestamps/`; `index.json` records target/hash/tsa/tsr.
- **Do not edit tracked evidence files by hand.** Re-fetch and re-snapshot.
- Incident to know: a LibreOffice `.~lock.<file>#` file once got committed when
  the client had a CSV open; now gitignored (`.~lock*`, `*.csv#`).

### Environment gotchas
- Windows/pwsh; heredocs unavailable — write scripts to files, don't pipe.
- `openssl`/`ots` absent → RFC 3161 is implemented in pure Python in
  `timestamp.py`; full token verification is deferred to counsel's `openssl ts`.
- Playwright browsers live under `%LOCALAPPDATA%\ms-playwright` (not in repo).
- Repo is ~80 MB (captures are the bulk).

---

## 10. What exists today (artifacts)
- `evidence/` — 12 tables + `site_config` (base64 model images replaced by
  sha256 markers), RLS negatives, `manifest.json`, `timestamps/` (2 RFC 3161 tokens).
- `captures/20261009T050349Z/` — 12 works × {html,png,pdf} + hashed manifest;
  `captures/archive.json` — Wayback (8/12 ok, 4 retryable).
- `takedowns/` — `takedown_index.csv` + notices for operator/Netlify/Bunny/Supabase.
- `damages/` — **12 works, 8.13 GiB, 1.79 h, 2,511 views; §504(c) willful max $1.8M**.
- `osint/` — tech catalog, `PUBLIC_EXPOSURE.md`, `SUBPOENA_TARGETS.md`.
- `case_package/` + `case_package_20261009.zip` (text-only bundle).

---

## 11. Legal strategy (analysis for counsel, not advice)
**Two dominant facts:** evidence **decays** (610/624 already deleted), and
**registration gates the money** — 17 U.S.C. **§ 412**: without timely
registration there are **no statutory damages and no attorney's fees**.

Priority: **P1 preserve** and **P2 register** are co-#1. Then defendant ID,
damages, takedowns, filing.

- **Claims:** § 501 infringement; § 504(c) statutory ($750–$30k/work, **up to
  $150k/work if willful**); § 504(b) actual damages + profits; DMCA §§ 512(c)/(h),
  512(d) delisting.
- **Willfulness:** operator ignored `lkxentertainmentltd`'s takedown demand.
- **Venue:** Florida (11th Cir.); plaintiff via US LLC; cross-border CA→US.
- **Simulated-minor analysis (asked earlier):** obscenity never defeats
  copyrightability (*Mitchell Bros.* 5th Cir.; *Jartech* 9th Cir.). BUT if work
  were deemed **obscene**, 18 U.S.C. § 1466A reaches *simulated* depictions, and
  **Canada's s. 163.1 is stricter (no obscenity requirement)** — creating
  exposure for the creator and leverage for the operator. Moot here given the
  §2 confirmation, but **never frame works by minor-coded elements** in any
  filing/notice.

### Preservation targets (send FIRST)
Supabase (project ref above), Bunny.net, Netlify, ExoClick — before logs/billing
age out. See `osint/SUBPOENA_TARGETS.md`.

---

## 12. Open work
See `TODO.md`. Highest-leverage next actions:
1. **P2 registration status** (client-side; blocks the remedy) and JFF export → `match.py`.
2. **Preservation letters** (counsel) to Supabase/Bunny/Netlify/ExoClick.
3. Retry the **4 failed Wayback** snapshots (`archive.py`).
4. Optionally: capture the **monetization surface** as served; preserve the
   **610 delisted** thumbnails; add **video-frame fingerprinting** to `match.py`.
5. Draft the **declaration/affidavit** tying works → registrations → rehosts → damages.

---

## 13. Key identifiers (copy/paste)
```
Uploader (all 12 works)  Creator1        a89bb9dc-d09f-4475-b9ed-ae398edf928b
Operator                 Admin          46a556ca-1789-4dd9-a72d-bbe6df94e5c9
Mod / top uploader       babycakesabdl  5c86b4b8-5f02-4d6a-a649-aebac3d99a78
Mod                      LightSwitch    0b607c1d-5bb3-4ee3-a26e-e7180ed7af13
Supabase project ref     hbvwlzjxsmhreeqwypwp
Bunny library            621930
Bunny pull zone          vz-e81debcf-c73.b-cdn.net
Sponsor                  AbdlMatch.com
Bitcoin                  bc1qmw0zehsntqj0ckwsw4mm44flhcqm7tvzu0xu4h
Discord invite           kbnJTj2DB
12 rehost guids          8f71399f-…, 9627aedf-…, 4478076e-…, 39b63ca2-…, 710142df-…,
                         cbc1420c-…, c1904e3e-…, f64107b2-…, 02f46a22-…, 50e8212f-…,
                         26cf42e4-…, 03bfd473-…        (full guid in takedowns/takedown_index.csv)
```

---

## 14. Git conventions in use
- Small, frequent, descriptive commits (see log). **Commit early and often.**
- Never commit secrets you introduce; the only credential in-repo is the site's
  **public anon JWT** (by design).
- Repo-local git identity was set (`jas` / `jas@localhost`) because none was
  configured; global config was not touched.
- `.cache/` and `__pycache__/` are ignored; `evidence/`, `captures/`,
  `takedowns/`, `damages/`, `case_package/` are tracked.

---

## 15. Hard "do nots"
- Do not attempt unauthorized access, exploitation, or service-key usage.
- Do not probe `AbdlMatch.com` or other partner infrastructure.
- Do not collect/preserve material if the §2 legality gate is not met.
- Do not rewrite git history or hand-edit tracked evidence.
- Do not "help" beyond lawful, read-only, low-profile collection and packaging.
