#!/usr/bin/env python3
"""Generate DMCA § 512(c) takedown packages from the collected evidence.

Reads the attributed submissions (evidence/video_submissions.json) and the
URL index (sophie_little_*.csv) and emits:

    takedowns/takedown_index.csv      one row per infringing work
    takedowns/dmca_notice_abdlhub.txt notice to the site operator
    takedowns/dmca_notice_netlify.txt notice to the site host
    takedowns/dmca_notice_bunny.txt   notice to the media CDN (Bunny Stream)
    takedowns/dmca_notice_supabase.txt notice to the metadata backend

Placeholders in [BRACKETS] must be filled by the complainant / counsel before
sending. Nothing here is sent automatically.

Usage:
    python takedown.py
"""

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "evidence")
OUT = os.path.join(HERE, "takedowns")
ALL_CSV = os.path.join(HERE, "sophie_little_all_videos.csv")
LIVE_CSV = os.path.join(HERE, "sophie_little_live_videos.csv")

# The account that uploaded the "Sofia"/creator rehosts (see osint/PUBLIC_EXPOSURE.md).
ATTRIBUTED_UPLOADER = "a89bb9dc-d09f-4475-b9ed-ae398edf928b"
TITLE_PATTERN = re.compile(r"sofia", re.I)


def load_rows(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        return {r["guid"]: r for r in csv.DictReader(fh)}


def guid_of(url):
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url or "")
    return m.group(1) if m else None


def build_works():
    subs = json.load(open(os.path.join(EVIDENCE, "video_submissions.json"), encoding="utf-8"))["rows"]
    url_rows = load_rows(ALL_CSV)
    live = load_rows(LIVE_CSV)
    works = []
    for s in subs:
        if s.get("user_id") != ATTRIBUTED_UPLOADER and not TITLE_PATTERN.search(s.get("title") or ""):
            continue
        g = guid_of(s.get("video_url"))
        row = url_rows.get(g, {})
        works.append({
            "submission_id": s["id"],
            "title": s["title"],
            "guid": g,
            "page_url": row.get("page_url", f"https://abdlhub.com/?v={g}"),
            "thumbnail_url": row.get("thumbnail_url", ""),
            "stream_url": row.get("stream_url", f"https://vz-e81debcf-c73.b-cdn.net/{g}/playlist.m3u8"),
            "submitted_at": s["created_at"],
            "file_size_bytes": s.get("file_size") or "",
            "uploader_user_id": s["user_id"],
            "live": g in live,
        })
    works.sort(key=lambda w: (w["submitted_at"] or ""))
    return works


def write_index(works):
    path = os.path.join(OUT, "takedown_index.csv")
    fields = list(works[0].keys()) if works else []
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(works)
    return path


def works_block(works):
    lines = []
    for i, w in enumerate(works, 1):
        lines.append(f"{i}. \"{w['title']}\"")
        lines.append(f"   Infringing page : {w['page_url']}")
        lines.append(f"   Media URL       : {w['stream_url']}")
        lines.append(f"   Thumbnail       : {w['thumbnail_url']}")
        lines.append(f"   Uploaded        : {w['submitted_at']} (Bunny guid {w['guid']})")
    return "\n".join(lines)


def notice(recipient_block, works, extra=""):
    return f"""\
DMCA § 512(c)(3) NOTIFICATION OF COPYRIGHT INFRINGEMENT
[PREPARED FOR COUNSEL REVIEW — DO NOT SEND UNTIL COMPLETED]

To: {recipient_block}
Date: [DATE]

I am the owner, or an agent authorized to act on behalf of the owner, of
exclusive rights under copyright in the works listed below.

1. Identification of the copyrighted works:
   [DESCRIBE / LIST THE ORIGINAL WORKS — titles, publication dates, and US
   Copyright Office registration numbers if any.]

2. Identification of the infringing material (URLs):
{works_block(works)}

3. Contact information of the complaining party:
   Name:    [COMPLAINANT NAME]
   Address: [STREET, CITY, STATE/PROVINCE, POSTAL, COUNTRY]
   Phone:   [PHONE]
   Email:   [EMAIL]

4. Statement of good faith: I have a good-faith belief that the use of the
   material described above is not authorized by the copyright owner, its
   agent, or the law.

5. Statement under penalty of perjury: The information in this notification
   is accurate, and I am the copyright owner or am authorized to act on behalf
   of the owner of an exclusive right that is allegedly infringed.

6. Electronic signature: /s/ [COMPLAINANT NAME]

Supporting evidence (hashes + RFC 3161 timestamp) is catalogued under
evidence/ (see evidence/manifest.json and evidence/timestamps/index.json).
{extra}
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    works = build_works()
    if not works:
        sys.exit("no attributed works found — run osint/public_exposure.py first")
    index = write_index(works)

    notices = {
        "dmca_notice_abdlhub.txt": notice("abdlhub.com / site operator [AND its designated DMCA agent, if any]", works),
        "dmca_notice_netlify.txt": notice("Netlify, Inc. — Abuse / DMCA (host of abdlhub.com)", works,
                                          extra="\nSite is served by Netlify (Server: Netlify); see osint/SITE_CATALOG.md."),
        "dmca_notice_bunny.txt": notice("Bunny.net / BunnyCDN — Abuse (pull zone vz-e81debcf-c73.b-cdn.net, library 621930)", works,
                                        extra="\nMedia is served by Bunny Stream/CDN; see osint/SITE_CATALOG.md."),
        "dmca_notice_supabase.txt": notice("Supabase, Inc. — Abuse (project hbvwlzjxsmhreeqwypwp)", works,
                                           extra="\nMetadata backend is Supabase/PostgREST; uploader user_id "
                                                 f"{ATTRIBUTED_UPLOADER}."),
    }
    for name, text in notices.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)

    print(f"{len(works)} works; live={sum(1 for w in works if w['live'])}")
    print(f"wrote {index}")
    for name in notices:
        print(f"wrote {os.path.join(OUT, name)}")


if __name__ == "__main__":
    main()
