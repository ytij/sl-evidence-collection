# ABDL-HUB rehosting — findings & evidence summary

**Prepared for the copyright holder and counsel.** This repository documents
the unauthorized rehosting of a creator's works on **abdlhub.com**, preserves
the evidence in an authenticated form, and assembles the drafts needed for
takedown and litigation. Originally written 2026-10-09; see
[`TODO.md`](TODO.md) for the live status.

> **Read first:** [`HANDOVER.md`](HANDOVER.md) (full brief), [`AGENTS.md`](AGENTS.md)
> (rules of engagement), [`REPO_MAP.md`](REPO_MAP.md) (file index).
> **Not legal advice** — the legal reasoning here is analysis to hand to counsel.

---

## 1. Executive summary
A commercial piracy site, **abdlhub.com**, reproduced and publicly distributed
this creator's adult video works without authorization and monetizes them with
advertising. The works were uploaded by a single identifiable account, and the
site's own publicly-readable backend **names that account and the operator**.
We have preserved the rehosted copies themselves — including the full video
media — with cryptographic hashes and trusted timestamps, and prepared DMCA
notices, a preservation/subpoena package, and a complaint shell.

Two facts drive the strategy:
1. **The evidence decays.** Most of the rehosted works have already been
   deleted; we preserved what remained just "before it's gone."
2. **Registration gates the remedy.** Under 17 U.S.C. § 412, no statutory
   damages or attorney's fees are available without timely registration. This is
   the single most important item for the copyright holder/counsel to confirm.

## 2. Key findings
1. **Scale and scope.** 624 works on the site match the creator's identifying
   marks (the "Sophie Little" tag or "Sofia"-titled works). **14 were still live**
   at capture time; **610 had already been delisted** (thumbnails and database
   rows remained).
2. **Uploader attribution (the core proof).** The site's public backend table
   `video_submissions` exposes the uploader of every approved video. **All 12
   attribution-checked rehosts were uploaded by one account — `Creator1`
   (`user_id a89bb9dc-d09f-4475-b9ed-ae398edf928b`)** — between 2026-07-15 and
   2026-09-29, each up to ~1.66 GB.
3. **Operator and staff.** The operator account is **`Admin` (`46a556ca-…`)**;
   moderators include **`babycakesabdl`** (also the single largest uploader, 44
   submissions) and **`LightSwitch`**.
4. **Willfulness.** Another rights holder, `lkxentertainmentltd`, posted a
   public **takedown/sue demand on 2026-09-29**; the operator ignored it and
   continued hosting. This supports a willfulness finding (§ 504(c)(2)) and,
   potentially, the § 504(c)(3) presumption (false registrar contact info).
5. **Leaked provenance.** The operator's own submission descriptions reveal the
   original creator's other identities and the files' provenance, supporting
   chain of custody.
6. **Asset preservation succeeded.** Full **video media for all 14 live works**
   (345 MB), **608 of 610 orphaned thumbnails**, rendered page captures for all
   14, and 12 backend tables — all hashed and timestamped.

## 3. Evidence and authenticity
| What | Where | Integrity |
| --- | --- | --- |
| Backend tables (12) | [`evidence/`](evidence/), [`evidence/manifest.json`](evidence/manifest.json) | SHA-256 per table + provenance |
| Trusted timestamps | [`evidence/timestamps/index.json`](evidence/timestamps/index.json) | **RFC 3161** tokens (FreeTSA) |
| Rehosted media (14 works) | [`captures/media_manifest.json`](captures/media_manifest.json) (bytes in gitignored `staging/media/`) | SHA-256 per work + key |
| Orphan thumbnails (608) | [`captures/thumbs/`](captures/thumbs/) (bytes local-only) | SHA-256 per image |
| Page captures (HTML committed; PNG/PDF local-only) | [`captures/20261009T201150Z/`](captures/20261009T201150Z/) | SHA-256 per file |
| Independent archive | [`captures/archive.json`](captures/archive.json) | Wayback snapshots |
| DMCA notices | [`takedowns/`](takedowns/) | § 512(c)(3) element-complete |
| Damages computation | [`damages/`](damages/) | § 504(c) matrix |

**How the evidence was obtained (for authentication):** every item was collected
through the site's **ordinary public interface** using the anonymous key the
site publishes to every visitor (`legal/METHODOLOGY.md`; `legal/DECLARATION_1746.md`).
No authentication was bypassed, no privileged credential used, and nothing on
the target was modified. Collection was rate-limited and low-profile.

**Chain of custody:** every snapshot is hashed and recorded with its source URL
and fetch time; the manifests are timestamped by a third-party Time Stamp
Authority; the version-control history preserves every prior snapshot; and
tracked evidence is pinned byte-exact so hashes survive checkout.

## 4. Legal posture (for counsel)
- **Claims:** copyright infringement (17 U.S.C. § 501; exclusive rights of
  reproduction, distribution, public performance/display — § 106); statutory
  damages (§ 504(c)) or actual damages + profits (§ 504(b)); costs and fees
  (§ 505).
