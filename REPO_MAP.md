# REPO_MAP — every primary file, and how to find your way

A guided index of the repository. Entry point: [`README.md`](README.md).
Full brief: [`HANDOVER.md`](HANDOVER.md). Rules: [`AGENTS.md`](AGENTS.md).

**How to use this map:** each row is `file → what it is → when you'd touch it`.
Links are relative to the repo root. Generated/derived files are marked ⟳.

---

## 1. Root documents (read these)
| File | What it is |
| --- | --- |
| [`README.md`](README.md) | Front door: purpose, quickstart, directory map, "start here". |
| [`HANDOVER.md`](HANDOVER.md) | Full successor brief: situation, rules, architecture, findings, strategy. |
| [`AGENTS.md`](AGENTS.md) | Non-negotiable rules + common commands (auto-loaded by agents). |
| [`TODO.md`](TODO.md) | Live prioritised plan and status. |
| [`THUMBNAIL_PRESERVATION.md`](THUMBNAIL_PRESERVATION.md) | Stealth analysis + rollout for the 610 orphaned thumbnails. |
| [`JFF_MATCHING.md`](JFF_MATCHING.md) | Analysis + plan for JFF↔abdlhub matching and Notion integration. |
| [`REPO_MAP.md`](REPO_MAP.md) | This file. |

## 2. Root tools (what collects/generates)
| File | What it does | Run |
| --- | --- | --- |
| [`sophie_scrape.py`](sophie_scrape.py) | Discovers + verifies the rehosts; builds URLs; caches; low-profile HTTP. | `python sophie_scrape.py --verify` |
| [`osint_recon.py`](osint_recon.py) | Tech-stack OSINT → `osint/site_catalog.*`. | `python osint_recon.py` |
| [`osint/public_exposure.py`](osint/public_exposure.py) | Attribution/public-exposure review; writes `evidence/` + `osint/PUBLIC_EXPOSURE.*`. | `python osint/public_exposure.py` |
| [`evidence_store.py`](evidence_store.py) | Evidence snapshots + SHA-256 manifest; `verify` CLI. | `python evidence_store.py evidence` |
| [`timestamp.py`](timestamp.py) | RFC 3161 trusted timestamping (FreeTSA). | `python timestamp.py [file]` |
| [`capture.py`](capture.py) | Headless page capture (HTML/PNG/PDF), age-gate aware. | `python capture.py` |
| [`archive.py`](archive.py) | Wayback Machine submission. | `python archive.py` |
| [`preserve_thumbs.py`](preserve_thumbs.py) | Stealth preservation of the 610 orphaned thumbnails. | `python preserve_thumbs.py --limit 60` |
| [`takedown.py`](takedown.py) | Generates the infringing-work index + DMCA § 512(c) notices. | `python takedown.py` |
| [`damages.py`](damages.py) | Aggregates damages inputs + § 504(c) matrix. | `python damages.py` |
| [`match.py`](match.py) | Matches JFF originals ↔ rehosts (duration/title/pHash). | `python match.py --originals <jff>` |
| [`build_legal.py`](build_legal.py) | Generates `legal/EXHIBIT_INDEX.md`, preservation letters, exhibit shells. | `python build_legal.py` |
| [`notion_export.py`](notion_export.py) | Builds the Notion-import CSV from our data + the client's manual sheet. | `python notion_export.py` |
| [`package.py`](package.py) | Assembles the lawyer bundle → `case_package/`. | `python package.py --include-media --zip` |
| [`run_tests.py`](run_tests.py) | Runs the validation suite. | `python run_tests.py` |

## 3. Root data & config
| File | What it is |
| --- | --- |
| [`sophie_little_all_videos.csv`](sophie_little_all_videos.csv) | All 624 matching works with URLs + HTTP status. |
| [`sophie_little_live_videos.csv`](sophie_little_live_videos.csv) | The 14 currently-playable works. |
| [`sophie_little_videos.csv`](sophie_little_videos.csv) | ⚠️ Superseded tag-only output; ignore. |
| [`case_package_20261009.zip`](case_package_20261009.zip) | ⟳ Zipped lawyer bundle. |
| [`requirements.txt`](requirements.txt) | Python deps. |
| [`.gitattributes`](.gitattributes) | Pins `evidence/*.json` and `captures/**` byte-exact (`-text`) for hashing. |
| [`.gitignore`](.gitignore) | Ignores `.cache/`, `__pycache__/`, lock files. |

