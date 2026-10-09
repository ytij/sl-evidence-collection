#!/usr/bin/env python3
"""Generate the data-driven court-facing drafts.

  legal/EXHIBIT_INDEX.md            exhibits with hashes + timestamp refs
  legal/preservation/<provider>.txt litigation-hold / preservation letters

Hand-written instruments that this complements: legal/METHODOLOGY.md,
legal/DECLARATION_1746.md, legal/SUBPOENA_512h.md.

Usage:
    python build_legal.py
"""

import csv
import hashlib
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
LEGAL = os.path.join(HERE, "legal")
WORKS_INDEX = os.path.join(HERE, "takedowns", "takedown_index.csv")

EXHIBITS = [
    ("A", "Attribution of the rehosted works",
     "osint/PUBLIC_EXPOSURE.md",
     "Links all 12 subject rehosts to the uploading account and the operator/mod accounts."),
    ("B", "Index of infringing works and URLs",
     "takedowns/takedown_index.csv",
     "Per-work page URL, stream URL, thumbnail URL, uploader id, and submission timestamp."),
    ("C", "Raw backend data snapshots",
     "evidence/manifest.json",
     "Twelve Supabase/Bunny tables captured verbatim with SHA-256 hashes and provenance."),
    ("D", "Rendered page captures (HTML/PNG/PDF)",
     "captures/20261009T050349Z/manifest.json",
     "Each live page captured as served, age gate dismissed, with per-file hashes."),
    ("E", "Independent third-party archival (Wayback)",
     "captures/archive.json",
     "Third-party snapshots that survive deletion of the originals."),
    ("F", "Site technology & infrastructure report",
     "osint/SITE_CATALOG.md",
     "Hosting, CDN, backend, ad/analytics stack and the public access surface."),
    ("G", "RFC 3161 timestamp tokens",
     "evidence/timestamps/index.json",
     "Trusted timestamps over the evidence and capture manifests."),
    ("H", "Damages computation",
     "damages/damages.json",
     "Work count, sizes, views, the infringement window, and the § 504(c) matrix."),
    ("I", "Legal authority mapping",
     "legal/AUTHORITIES.md",
     "Each required element mapped to a controlling authority with verified sources."),
]

PROVIDERS = [
    {
        "slug": "supabase",
        "name": "Supabase, Inc.",
        "role": "operator of the metadata backend (PostgREST/GoTrue) for abdlhub.com",
        "identifiers": [
            "Project reference: hbvwlzjxsmhreeqwypwp (hbvwlzjxsmhreeqwypwp.supabase.co)",
            "Uploading account username 'Creator1', user_id a89bb9dc-d09f-4475-b9ed-ae398edf928b",
            "Operator account 'Admin', user_id 46a556ca-1789-4dd9-a72d-bbe6df94e5c9",
            "Records: video_submissions, user_profiles, video_meta, comments, site_config",
        ],
    },
    {
        "slug": "bunny",
        "name": "Bunny.net (BunnyWay d.o.o.)",
        "role": "operator of the CDN/Stream service hosting the infringing video files",
        "identifiers": [
            "Stream library: 621930",
            "Pull zone: vz-e81debcf-c73.b-cdn.net",
            "Storage zone: abdlhub-images.b-cdn.net",
            "12 offending media GUIDs listed in Exhibit B",
        ],
    },
    {
        "slug": "netlify",
        "name": "Netlify, Inc.",
        "role": "web host and DNS provider for abdlhub.com",
        "identifiers": [
            "Domain: abdlhub.com (DNS via nsone.net / Netlify Domains)",
            "Serverless functions: bunny-videos, request-upload, set-title, upload-avatar",
            "Account billing/identity and function logs for abdlhub.com",
        ],
    },
    {
        "slug": "exoclick",
        "name": "ExoClick (Exo Group)",
        "role": "advertising network monetising the infringing pages",
        "identifiers": [
            "Ad zones: 6009644, 6016956, 6011096, 6012920",
            "Payee identity, payout method, and revenue for those zones",
        ],
    },
]

