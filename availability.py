#!/usr/bin/env python3
"""Availability audit — validate what is still up vs taken down, as an
append-only, timestamped snapshot.

Reads the baseline work list from `sophie_little_all_videos.csv` (never
modified), re-fetches the live catalog + tag table, and re-probes every stream
URL fresh (bypassing caches). Writes a NEW immutable snapshot under
`evidence/availability/<UTC>/` and appends a hash record to
`evidence/availability/index.json`. Existing evidence files are never touched.

Usage:
    python availability.py                 # probe all 624 streams + fetch sources
    python availability.py --no-probe      # sources only (catalog/meta), no stream probes
    python availability.py --workers 6 --delay 0.2
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sophie_scrape import (
    BUNNY_FN, PAGE_SIZE, PULL_ZONE, SITE, SUPA, SUPA_KEY,
    HostRateLimiter, PoliteSession,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(HERE, "sophie_little_all_videos.csv")
AVAIL_DIR = os.path.join(HERE, "evidence", "availability")
INDEX = os.path.join(AVAIL_DIR, "index.json")
REFERER = f"{SITE}/"

STREAM_ACCEPT = "application/vnd.apple.mpegurl,*/*;q=0.8"


def now_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_baseline():
    with open(BASELINE, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def fetch_catalog(session):
    guids, total, page = set(), None, 1
    while True:
        r = session.get(BUNNY_FN, params={"page": page, "perPage": 500},
                        headers={"Accept": "application/json"})
        r.raise_for_status()
        d = r.json()
        total = d.get("totalItems", total)
        items = d.get("items") or []
        for it in items:
            if it.get("guid"):
                guids.add(it["guid"])
        if not items or len(items) < 500:
            break
        page += 1
    return guids, total


def fetch_meta(session):
    rows, offset = [], 0
    while True:
        r = session.get(
            f"{SUPA}/rest/v1/video_meta?select=guid,tags&order=guid&limit={PAGE_SIZE}&offset={offset}",
            headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                     "Accept": "application/json"})
        r.raise_for_status()
        b = r.json()
        rows.extend(b)
        if len(b) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def probe_stream(session, url):
    try:
        r = session.get(url, headers={"Accept": STREAM_ACCEPT}, referer=REFERER, stream=True)
        status, ctype = r.status_code, r.headers.get("Content-Type", "")
        r.close()
        return status, ctype
    except Exception as exc:  # noqa: BLE001
        return f"ERR:{exc.__class__.__name__}", ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--catalog-only", action="store_true",
                    help="probe only works still in the catalog (+ previously-live); avoids mass CDN traffic")
    ap.add_argument("--note", default="", help="free-text note recorded in the snapshot")
    args = ap.parse_args()

    baseline = load_baseline()
    limiter = HostRateLimiter(args.delay, 1.0, 120, (3.0, 10.0))
    session = PoliteSession(limiter)

    print("fetching catalog + tag table ...")
    catalog_guids, catalog_total = fetch_catalog(session)
    meta_rows = fetch_meta(session)
    meta_guids = {m["guid"] for m in meta_rows}
    print(f"  catalog {catalog_total} items | video_meta {len(meta_rows)} rows")

    works = []
    for r in baseline:
        guid = r["guid"]
        works.append({
            "guid": guid,
            "title": r.get("title", ""),
            "stream_url": r.get("stream_url", ""),
            "thumbnail_url": r.get("thumbnail_url", ""),
            "prior_status": r.get("stream_http_status", ""),
            "prior_in_catalog": r.get("in_catalog", ""),
            "now_in_catalog": guid in catalog_guids,
            "in_meta": guid in meta_guids,
            "now_status": "",
            "content_type": "",
        })

    probe_set = works
    if args.catalog_only:
        probe_set = [w for w in works if w["now_in_catalog"] or w["prior_status"] == "200"]
    probe_guids = {w["guid"] for w in probe_set}
    for w in works:
        if w["guid"] not in probe_guids:
            w["now_status"] = "not_probed"

    if not args.no_probe:
        print(f"re-probing {len(probe_set)} stream URLs (workers={args.workers}) ...")

        def work(w):
            w["now_status"], w["content_type"] = probe_stream(session, w["stream_url"])
            return w

        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for _ in as_completed([pool.submit(work, w) for w in probe_set]):
                done += 1
                if done % 50 == 0 or done == len(probe_set):
                    sys.stderr.write(f"\r  probed {done}/{len(probe_set)}")
                    sys.stderr.flush()
        sys.stderr.write("\n")

    # classify deltas
    for w in works:
        w["prior_live"] = str(w["prior_status"]) == "200"
        w["now_live"] = str(w["now_status"]) == "200"
        if w["now_status"] in ("", "not_probed"):
            w["delta"] = "NOT_PROBED"
        elif w["prior_live"] and not w["now_live"]:
            w["delta"] = "TAKEN_DOWN_SINCE"
        elif w["prior_live"] and w["now_live"]:
            w["delta"] = "STILL_LIVE"
        elif not w["prior_live"] and w["now_live"]:
            w["delta"] = "NEWLY_LIVE"
        else:
            w["delta"] = "STILL_DOWN"

    stamp = now_stamp()
    out_dir = os.path.join(AVAIL_DIR, stamp)
    os.makedirs(out_dir, exist_ok=True)

    snapshot = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "baseline_file": "sophie_little_all_videos.csv",
        "catalog_total": catalog_total,
        "catalog_guids": len(catalog_guids),
        "video_meta_rows": len(meta_rows),
        "works_audited": len(works),
        "note": args.note,
        "summary": {
            "probed": sum(1 for w in works if w["now_status"] not in ("", "not_probed")),
            "now_live": sum(1 for w in works if w["now_live"]),
            "taken_down_since": sum(1 for w in works if w["delta"] == "TAKEN_DOWN_SINCE"),
            "still_live": sum(1 for w in works if w["delta"] == "STILL_LIVE"),
            "newly_live": sum(1 for w in works if w["delta"] == "NEWLY_LIVE"),
            "still_down": sum(1 for w in works if w["delta"] == "STILL_DOWN"),
            "not_probed": sum(1 for w in works if w["delta"] == "NOT_PROBED"),
        },
        "works": works,
    }
    snap_json = os.path.join(out_dir, "snapshot.json")
    with open(snap_json, "w", encoding="utf-8", newline="") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)

    snap_csv = os.path.join(out_dir, "snapshot.csv")
    with open(snap_csv, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(works[0].keys()))
        w.writeheader()
        w.writerows(works)

    # append-only index (never overwritten; each run adds a record)
    index = []
    if os.path.exists(INDEX):
        with open(INDEX, encoding="utf-8") as fh:
            index = json.load(fh)
    index.append({
        "audited_at": snapshot["audited_at"],
        "dir": os.path.relpath(out_dir, HERE).replace("\\", "/"),
        "snapshot_json_sha256": sha256_file(snap_json),
        "snapshot_csv_sha256": sha256_file(snap_csv),
        "summary": snapshot["summary"],
        "catalog_total": catalog_total,
        "video_meta_rows": len(meta_rows),
    })
    os.makedirs(AVAIL_DIR, exist_ok=True)
    with open(INDEX, "w", encoding="utf-8", newline="") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)

    s = snapshot["summary"]
    print(f"\nsnapshot: {os.path.relpath(snap_json, HERE)}")
    print(f"  works={len(works)} now_live={s['now_live']} "
          f"taken_down_since={s['taken_down_since']} still_live={s['still_live']} "
          f"newly_live={s['newly_live']} still_down={s['still_down']}")
    print(f"  catalog_total={catalog_total} video_meta_rows={len(meta_rows)}")


if __name__ == "__main__":
    main()