## 4. `evidence/` — authenticated backend snapshots
| File | What it is |
| --- | --- |
| [`evidence/manifest.json`](evidence/manifest.json) | Per-table SHA-256 + provenance (the integrity spine). |
| [`evidence/video_meta.json`](evidence/video_meta.json) | Tag table (612 "Sophie Little" rows historically). |
| [`evidence/video_submissions.json`](evidence/video_submissions.json) | Uploads incl. `user_id` → the attribution source. |
| [`evidence/user_profiles.json`](evidence/user_profiles.json) | Accounts + admin/mod flags. |
| [`evidence/comments.json`](evidence/comments.json) | 93 comments (incl. the ignored takedown demand). |
| `video_views` · `video_likes` · `video_dislikes` · `video_reactions` | Engagement tables — readable but **not yet snapshotted** (would require re-timestamping). |
| [`evidence/bunny_catalog.json`](evidence/bunny_catalog.json) | Full Bunny Stream catalog at capture time. |
| [`evidence/site_config.json`](evidence/site_config.json) | Site settings (donation address, ad zones; big images hashed). |
| [`evidence/poll_votes.json`](evidence/poll_votes.json) | Poll votes. |
| [`evidence/favorites.json`](evidence/favorites.json) · [`evidence/watch_history.json`](evidence/watch_history.json) · [`evidence/video_reports.json`](evidence/video_reports.json) · [`evidence/model_requests.json`](evidence/model_requests.json) · [`evidence/title_suggestions.json`](evidence/title_suggestions.json) | RLS-protected — empty (negative evidence). |
| [`evidence/timestamps/index.json`](evidence/timestamps/index.json) | RFC 3161 tokens over the manifests (`.tsq`/`.tsr` alongside). |

## 5. `osint/` — technology & attribution
| File | What it is |
| --- | --- |
| [`osint/SITE_CATALOG.md`](osint/SITE_CATALOG.md) ⟳ | Human-readable tech/infra report. |
| [`osint/site_catalog.json`](osint/site_catalog.json) ⟳ | Raw OSINT evidence (headers, DNS, TLS, schema). |
| [`osint/PUBLIC_EXPOSURE.md`](osint/PUBLIC_EXPOSURE.md) ⟳ | Attribution + public-data findings (Creator1, operator, takedown-threat). |
| [`osint/public_exposure.json`](osint/public_exposure.json) ⟳ | Structured version of the above. |
| [`osint/public_exposure.py`](osint/public_exposure.py) | Generator for the exposure report. |
| [`osint/SUBPOENA_TARGETS.md`](osint/SUBPOENA_TARGETS.md) | Who to subpoena, what to ask, by what mechanism. |

## 6. `captures/` — rendered pages, archive, thumbnails
| File | What it is |
| --- | --- |
| [`captures/archive.json`](captures/archive.json) | Wayback snapshots for the works. |
| [`captures/20261009T050349Z/manifest.json`](captures/20261009T050349Z/manifest.json) | Per-file hashes of the page captures (12 works × HTML/PNG/PDF). |
| [`captures/thumbs/manifest.json`](captures/thumbs/manifest.json) | Hashes of preserved orphan thumbnails. |
| [`captures/thumbs/`](captures/thumbs/) | Preserved thumbnail JPEGs (batch 1: 62/610). |

## 7. `takedowns/` — infringement index & notices
| File | What it is |
| --- | --- |
| [`takedowns/takedown_index.csv`](takedowns/takedown_index.csv) | One row per infringing work (URLs, uploader, timestamp). |
| [`takedowns/dmca_notice_abdlhub.txt`](takedowns/dmca_notice_abdlhub.txt) | § 512(c) notice to the site operator. |
| [`takedowns/dmca_notice_netlify.txt`](takedowns/dmca_notice_netlify.txt) · [`takedowns/dmca_notice_bunny.txt`](takedowns/dmca_notice_bunny.txt) · [`takedowns/dmca_notice_supabase.txt`](takedowns/dmca_notice_supabase.txt) | Notices to host/CDN/backend. |

## 8. `damages/`
| File | What it is |
| --- | --- |
| [`damages/damages.json`](damages/damages.json) ⟳ | Work count, bytes, views, § 504(c) matrix. |
| [`damages/damages.md`](damages/damages.md) ⟳ | Human-readable damages summary. |

