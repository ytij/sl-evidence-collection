#!/usr/bin/env python3
"""Preserve the thumbnails of delisted (orphaned) works, low-and-slow.

Why this matters: 610 of the 624 matching works have already been removed from
the media library — their HLS streams 404 — and only the CDN-cached thumbnail
and the database row remain. The thumbnails are the last remnant proving the
works existed on the site, and they can be purged at any time.

THREAT / STEALTH ANALYSIS  (read before running)
------------------------------------------------
The specific difficulty here is that these are *orphaned* assets: because the
publish pages were delisted from the site's grid, **no legitimate visitor ever
requests these thumbnails**. There is therefore no way to make the fetches
"look normal" at the origin — any request for them is inherently anomalous.
Stealth can only be achieved by (a) keeping the total footprint tiny and
one-time, (b) spreading it over a long window so no burst is visible, and
(c) making each request individually indistinguishable from an ordinary image
load by the site's own front end.

Controls implemented:
  * Serial (workers=1) with per-host pacing, jitter, and a long pause every N
    requests, so the average rate is ~1 thumbnail / 8-15 s by default.
  * Browser-realistic request for the image: image `Accept`, `Sec-Fetch-Dest:
    image`, and a `Referer` of the work's own page (the way the site's front
    end would load it).
  * **Incremental and resumable**: already-preserved thumbnails are skipped, so
    re-runs make zero requests. Use `--limit` to split the set across days.
  * Randomized order, so no scripted sequential pattern.
  * `--max-requests` hard cap.
  * Optional: authorize fetching via the site's own page path is unnecessary;
    the CDN requires only the site `Referer`, which we send.

Recommended rollout (do NOT run all 610 at once): e.g.
    python preserve_thumbs.py --limit 60      # ~10 min, once a day for ~10 days
Each run only fetches what is still missing.

Usage:
    python preserve_thumbs.py --dry-run       # list what would be fetched (0 requests)
    python preserve_thumbs.py --limit 25      # fetch 25 this run
    python preserve_thumbs.py --include-live  # also snapshot the 14 live ones
    python preserve_thumbs.py --verify        # re-verify stored hashes
"""

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone

from sophie_scrape import HostRateLimiter, PoliteSession

HERE = os.path.dirname(os.path.abspath(__file__))
ALL_CSV = os.path.join(HERE, "sophie_little_all_videos.csv")
THUMB_DIR = os.path.join(HERE, "captures", "thumbs")
MANIFEST = os.path.join(THUMB_DIR, "manifest.json")

IMG_HEADERS = {
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Sec-Fetch-Dest": "image",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Site": "cross-site",
}

EXT = {
    "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
    "image/webp": ".webp", "image/gif": ".gif", "image/avif": ".avif",
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    return {"generated_at": now_iso(), "entries": {}}


def save_manifest(m):
    os.makedirs(THUMB_DIR, exist_ok=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        json.dump(m, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


def load_targets(include_live):
    with open(ALL_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    out = []
    for r in rows:
        live = r["stream_http_status"] == "200"
        if live and not include_live:
            continue
        out.append(r)
    return out


def verify():
    if not os.path.exists(MANIFEST):
        print("no manifest yet")
        return 1
    m = load_manifest()
    bad = 0
    for guid, e in sorted(m.get("entries", {}).items()):
        if e.get("status") != 200 or not e.get("file"):
            continue
        p = os.path.join(THUMB_DIR, e["file"])
        if not os.path.exists(p):
            print(f"MISSING  {guid}")
            bad += 1
        elif sha256(p) != e.get("sha256"):
            print(f"MISMATCH {guid}")
            bad += 1
    print(f"verified {len(m.get('entries', {}))} entries; problems: {bad}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delay", type=float, default=4.0, help="base seconds between requests (default 4)")
    ap.add_argument("--jitter", type=float, default=1.5, help="random extra fraction of delay (default 1.5)")
    ap.add_argument("--long-pause-every", type=int, default=20, help="long pause every N requests (default 20)")
    ap.add_argument("--limit", type=int, default=0, help="max thumbnails this run (0 = all)")
    ap.add_argument("--max-requests", type=int, default=0, help="hard request cap (0 = unlimited)")
    ap.add_argument("--include-live", action="store_true", help="also snapshot the live works")
    ap.add_argument("--recheck", action="store_true", help="re-fetch even if already preserved")
    ap.add_argument("--dry-run", action="store_true", help="list targets, make no requests")
    ap.add_argument("--verify", action="store_true", help="re-verify stored hashes and exit")
    args = ap.parse_args()

    if args.verify:
        sys.exit(verify())

    manifest = load_manifest()
    entries = manifest.setdefault("entries", {})
    targets = load_targets(args.include_live)

    pending = []
    for r in targets:
        guid = r["guid"]
        prior = entries.get(guid)
        if prior and prior.get("status") == 200 and not args.recheck:
            f = prior.get("file")
            if f and os.path.exists(os.path.join(THUMB_DIR, f)):
                continue
        pending.append(r)

    preserved = len(targets) - len(pending)
    random.shuffle(pending)
    if args.limit:
        pending = pending[: args.limit]

    print(f"targets: {len(targets)} | already preserved: {preserved} | "
          f"will fetch: {len(pending)}")
    if args.dry_run:
        for r in pending[:10]:
            print("  ", r["guid"], r["thumbnail_url"])
        if len(pending) > 10:
            print(f"   ... (+{len(pending) - 10} more)")
        return

    os.makedirs(THUMB_DIR, exist_ok=True)
    limiter = HostRateLimiter(args.delay, args.jitter, args.long_pause_every, (30.0, 120.0))
    session = PoliteSession(limiter, args.max_requests)

    saved = skipped = failed = 0
    for i, r in enumerate(pending, 1):
        guid = r["guid"]
        url = r["thumbnail_url"]
        referer = f"https://abdlhub.com/?v={guid}"
        try:
            resp = session.get(url, headers=IMG_HEADERS, referer=referer, stream=True)
            status = resp.status_code
            ctype = resp.headers.get("Content-Type", "")
            etag = resp.headers.get("ETag", "")
            if status == 200 and ctype.startswith("image/"):
                data = resp.content
                ext = EXT.get(ctype.split(";")[0].strip(), ".bin")
                fname = f"{guid}{ext}"
                fpath = os.path.join(THUMB_DIR, fname)
                with open(fpath, "wb") as fh:
                    fh.write(data)
                entries[guid] = {
                    "file": fname, "url": url, "status": 200, "content_type": ctype,
                    "bytes": len(data), "sha256": sha256(fpath), "etag": etag,
                    "fetched_at": now_iso(), "live": r["stream_http_status"] == "200",
                }
                saved += 1
            else:
                entries[guid] = {"file": None, "url": url, "status": status,
                                 "content_type": ctype, "fetched_at": now_iso()}
                skipped += 1
            resp.close()
        except Exception as exc:  # noqa: BLE001
            entries[guid] = {"file": None, "url": url, "status": f"ERR:{exc.__class__.__name__}",
                             "fetched_at": now_iso()}
            failed += 1
        if i % 10 == 0 or i == len(pending):
            print(f"  {i}/{len(pending)} saved={saved} skipped={skipped} failed={failed}")
            save_manifest(manifest)

    save_manifest(manifest)
    manifest["generated_at"] = now_iso()
    print(f"done: saved={saved} skipped={skipped} failed={failed} | manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