- **Registration:** registration must be complete to sue on a "United States
  work" (§ 411(a); *Fourth Estate v. Wall-Street.com*, 586 U.S. 296 (2019)), and
  **timely registration is required for statutory damages/fees (§ 412)** —
  including for foreign works.
- **Damages exposure:** 12 works × statutory range (§ 504(c)) yields a willful
  maximum of **$1,800,000**; see [`damages/damages.json`](damages/damages.json).
- **Jurisdiction/venue:** the operator is believed to be in **Florida**;
  personal jurisdiction under Fla. Stat. § 48.193; venue under 28 U.S.C.
  § 1400(a). Subject-matter jurisdiction under 28 U.S.C. § 1338(a).
- **Identification:** a **§ 512(h) subpoena package** targets the backend,
  CDN, host, and ad network to name the natural person
  ([`osint/SUBPOENA_TARGETS.md`](osint/SUBPOENA_TARGETS.md),
  [`legal/SUBPOENA_512h.md`](legal/SUBPOENA_512h.md)).
- **Mapped authorities:** every required document element with a verified
  citation is in [`legal/AUTHORITIES.md`](legal/AUTHORITIES.md).

Draft instruments ready for counsel: [`legal/COMPLAINT.md`](legal/COMPLAINT.md),
[`legal/DECLARATION_1746.md`](legal/DECLARATION_1746.md),
[`legal/SUBPOENA_512h.md`](legal/SUBPOENA_512h.md),
[`legal/EXHIBIT_INDEX.md`](legal/EXHIBIT_INDEX.md).

## 5. What is needed from the copyright holder / counsel
1. **Copyright registration number(s) and dates** — the § 412 gate (§ 411(a) for
   a U.S. work). *Highest priority.*
2. **Write-back into Notion** — a Notion-importable export of both our data and
   her manual JFF sheet is at [`notion/`](notion/) (see § 6 below).
3. **JFF originals export** (media, captions, thumbnails) — to prove each
   original and to run frame matching ([`JFF_MATCHING.md`](JFF_MATCHING.md)).
4. **Her `Site screenshot` PNGs** — to match her list to our abdlhub records.
5. **Counsel decisions** — venue, whether to download the infringing media for
   the record (already done for the live works), and sign-off on notices.
6. **Send the preservation letters** ([`legal/preservation/`](legal/preservation/))
   before provider logs/billing age out.

## 6. The copyright holder's manual collection
She has been collecting the theft manually. Her sheet
([`manual/`](manual/)) maps **abdlhub titles → JFF Video IDs** (74 rows; 58
unique JFF ids; 10 already fingerprinted; **73 already delisted**). We merged it
with our automated data into a **fresh-import CSV for Notion**
([`notion/abdlhub_stolen_videos.csv`](notion/abdlhub_stolen_videos.csv), 698
rows) — schema and steps in [`notion/NOTION_SCHEMA.md`](notion/NOTION_SCHEMA.md).
Her structure (JFF id + title + screenshot) is the anchor for the matching
system designed in [`JFF_MATCHING.md`](JFF_MATCHING.md).

## 7. Limitations (stated candidly)
- `views` are the site's own counters, not independently verified plays.
- Of 624 matching works, **610 were already deleted**; for those, only the
  cached thumbnail and the database row survive.
- The identity of the natural person behind the accounts is **not established**
  here; it requires the subpoena.
- Dates are the collector's clock (UTC) plus the RFC 3161 TSA time, not the
  target's server clock.
- This project assumes the content is consensual adult work with **no depiction
  of a minor (real or simulated)**; that premise must hold for the civil posture.
- **Media bytes are excluded from the git repo.** The rehosted videos live in
  gitignored `staging/media/`, and the thumbnails/screenshots/PDFs also stay
  local (gitignored); only the SHA-256 manifests are committed. Back the bytes
  up out of the repo — a clone contains hashes, not imagery.

## 8. Navigating the repository
[`REPO_MAP.md`](REPO_MAP.md) is the file-by-file index. Highlights:
[`osint/PUBLIC_EXPOSURE.md`](osint/PUBLIC_EXPOSURE.md) (attribution findings),
[`osint/SITE_CATALOG.md`](osint/SITE_CATALOG.md) (technology),
[`legal/`](legal/) (court-facing drafts), [`evidence/`](evidence/) (authenticated
data), [`takedowns/`](takedowns/), [`damages/`](damages/),
[`case_package/`](case_package/) (assembled bundle).

## 9. Reproduce / verify (engineers)
```powershell
pip install -r requirements.txt
python evidence_store.py evidence   # verify all SHA-256 hashes -> all OK
python run_tests.py                 # 81 integrity / validation checks
```
See [`AGENTS.md`](AGENTS.md) for the full command set and
[`HANDOVER.md`](HANDOVER.md) for architecture and rules.
