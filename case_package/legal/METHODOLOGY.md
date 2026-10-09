# Collection methodology

Purpose: document, for authentication and for any custodian declaration, **how
each item of evidence in this repository was collected, when, with what tools,
and how its integrity is preserved**. Companion instruments:
[`DECLARATION_1746.md`](DECLARATION_1746.md), [`AUTHORITIES.md`](AUTHORITIES.md),
[`HANDOVER.md`](../HANDOVER.md).

**Navigate:** [`REPO_MAP`](../REPO_MAP.md) · [`HANDOVER`](../HANDOVER.md) · [`DECLARATION_1746`](DECLARATION_1746.md) · [`COMPLAINT`](COMPLAINT.md)

> This is a factual methodology record, not legal advice.

## 1. Collector and authority
- Collected by: **[COLLECTOR NAME]** on behalf of **[CLIENT / RIGHTS HOLDER]**.
- Authority: **[STATE ROLE — e.g., owner, agent, or retained investigator]**.
- Client location: **British Columbia, Canada** (see declaration form in
  `legal/DECLARATION_1746.md`, § 1746 executed-without-the-United-States form).

## 2. Environment
- Windows 11 / PowerShell 7; Python 3.11.
- Tools: `requests`; Playwright (Chromium); Pillow/numpy/OpenCV for matching.
- All collection used ordinary HTTP requests and a headless browser simulating
  a normal visitor. **No authentication was bypassed, no privileged/service
  key was used, no data was written to the target, and no partner
  infrastructure was tested.** See `HANDOVER.md` §2.

## 3. Target and public access surface
`abdlhub.com` is a single-page application. Three public services expose the
data collected here:

| Service | Public surface | Access control |
| --- | --- | --- |
| Supabase (project `hbvwlzjxsmhreeqwypwp`) | `/rest/v1/{table}` (PostgREST) and `/auth/v1/settings` | The site ships its **anon JWT in its own HTML**; that key is used exactly as any visitor's browser does. |
| Netlify function | `/.netlify/functions/bunny-videos?page=&perPage=` (JSON catalog) | Unauthenticated. |
| Bunny Stream/CDN (`vz-e81debcf-c73.b-cdn.net`) | thumbnails and HLS (`{guid}/playlist.m3u8`) | Requires only a `Referer: https://abdlhub.com/` header. |

Supabase tables captured: `comments`, `poll_votes`, `site_config`,
`user_profiles`, `video_dislikes`, `video_likes`, `video_meta`,
`video_reactions`, `video_submissions`, `video_views`; and RLS-protected tables
recorded as **negative evidence** (`favorites`, `watch_history`,
`video_reports`, `model_requests`, `title_suggestions`). The Supabase admin API
requires the service key, which is **not** present in the client and was not
used.

## 4. Procedures
1. **Discovery & join** (`sophie_scrape.py`): fetch the full `video_meta` table
   and the Bunny catalog; join on media `guid`; build the public page URL
   (`https://abdlhub.com/?v={guid}`), thumbnail URL, HLS master and variant
   playlist URLs. Selection rule: tag exactly `"Sophie Little"` **or** title
   matching `/sofia/`, excluding `/kiki cali|sophie ladder|sophiaquin/`.
2. **URL verification**: each URL is probed; HTTP status and content-type are
   recorded per row (`sophie_little_all_videos.csv`).
3. **Raw snapshots** (`evidence_store.py` / `osint/public_exposure.py`): every
   table's rows are written verbatim with `source_url`, `row_count`, and
   `fetched_at`; `site_config`'s large inline base64 model images are replaced
   by their SHA-256 markers (the images are unrelated to the claim).
4. **Page captures** (`capture.py`): each live page is rendered in headless
   Chromium, the site's own age gate (`#ageGate .btn-enter`) is dismissed, and
   the fully hydrated page is saved as HTML, full-page PNG, and PDF.
5. **Third-party archival** (`archive.py`): the same page URLs are submitted to
   the Internet Archive (Wayback).
6. **Legal drafts** (`build_legal.py`, `takedown.py`, `damages.py`): generated
   from the evidence without manual transcription.

## 5. Integrity & chain of custody
- **SHA-256**: every snapshot and capture is hashed; `evidence/manifest.json`
  and `captures/<run>/manifest.json` record per-item hashes with an append-only
  history. `python evidence_store.py evidence` re-verifies all hashes.
- **RFC 3161 trusted timestamps**: the evidence and capture manifests are
  timestamped by a public Time Stamp Authority (FreeTSA); tokens and the request
  files are stored under `evidence/timestamps/` and may be independently
  verified with `openssl ts -verify`.
- **Immutability**: tracked evidence is pinned byte-exact (`-text`) in
  `.gitattributes` so line-ending conversion cannot alter hashes; the version
  control history preserves every prior snapshot.
- **No alteration**: evidence files are never hand-edited; refreshes create new
  snapshots rather than modifying existing ones.

## 6. Reproduction
```
python sophie_scrape.py --verify --out sophie_little_all_videos.csv --live-out sophie_little_live_videos.csv
python osint_recon.py
python osint/public_exposure.py
python timestamp.py ; python capture.py ; python archive.py
python takedown.py ; python damages.py ; python build_legal.py
python evidence_store.py evidence    # all hashes should print OK
python run_tests.py                  # 58+ integrity checks
```

## 7. Known limitations (state these candidly)
- `views` are the site's own counters, not independently verified plays.
- Of 624 matching records, **610 were already deleted** from the media library;
  for those, only the cached thumbnail and the database row survive.
- Creator tagging is applied inconsistently; selection therefore combines tag
  and title, and known non-subject names are excluded (Exhibit B).
- Dates are the collector's clock (UTC) plus the RFC 3161 TSA time; they are
  not drawn from the target's server clock.
- The identity of the natural person behind the accounts is **not** established
  here; it requires the subpoenas in `legal/SUBPOENA_512h.md` and
  `osint/SUBPOENA_TARGETS.md`.
- This project assumes the content is consensual adult work with no depiction
  of a minor; that premise must hold for the civil posture to apply.
