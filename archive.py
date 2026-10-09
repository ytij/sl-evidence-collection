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
import csv
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "captures")
ALL_CSV = os.path.join(HERE, "sophie_little_all_videos.csv")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

LIVE_CSV = os.path.join(HERE, "sophie_little_live_videos.csv")


def live_guids():
    with open(LIVE_CSV, encoding="utf-8-sig") as fh:
        return [r["guid"] for r in csv.DictReader(fh)]


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
    guids = live_guids()
    if limit:
        guids = guids[:limit]

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