## 9. `legal/` — court-facing documentation
| File | What it is |
| --- | --- |
| [`legal/AUTHORITIES.md`](legal/AUTHORITIES.md) | Every required element mapped to a controlling authority (verified sources). |
| [`legal/authorities.json`](legal/authorities.json) | Structured authorities + documentation-element map + statuses. |
| [`legal/METHODOLOGY.md`](legal/METHODOLOGY.md) | How the evidence was collected/authenticated (declaration foundation). |
| [`legal/DECLARATION_1746.md`](legal/DECLARATION_1746.md) | Custodian declaration shell (28 U.S.C. § 1746). |
| [`legal/SUBPOENA_512h.md`](legal/SUBPOENA_512h.md) | § 512(h) notification + proposed subpoena + declaration. |
| [`legal/COMPLAINT.md`](legal/COMPLAINT.md) | Federal complaint shell. |
| [`legal/EXHIBIT_INDEX.md`](legal/EXHIBIT_INDEX.md) ⟳ | Exhibits A–I with hashes. |
| [`legal/exhibits/`](legal/exhibits/) ⟳ | Per-exhibit cover sheets (`exhibit_A.md` … `exhibit_I.md`). |
| [`legal/preservation/`](legal/preservation/) ⟳ | Preservation/legal-hold letters (supabase, bunny, netlify, exoclick). |

## 10. `tests/` — validation suite
| File | Covers |
| --- | --- |
| [`tests/test_evidence.py`](tests/test_evidence.py) | Manifest hashes, payload schema, RLS negatives, timestamps. |
| [`tests/test_scrape_outputs.py`](tests/test_scrape_outputs.py) | CSV columns, URL construction, no false positives, live ⊆ all. |
| [`tests/test_compare.py`](tests/test_compare.py) | Match scoring, date gate, pHash. |
| [`tests/test_legal.py`](tests/test_legal.py) | authorities.json schema, citation formats, allowed source domains. |
| [`tests/test_takedown.py`](tests/test_takedown.py) | § 512(c)(3) elements, work coverage. |
| [`tests/test_damages.py`](tests/test_damages.py) | Aggregate math + statutory constants. |
| [`tests/test_court_docs.py`](tests/test_court_docs.py) | Complaint/exhibit/declaration/preservation content. |
| [`tests/test_thumbs.py`](tests/test_thumbs.py) | Thumbnail targeting + manifest consistency. |
| [`tests/test_evidence_store.py`](tests/test_evidence_store.py) · [`tests/test_timestamp.py`](tests/test_timestamp.py) | Store tamper-detection; RFC 3161 DER structure. |
| [`tests/test_docs.py`](tests/test_docs.py) · [`tests/test_links.py`](tests/test_links.py) | Referenced paths exist; all markdown links resolve. |
| [`tests/common.py`](tests/common.py) | Shared test helpers. |

## 11. `case_package/` — generated bundle
[`case_package/`](case_package/) ⟳ mirrors the deliverables (evidence index,
infringement table, takedowns, `legal/`, manifest) for handing to counsel.
Regenerate with [`package.py`](package.py). Not edited by hand.

## 12. Where things come from (provenance quick-ref)
- `sophie_little_*_videos.csv` → [`sophie_scrape.py`](sophie_scrape.py)
- `evidence/*.json` → [`evidence_store.py`](evidence_store.py) / [`osint/public_exposure.py`](osint/public_exposure.py)
- `evidence/timestamps/*` → [`timestamp.py`](timestamp.py)
- `osint/*` → [`osint_recon.py`](osint_recon.py) / [`osint/public_exposure.py`](osint/public_exposure.py)
- `captures/…` → [`capture.py`](capture.py); `captures/archive.json` → [`archive.py`](archive.py)
- `captures/thumbs/…` → [`preserve_thumbs.py`](preserve_thumbs.py)
- `takedowns/*` → [`takedown.py`](takedown.py)
- `damages/*` → [`damages.py`](damages.py)
- `legal/EXHIBIT_INDEX.md`, `legal/exhibits/`, `legal/preservation/` → [`build_legal.py`](build_legal.py)
- `case_package/*` → [`package.py`](package.py)

## 13. `manual/` — client-provided inputs
| File | What it is |
| --- | --- |
| [`manual/abdlhub_stolen_videos_manual.csv`](manual/abdlhub_stolen_videos_manual.csv) | Client's manual sheet: abdlhub title → JFF Video ID (+ fingerprint flag, screenshot, line #). |
| [`manual/abdlhub_stolen_videos_manual_all.csv`](manual/abdlhub_stolen_videos_manual_all.csv) | Same 74 rows, reordered (not a superset). |

## 14. `notion/` — Notion import
| File | What it is |
| --- | --- |
| [`notion/abdlhub_stolen_videos.csv`](notion/abdlhub_stolen_videos.csv) ⟳ | Union of both datasets (698 rows) in a Notion-import schema. |
| [`notion/NOTION_SCHEMA.md`](notion/NOTION_SCHEMA.md) ⟳ | Property types + import steps. |
| [`notion_export.py`](notion_export.py) | Generator for the above; see [`JFF_MATCHING.md`](JFF_MATCHING.md) §3. |
