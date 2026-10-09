# ABDL-HUB copyright evidence project

Evidence-collection and legal-packaging project for the unauthorized rehosting
of a creator's adult video works on **abdlhub.com**. It discovers the rehosts,
preserves and authenticates the evidence, attributes the uploads, quantifies
damages, and assembles lawyer-ready drafts and takedowns.

> **Read before doing anything:** [`AGENTS.md`](AGENTS.md) (hard rules) and
> [`HANDOVER.md`](HANDOVER.md) (full brief). Collection is **read-only public
> access**, low-profile, and the content is assumed to be consensual adult
> age-play with no depiction of a minor. This is not legal advice.

## Start here
| If you want to… | Open |
| --- | --- |
| Understand the whole project | [`HANDOVER.md`](HANDOVER.md) |
| Know the rules of engagement | [`AGENTS.md`](AGENTS.md) |
| See what's done / what's next | [`TODO.md`](TODO.md) |
| Find any file in the repo | [`REPO_MAP.md`](REPO_MAP.md) |
| Understand the preservation approach | [`THUMBNAIL_PRESERVATION.md`](THUMBNAIL_PRESERVATION.md) |
| See the key findings | [`osint/PUBLIC_EXPOSURE.md`](osint/PUBLIC_EXPOSURE.md) |
| Plan the JFF↔Notion matching | [`JFF_MATCHING.md`](JFF_MATCHING.md) |
| Read the court-facing drafts | [`legal/COMPLAINT.md`](legal/COMPLAINT.md), [`legal/DECLARATION_1746.md`](legal/DECLARATION_1746.md) |

## Quickstart
```powershell
pip install -r requirements.txt
python sophie_scrape.py --verify --out sophie_little_all_videos.csv --live-out sophie_little_live_videos.csv
python osint_recon.py ; python osint/public_exposure.py
python evidence_store.py evidence      # verify all SHA-256 hashes -> all OK
python run_tests.py                    # 71 integrity / validation checks
```

## Directory map
| Path | What's in it |
| --- | --- |
| [`evidence/`](evidence/) | Raw backend table snapshots + SHA-256 manifest + RFC 3161 timestamp tokens |
| [`osint/`](osint/) | Site technology catalog, public-exposure & attribution report, subpoena targets |
| [`captures/`](captures/) | Rendered page captures (HTML/PNG/PDF), Wayback index, preserved thumbnails |
| [`takedowns/`](takedowns/) | Infringing-work index + DMCA § 512(c) notices |
| [`damages/`](damages/) | Work count, bytes, views + § 504(c) statutory matrix |
| [`legal/`](legal/) | Authorities, methodology, declaration, subpoena package, complaint, exhibits |
| [`manual/`](manual/) | Client's manual sheet (abdlhub title → JFF Video ID) |
| [`notion/`](notion/) | Notion-import CSV + schema |
| [`tests/`](tests/) | Validation suite (`run_tests.py`) |
| [`case_package/`](case_package/) | Generated lawyer-ready bundle (mirror of the deliverables) |
| `.cache/` (gitignored) | Source/probe caches — keep re-runs at ~0 requests |

The full, file-by-file index with links is in [`REPO_MAP.md`](REPO_MAP.md).

## Evidence chain (how a fact becomes proof)
1. **Collect** — [`sophie_scrape.py`](sophie_scrape.py), [`osint/public_exposure.py`](osint/public_exposure.py) → raw data.
2. **Snapshot** — [`evidence_store.py`](evidence_store.py) → [`evidence/`](evidence/) with hashes.
3. **Authenticate** — [`timestamp.py`](timestamp.py) → [`evidence/timestamps/`](evidence/timestamps/); [`capture.py`](capture.py) for rendered pages.
4. **Preserve the copies** — [`preserve_media.py`](preserve_media.py) (full HLS media) and [`preserve_thumbs.py`](preserve_thumbs.py); [`archive.py`](archive.py) (Wayback).
5. **Package** — [`takedown.py`](takedown.py), [`damages.py`](damages.py), [`build_legal.py`](build_legal.py), [`package.py`](package.py) → [`legal/`](legal/) + [`case_package/`](case_package/).

## Status snapshot
624 matching works (14 live / 610 orphaned); 12 attributed to uploader `Creator1`.
Preserved during the deletion sweep: **full media for all 14 live works**,
**608/610 orphan thumbnails**, and **page captures for all 14**. 80 tests passing.
Details in [`TODO.md`](TODO.md).