PRESERVATION_TEMPLATE = """\
[LETTERHEAD OF COUNSEL]
[DATE]

VIA EMAIL AND CERTIFIED MAIL
Preservation / Legal Hold Notice
Re: [CLIENT NAME] v. [DEFENDANT — to be identified]; Copyright Infringement
    of works published on abdlhub.com

To: {name} — Legal / Trust & Safety
    {role}

Dear Sir or Madam:

This firm represents [CLIENT], the owner of copyrighted works that appear to
have been reproduced and publicly distributed without authorization on the
website abdlhub.com (the "Site"). Litigation is reasonably anticipated. This
letter is a demand that {name} preserve, and refrain from deleting or altering,
all records in its possession, custody, or control relating to the Site and the
following specific identifiers:

{id_block}

Please preserve, at minimum, the following categories of records (including
metadata and, where applicable, the contents themselves), and suspend any
auto-deletion or retention policy that would otherwise purge them:

  1. Account registration and billing records (name, address, email, phone,
     payment method) for the accounts associated with the identifiers above.
  2. Connection/access logs, including IP addresses, user agents, and
     timestamps of uploads, API calls, and downloads.
  3. The uploaded content and any associated filenames, thumbnails, and
     metadata.
  4. Communications with the account holder(s) and with any third party about
     the content or the Site.

This request covers records regardless of the medium or system on which they
reside, including backups, archives, and logs. If any responsive records are
subject to a routine destruction policy, please preserve them pending
resolution of this matter. Failure to preserve may result in sanctions under
Fed. R. Civ. P. 37(e).

Please confirm in writing, within ten (10) business days, that these records
have been preserved and identify the custodian responsible for them. Nothing
in this letter waives any right or remedy; all rights are expressly reserved.

Very truly yours,

[SIGNATURE]
[COUNSEL NAME], Esq.
[FIRM] | [ADDRESS] | [PHONE] | [EMAIL]
"""


def sha256(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_works():
    if not os.path.exists(WORKS_INDEX):
        return []
    with open(WORKS_INDEX, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_exhibit_index(works):
    lines = []
    lines.append("# Exhibit index")
    lines.append("")
    lines.append(f"_Generated {date.today().isoformat()} by `build_legal.py`._ "
                 "Hashes are SHA-256 of the listed artifact; timestamp column refers to "
                 "`evidence/timestamps/index.json`.")
    lines.append("")
    lines.append("| Ex. | Description | Artifact | SHA-256 | Proves |")
    lines.append("| --- | --- | --- | --- | --- |")
    for tag, desc, rel, proves in EXHIBITS:
        digest = sha256(os.path.join(HERE, rel)) or "(directory — see its manifest)"
        d = digest if len(digest) <= 20 else digest[:20] + "…"
        lines.append(f"| {tag} | {desc} | `{rel}` | `{d}` | {proves} |")
    lines.append("")
    lines.append(f"## Exhibit B — {len(works)} infringing works")
    lines.append("")
    lines.append("| # | Title | Page URL | Uploaded | Bytes |")
    lines.append("| --- | --- | --- | --- | --- |")
    for i, w in enumerate(works, 1):
        lines.append(f"| {i} | {w['title'][:70]} | {w['page_url']} | "
                     f"{w['submitted_at'][:10]} | {w['file_size_bytes']} |")
    lines.append("")
    lines.append("_See `HANDOVER.md` §5 and `osint/PUBLIC_EXPOSURE.md` for the attribution "
                 "of the uploads to account `Creator1`._")
    lines.append("")
    path = os.path.join(LEGAL, "EXHIBIT_INDEX.md")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines))
    return path


def write_preservation_letters():
    out_dir = os.path.join(LEGAL, "preservation")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for p in PROVIDERS:
        block = "\n".join(f"   - {x}" for x in p["identifiers"])
        text = PRESERVATION_TEMPLATE.format(name=p["name"], role=p["role"], id_block=block)
        path = os.path.join(out_dir, f"{p['slug']}.txt")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        written.append(path)
    return written


def main():
    os.makedirs(LEGAL, exist_ok=True)
    works = load_works()
    idx = write_exhibit_index(works)
    letters = write_preservation_letters()
    print(f"wrote {idx} ({len(works)} works)")
    for p in letters:
        print(f"wrote {os.path.relpath(p, HERE).replace(chr(92), '/')}")


if __name__ == "__main__":
    main()
