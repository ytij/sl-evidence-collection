#!/usr/bin/env python3
"""Submit the infringing pages to the Internet Archive (Wayback) for
independent, third-party corroboration that they existed.

Wayback is operated by a third party, so its snapshots survive even if the
operator deletes the originals — useful evidence-preservation insurance.

Outputs captures/archive.json (with hashes/timestamps).

Usage:
    python archive.py                 # submits the attributed works' pages
    python archive.py --limit 3       # only the first N
"""

import hashlib
import json
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "captures")
ALL_CSV = os.path.join(HERE, "sophie_little_all_videos.csv")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

ATTRIBUTED_GUIDS = [
    "8f71399f-5565-497a-944f-466ad42b0271", "9627aedf-d3d6-4a5a-8141-6467c764a33a",
    "4478076e-76ec-42d9-886b-a61ba179235a", "39b63ca2-4e5a-406c-94bd-3fb72d55a879",
    "710142df-923e-4ad3-80d0-c7a87391fc3e", "cbc1420c-cd65-4f92-b06c-73092650ab13",
    "c1904e3e-e123-4ddb-8830-b53a7c55a31e", "f64107b2-9919-4c19-99ce-115eaf90432a",
    "02f46a22-2881-4dfa-a888-7f0dfbf3aefb", "50e8212f-eec5-465a-a080-42f4e09fd7f6",
    "26cf42e4-3fb8-44da-9822-7758b3a692fc", "03bfd473-3c67-4bae-aee1-ee7120b6664c",
]


def snapshot_url(session, url):
    r = session.get("https://archive.org/wayback/available",
                    params={"url": url}, timeout=30)
    if r.status_code == 200:
        data = r.json()
        snap = data.get("archived_snapshots", {}).get("closest")
        if snap and snap.get("available"):
            return snap.get("url")
    return None


def save_page(session, url):
    r = session.get(f"https://web.archive.org/save/{url}", timeout=120,
                    headers={"User-Agent": UA}, allow_redirects=True)
    loc = r.headers.get("Content-Location") or r.headers.get("Location")
    if loc and loc.startswith("/web/"):
        return "https://web.archive.org" + loc.split("?")[0]
    return snapshot_url(session, url)


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    guids = ATTRIBUTED_GUIDS[:limit] if limit else ATTRIBUTED_GUIDS

    os.makedirs(OUT, exist_ok=True)
    session = requests.Session()
    records = []
    for i, g in enumerate(guids, 1):
        page = f"https://abdlhub.com/?v={g}"
        try:
            archived = save_page(session, page)
            status = "ok" if archived else "no-snapshot"
        except requests.RequestException as exc:
            archived, status = None, f"ERR:{exc.__class__.__name__}"
        rec = {"guid": g, "page_url": page, "archived_url": archived, "status": status,
               "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        records.append(rec)
        print(f"[{i}/{len(guids)}] {status:12s} {g} -> {archived}")
        time.sleep(3)  # be polite to the archive

    path = os.path.join(OUT, "archive.json")
    payload = {"count": len(records), "records": records}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    print(f"wrote {path} (sha256 {hashlib.sha256(text.encode()).hexdigest()[:16]})")


if __name__ == "__main__":
    main()
