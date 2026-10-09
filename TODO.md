# TODO — ABDL-HUB rehosting case

Objective: preserve, authenticate, and package evidence of the rehosting of
the creator's works on `abdlhub.com`, identify the Florida defendant, quantify
damages, and drive automated takedowns through counsel.

> **Gate (counsel to confirm):** the work is plain adult age-play between
> consenting adults, with **no depiction of a minor (real or simulated)**.
> Everything below assumes that. If that changes, stop and route to law
> enforcement instead.

## Assets we already hold
- `sophie_scrape.py` — discovers/verifies every tagged video; `sophie_little_all_videos.csv` (624), `sophie_little_live_videos.csv` (14).
- `evidence/` — raw backend table snapshots with a **SHA-256 manifest** (`comments`, `video_submissions`, `user_profiles`, `video_meta`, `bunny_catalog`, `site_config`, polls, RLS negatives).
- `osint/` — tech catalog + `PUBLIC_EXPOSURE.md`: uploader attribution (`Creator1` `a89bb9dc-…`), operator/staff accounts, donation address, sponsor `AbdlMatch.com`.
- Git history = immutable record of every prior snapshot.

## Priority analysis
Two truths dominate the strategy:
1. **Evidence decays** — 610 of 624 tagged works are already gone from Bunny; only cached thumbnails remain. Preservation is the only *irreversible* risk.
2. **Registration gates the money** — 17 U.S.C. § 412: without timely registration, **no statutory damages and no attorney's fees**.

So P1 (preserve) and P2 (register) are co-#1: one protects the evidence, the other protects the remedy.

---

## P1 — Freeze & authenticate evidence  *(do first)*
- [x] Raw API/table snapshots + hash manifest (`evidence/`).
- [x] **RFC 3161 trusted timestamp** of the evidence manifest (`timestamp.py`) → `evidence/timestamps/` (FreeTSA).
- [x] Full **page capture** (HTML + screenshot + PDF) per live URL (`capture.py`) — 12/12 captured, hashed, timestamped → `captures/20261009T050349Z/`.
- [x] Independent archival: `archive.py` submitted the 12 works to the **Wayback Machine** (8/12 snapshotted; 4 retryable) → `captures/archive.json`.
- [ ] Capture the **monetization** surface (ExoClick zones, Bitcoin, supporter paywall) as served on-page.
- [ ] Preserve the **delisted** works' thumbnails (610) + `video_meta` rows (already snapshotted) as proof they existed.

## P2 — Ownership & registration  *(co-#1)*
- [ ] Per-work **US Copyright Office registration** status; register now if not timely (statutory damages + fees).
- [ ] Originals with **EXIF/creation timestamps**; original platform upload dates; releases/contracts.
- [ ] Document authorship chain for the `Sophie Little` works (maps to `Creator1` submissions 9,10,33,34,70–73,80,86–88).
- [ ] Match originals (JFF export) to rehosts (`match.py --originals <export>`) → `matches/`.
- [ ] Assemble lawyer-ready bundle (`package.py --include-media --zip`) → `case_package/`.

## P3 — Identify the Florida defendant
- [ ] Subpoena target dossier (`osint/SUBPOENA_TARGETS.md`).
- [ ] DMCA **§ 512(h) subpoena** to Supabase for `Creator1` (`a89bb9dc-…`) and `Admin` (`46a556ca-…`).
- [ ] Reconcile with Dominic's location intel; confirm residency/venue in FL.
- [ ] Pivots: Bitcoin address, `AbdlMatch.com`, Discord, ExoClick payouts.

## P4 — Damages
- [ ] Aggregate works/views/duration/bytes (`damages.py`).
- [ ] Evidence of **willfulness** (ignored takedowns).
- [ ] Statutory matrix: § 504(c) $750–$30k/work, up to **$150k/work willful**; § 504(b) actual damages + profits.

## P5 — Automated takedown pipeline
- [ ] `takedown.py`: generate per-URL **§ 512(c)** notices from evidence, routed through the lawyer's letterhead.
- [ ] Host/ISP + search delisting + ExoClick/Bunny/Netlify/Supabase abuse reports.
- [ ] Track responses and escalations (`takedowns/index`).

## P6 — Counsel & process
- [ ] Retain FL attorney; issue **preservation letters** before the site purges.
- [ ] File; seek TRO/preliminary injunction; discovery; run the US LLC as plaintiff.

## P7 — Hygiene
- [ ] Keep collection low-profile (in place: per-host pacing, caching, browser headers).
- [ ] Never alter originals; log every access with timestamps.

---

## Tooling map
| Pri | Tool | Status |
| --- | --- | --- |
| P1 | `timestamp.py` (RFC 3161) | done |
| P1 | `capture.py` (Playwright) | done (12/12) |
| P1 | `archive.py` (Wayback) | 8/12, retryable |
| P2 | `match.py` (originals ↔ rehosts) | ready for JFF export |
| P5 | `takedown.py` | done (12 works, 4 notices) |
| P4 | `damages.py` | done |
| — | `legal/AUTHORITIES.md` (cited) | done |
| — | `legal/` court drafts + `build_legal.py` | done (drafts) |
| — | `tests/` + `run_tests.py` | done (64 tests) |
| — | `package.py` (lawyer bundle) | done |
