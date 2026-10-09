# Court-facing documentation → authorities

Mapping of every document this project must produce (to authenticate evidence,
prove the claim, and recover) to the controlling authority, with the source
used to verify it. Structured data: `legal/authorities.json`.

**Verified 2026-10-09.** Primary text for the statutes/rules was fetched from
`law.cornell.edu` (U.S. Code, Federal Rules of Evidence) and
`leg.state.fl.us` (Florida Statutes); the Supreme Court decision was confirmed
via `courtlistener.com`. Entries marked **unverified** are standard citations
recorded for counsel to confirm.

> This is research to hand to counsel — **not legal advice**.

## Authorities

| ID | Citation | Ver. | Requirement (short) |
| --- | --- | --- | --- |
| USC17-411 | 17 U.S.C. § 411(a) | ✅ | Registration required to sue on a "United States work"; foreign works exempt from § 411(a) but not § 412. |
| USC17-412 | 17 U.S.C. § 412 | ✅ | No statutory damages/fees unless registration precedes infringement or is timely (≤ 3 months after first publication). |
| USC17-501 | 17 U.S.C. § 501 | ✅ | Defines infringement; owner may sue subject to § 411. |
| USC17-504 | 17 U.S.C. § 504(b),(c) | ✅ | Actual damages + profits; statutory $750–$30k/work, up to $150k willful; § 504(c)(3) registrar-false-info willfulness presumption. |
| USC17-505 | 17 U.S.C. § 505 | ✅ | Discretionary costs and attorney's fees (subject to § 412). |
| USC17-512 | 17 U.S.C. § 512(c)(3),(d),(f),(h) | ✅ | Six notice elements; info-location tools; misrepresentation liability; § 512(h) identification subpoena. |
| USC28-1338 | 28 U.S.C. § 1338(a) | ✅ | Exclusive federal jurisdiction over copyright claims. |
| USC28-1400 | 28 U.S.C. § 1400(a) | ✅ | Copyright venue where defendant resides or may be found. |
| USC28-1746 | 28 U.S.C. § 1746 | ✅ | Unsworn declarations under penalty of perjury — the certification vehicle. |
| FRE-901 | Fed. R. Evid. 901(b)(1),(9) | ✅ | Authentication; process/system producing accurate results. |
| FRE-902 | Fed. R. Evid. 902(13),(14) | ✅ | Self-authentication of electronic records and hashed data by certification. |
| FL-48.193 | Fla. Stat. § 48.193(1)(a)2,(2) | ✅ | Florida long-arm: tortious act in-state; substantial activity. |
| CASE-fourth-estate | Fourth Estate v. Wall-Street.com, 586 U.S. 296 (2019) | ✅ | Registration "made" only when the Office acts. |
| USC17-410 | 17 U.S.C. § 410(c) | ⚠️ | Registration certificate is prima facie evidence of validity. |
| USC17-101 | 17 U.S.C. § 101 | ⚠️ | "United States work" definition. |
| USC17-104 | 17 U.S.C. § 104 | ⚠️ | Protection for foreign works (Berne). |
| USC17-106 | 17 U.S.C. § 106(1),(4),(5) | ⚠️ | Exclusive rights infringed by rehosting. |
| FRCP-45 | Fed. R. Civ. P. 45 | ⚠️ | Third-party subpoenas. |
| FRCP-65 | Fed. R. Civ. P. 65 | ⚠️ | Injunctions / TRO. |
| FRCP-37 | Fed. R. Civ. P. 37(e) | ⚠️ | ESI spoliation sanctions. |
| CASE-lorraine | Lorraine v. Markel Am. Ins. Co., 241 F.R.D. 534 (D. Md. 2007) | ⚠️ | ESI authentication framework. |
| CASE-bansal | United States v. Bansal, 663 F.3d 634 (3d Cir. 2011) | ⚠️ | Web-page authentication. |
| CASE-mitchell | Mitchell Bros. Film Grp. v. Cinema Adult Theater, 604 F.2d 852 (5th Cir. 1979) | ⚠️ | Obscenity does not defeat copyrightability. |
| CASE-calder | Calder v. Jones, 465 U.S. 783 (1984) | ⚠️ | Effects test for personal jurisdiction. |
| CASE-walden | Walden v. Fiore, 571 U.S. 277 (2014) | ⚠️ | Minimum contacts must be the defendant's own. |
| CASE-zubulake | Zubulake v. UBS Warburg LLC, 220 F.R.D. 212 (S.D.N.Y. 2003) | ⚠️ | Duty to preserve evidence. |
| CASE-feist | Feist Publ'ns v. Rural Tel. Serv. Co., 499 U.S. 340 (1991) | ⚠️ | Originality requirement. |

