#!/usr/bin/env python3
"""Preserve the full HLS media of the still-live works, before they are deleted.

Downloads, per work, the master playlist, one variant playlist, the AES-128
key, and every segment; concatenates the segments into a single `.ts`; and
records hashes in a committed manifest. Media bytes go to `staging/media/`
(gitignored) so the repo stays small while the bytes are still preserved
locally with committed hashes.

Stealth: reuses `PoliteSession`/`HostRateLimiter` (one host, paced).

Usage:
    python preserve_media.py --dry-run
    python preserve_media.py --variant low        # smallest variant (default)
    python preserve_media.py --variant high
    python preserve_media.py --verify
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

from sophie_scrape import HostRateLimiter, PoliteSession, PULL_ZONE

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_CSV = os.path.join(HERE, "sophie_little_live_videos.csv")
STAGING = os.path.join(HERE, "staging", "media")
MANIFEST = os.path.join(HERE, "captures", "media_manifest.json")
REFERER = "https://abdlhub.com/"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            return json.load(fh)
    return {"generated_at": now_iso(), "entries": {}}


def save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        json.dump(m, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, MANIFEST)


def parse_master(text):
    """Return [(bandwidth, resolution, relative_path)] from a master playlist."""
    variants = []
    lines = [l.strip() for l in text.splitlines()]
    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            bw = int(re.search(r"BANDWIDTH=(\d+)", line).group(1)) if "BANDWIDTH=" in line else 0
            res = re.search(r"RESOLUTION=(\d+x\d+)", line)
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if nxt and not nxt.startswith("#"):
                variants.append((bw, res.group(1) if res else "", nxt))
    return variants


def get(session, url):
    return session.get(url, referer=REFERER)


def preserve_one(session, guid):
    base = f"https://{PULL_ZONE}/{guid}"
    out = os.path.join(STAGING, guid)
    os.makedirs(out, exist_ok=True)

    r = get(session, f"{base}/playlist.m3u8")
    if r.status_code != 200 or "EXTM3U" not in r.text:
        return {"status": r.status_code, "note": "no master"}
    master_text = r.text
    with open(os.path.join(out, "master.m3u8"), "w", encoding="utf-8", newline="") as fh:
        fh.write(master_text)

    variants = parse_master(master_text)
    if not variants:
        return {"status": 200, "note": "no variants"}
    variants.sort(key=lambda v: v[0])
    bw, res, rel = variants[0] if variant_choice == "low" else variants[-1]

    vr = get(session, f"{base}/{rel}")
    variant_text = vr.text
    with open(os.path.join(out, "variant.m3u8"), "w", encoding="utf-8", newline="") as fh:
        fh.write(variant_text)

    vdir = rel.rsplit("/", 1)[0] if "/" in rel else ""
    key_uri = None
    m = re.search(r'#EXT-X-KEY:METHOD=AES-128,URI="([^"]+)"', variant_text)
    if m:
        key_uri = m.group(1)
    key_bytes = b""
    if key_uri:
        key_url = key_uri if key_uri.startswith("http") else f"https://{PULL_ZONE}{key_uri}"
        kr = get(session, key_url)
        key_bytes = kr.content
        with open(os.path.join(out, "key.bin"), "wb") as fh:
            fh.write(key_bytes)

    segments = [l.strip() for l in variant_text.splitlines()
                if l.strip() and not l.startswith("#") and l.strip().endswith((".dts", ".ts", ".m4s", ".mp4"))]
    ts_path = os.path.join(out, "video.ts")
    seg_hashes = []
    with open(ts_path, "wb") as fh:
        for seg in segments:
            seg_url = f"{base}/{vdir}/{seg}" if vdir else f"{base}/{seg}"
            sr = get(session, seg_url)
            if sr.status_code != 200:
                return {"status": f"seg {sr.status_code}", "note": seg}
            data = sr.content
            fh.write(data)
            seg_hashes.append(sha256_bytes(data))

    return {
        "status": 200,
        "variant": res,
        "bandwidth": bw,
        "segments": len(segments),
        "bytes": os.path.getsize(ts_path),
        "sha256": sha256_file(ts_path),
        "key_sha256": sha256_bytes(key_bytes),
        "master_sha256": sha256_bytes(master_text.encode()),
        "seg_hashes_sample": seg_hashes[:3],
        "dir": os.path.relpath(out, HERE).replace("\\", "/"),
        "fetched_at": now_iso(),
    }


def verify():
    if not os.path.exists(MANIFEST):
        print("no manifest")
        return 1
    m = load_manifest()
    bad = 0
    for guid, e in sorted(m["entries"].items()):
        if e.get("status") != 200:
            continue
        p = os.path.join(HERE, e["dir"], "video.ts")
        if not os.path.exists(p):
            print(f"MISSING {guid}")
            bad += 1
        elif sha256_file(p) != e["sha256"]:
            print(f"MISMATCH {guid}")
            bad += 1
    print(f"verified {len(m['entries'])}; problems {bad}")
    return 1 if bad else 0


def main():
    global variant_choice
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variant", choices=["low", "high"], default="low")
    ap.add_argument("--delay", type=float, default=0.25)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--recheck", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    variant_choice = args.variant

    if args.verify:
        sys.exit(verify())

    manifest = load_manifest()
    entries = manifest.setdefault("entries", {})
    rows = list(csv.DictReader(open(LIVE_CSV, encoding="utf-8-sig")))
    if args.limit:
        rows = rows[: args.limit]

    pending = [r for r in rows if args.recheck or entries.get(r["guid"], {}).get("status") != 200]
    print(f"live works: {len(rows)} | already preserved: {len(rows) - len(pending)} | will fetch: {len(pending)}")
    if args.dry_run:
        for r in pending:
            print("  ", r["guid"], r["title"][:50])
        return

    limiter = HostRateLimiter(args.delay, 1.0, 100, (5.0, 15.0))
    session = PoliteSession(limiter)
    for i, r in enumerate(pending, 1):
        guid = r["guid"]
        try:
            rec = preserve_one(session, guid)
        except Exception as exc:  # noqa: BLE001
            rec = {"status": f"ERR:{exc.__class__.__name__}", "fetched_at": now_iso()}
        rec["title"] = r["title"]
        entries[guid] = rec
        print(f"  [{i}/{len(pending)}] {rec.get('status')} {guid} "
              f"{rec.get('variant','')} {rec.get('segments','')}seg {rec.get('bytes','')}B")
        save_manifest(manifest)
    save_manifest(manifest)
    print(f"manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