✅ verified this session · ⚠️ standard citation, confirm with counsel

## Documentation elements → what satisfies them

| ID | Element | Authorities | Artifact in repo | Status |
| --- | --- | --- | --- | --- |
| E1 | Chain of custody / integrity | FRE-901, FRE-902, USC28-1746, CASE-lorraine | `evidence/manifest.json`, `evidence/timestamps/`, `evidence_store.py`, capture manifest | partial |
| E2 | Authentication of web captures | FRE-901, FRE-902, CASE-bansal, CASE-lorraine | `capture.py`, capture manifest | partial |
| E3 | Ownership & authorship | USC17-410, CASE-mitchell, CASE-feist | — | missing |
| E4 | Registration-to-sue | USC17-411, CASE-fourth-estate | — | missing |
| E5 | Timely registration | USC17-412, USC17-410 | — | missing |
| E6 | Infringement elements | USC17-501, USC17-106 | `takedowns/takedown_index.csv`, live CSV | partial |
| E7 | DMCA § 512(c) notices | USC17-512 | `takedowns/dmca_notice_*.txt` | satisfied |
| E8 | Identity subpoena | USC17-512, FRCP-45 | `osint/SUBPOENA_TARGETS.md` | partial |
| E9 | Search delisting | USC17-512 | — | missing |
| E10 | Damages proof | USC17-504, USC17-412 | `damages/` | partial |
| E11 | Fees & costs | USC17-505, USC17-412 | `damages/damages.json` | partial |
| E12 | Injunction / impoundment | FRCP-65 | — | missing |
| E13 | Litigation hold / preservation | FRCP-37, CASE-zubulake | `evidence/manifest.json` | partial |
| E14 | Personal jurisdiction (FL) | FL-48.193, CASE-calder, CASE-walden | `osint/PUBLIC_EXPOSURE.md` | partial |
| E15 | Venue | USC28-1400 | — | missing |
| E16 | Subject-matter jurisdiction | USC28-1338 | — | missing |
| E17 | Foreign-author standing / Berne | USC17-104, USC17-101, USC17-411, USC17-501 | — | missing |
| E18 | Declaration form (§ 1746) | USC28-1746, FRE-902 | — | missing |
| E19 | Willfulness | USC17-504 | `osint/PUBLIC_EXPOSURE.md`, `evidence/comments.json` | partial |

Allowed status values: `satisfied`, `partial`, `missing`.

## Key nuances counsel must resolve
1. **"United States work" (§ 101/§ 411).** Registration-to-sue (§ 411) turns on
   whether the works are U.S. works (first publication on a U.S. platform may
   make them so). Regardless, **§ 412 applies to all works** — timely
   registration is needed for statutory damages and fees.
2. **§ 504(c)(3) willfulness presumption.** Providing materially false contact
   information to a domain registrar creates a rebuttable presumption of
   willfulness. Our OSINT already flags domain/registrar pivots
   (`osint/SUBPOENA_TARGETS.md`) — test this once registrar data is obtained.
3. **Content nature.** Adult age-play between adults does not defeat copyright
   (*Mitchell Bros.*); keep works framed by authorship, never minor-coded
   elements (see `HANDOVER.md` §11).

_Verification is reproducible: see `tests/test_legal.py`._
