#!/usr/bin/env python3
"""Match original works-of-authorship (JFF export) against the rehosted copies.

Input — a manifest of the creator's originals, JSON or CSV, with any subset of:

    id              stable id (e.g. JFF post id)
    title           original title
    published_at    ISO date the original was published (gates the rehost date)
    duration_seconds
    thumbnail       local path or URL to a still
    media           local path to the original file (optional)
    sha256          optional hash of the original file
    source_url      where the original lives (e.g. the JFF post)

Example (originals.json):
    {"creator": "Sophie Little", "works": [
        {"id": "jff-1", "title": "ballet practice", "published_at": "2024-01-02",
         "duration_seconds": 657, "thumbnail": "originals/jff-1.jpg",
         "source_url": "https://justfor.fans/..."}]}

Matching signals: duration (±2 s), fuzzy title similarity, optional perceptual
hash of thumbnail stills, and the hard constraint that the rehost postdates the
original. Writes matches/matches.json + matches.csv.

Usage:
    python match.py --originals originals.json
    python match.py --originals originals.csv --thumbnails   # download rehost thumbs
"""

import argparse
import csv
import json
import os
import re
import sys
from difflib import SequenceMatcher

import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "evidence")
LIVE_CSV = os.path.join(HERE, "sophie_little_live_videos.csv")
OUT = os.path.join(HERE, "matches")
THUMB_CACHE = os.path.join(HERE, ".cache", "thumbs")

ATTRIBUTED_UPLOADER = "a89bb9dc-d09f-4475-b9ed-ae398edf928b"
TITLE_PATTERN = re.compile(r"sofia", re.I)
ACCEPT_THRESHOLD = 0.60


def guid_of(url):
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url or "")
    return m.group(1) if m else None


def load_originals(path):
    if path.endswith(".json"):
        data = json.load(open(path, encoding="utf-8"))
        rows = data.get("works", data) if isinstance(data, dict) else data
    else:
        rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    out = []
    for r in rows:
        out.append({
            "id": str(r.get("id") or ""),
            "title": r.get("title") or "",
            "published_at": (r.get("published_at") or "")[:10],
            "duration_seconds": _int(r.get("duration_seconds")),
            "thumbnail": r.get("thumbnail") or "",
            "media": r.get("media") or "",
            "sha256": r.get("sha256") or "",
            "source_url": r.get("source_url") or "",
        })
    return out


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def load_rehosted():
    subs = json.load(open(os.path.join(EVIDENCE, "video_submissions.json"), encoding="utf-8"))["rows"]
    live = {}
    if os.path.exists(LIVE_CSV):
        with open(LIVE_CSV, encoding="utf-8-sig") as fh:
            live = {r["guid"]: r for r in csv.DictReader(fh)}
    works = []
    for s in subs:
        if s.get("user_id") != ATTRIBUTED_UPLOADER and not TITLE_PATTERN.search(s.get("title") or ""):
            continue
        g = guid_of(s.get("video_url"))
        row = live.get(g, {})
        works.append({
            "guid": g,
            "title": s["title"],
            "submitted_at": (s.get("created_at") or "")[:10],
            "duration_seconds": _int(row.get("duration_seconds")),
            "thumbnail_url": row.get("thumbnail_url", ""),
            "page_url": row.get("page_url", f"https://abdlhub.com/?v={g}"),
        })
    return works


def phash(image, hash_size=8):
    if cv2 is None:
        return None
    size = hash_size * 4
    img = image.convert("L").resize((size, size), Image.LANCZOS)
    pixels = np.asarray(img, dtype=np.float32)
    dct = cv2.dct(pixels)
    low = dct[:hash_size, :hash_size]
    med = np.median(low[1:, :])
    return (low > med).flatten()


def thumb_hash(src):
    if cv2 is None or not src:
        return None
    try:
        if str(src).lower().startswith("http"):
            import requests
            os.makedirs(THUMB_CACHE, exist_ok=True)
            dest = os.path.join(THUMB_CACHE, re.sub(r"\W+", "_", str(src))[-180:] + ".jpg")
            if not os.path.exists(dest):
                r = requests.get(src, timeout=30, headers={"Referer": "https://abdlhub.com/"})
                if r.status_code != 200:
                    return None
                open(dest, "wb").write(r.content)
            src = dest
        return phash(Image.open(src))
    except Exception:
        return None


def similarity(a, b):
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def score(orig, rehost, orig_hash):
    duration_score = 1.0 if (orig["duration_seconds"] and rehost["duration_seconds"]
                             and abs(orig["duration_seconds"] - rehost["duration_seconds"]) <= 2) else 0.0
    title_score = similarity(orig["title"], rehost["title"])
    thumb_score = 0.0
    if orig_hash is not None:
        rh = thumb_hash(rehost.get("thumbnail_url"))
        if rh is not None:
            dist = int(np.count_nonzero(orig_hash != rh))
            thumb_score = max(0.0, 1.0 - dist / 64.0)

    if orig_hash is not None:
        total = 0.30 * duration_score + 0.35 * title_score + 0.35 * thumb_score
    else:
        total = 0.45 * duration_score + 0.55 * title_score
    dated_ok = bool(orig["published_at"] and rehost["submitted_at"]
                    and rehost["submitted_at"] >= orig["published_at"])
    return {
        "total": round(total, 3),
        "duration_score": duration_score,
        "title_score": round(title_score, 3),
        "thumb_score": round(thumb_score, 3),
        "rehost_postdates_original": dated_ok,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--originals", required=True)
    ap.add_argument("--thumbnails", action="store_true", help="download rehost thumbs for perceptual matching")
    args = ap.parse_args()

    originals = load_originals(args.originals)
    rehosted = load_rehosted()
    os.makedirs(OUT, exist_ok=True)

    results = []
    for orig in originals:
        oh = thumb_hash(orig["thumbnail"]) if (args.thumbnails and orig["thumbnail"]) else None
        scored = []
        for rh in rehosted:
            s = score(orig, rh, oh)
            s["guid"] = rh["guid"]
            s["title"] = rh["title"]
            s["page_url"] = rh["page_url"]
            scored.append(s)
        scored.sort(key=lambda x: x["total"], reverse=True)
        best = scored[0] if scored else None
        results.append({
            "original": orig,
            "best_match": best,
            "accepted": bool(best and best["total"] >= ACCEPT_THRESHOLD
                             and best["rehost_postdates_original"]),
            "candidates": scored[:5],
        })
        flag = "MATCH" if results[-1]["accepted"] else "unmatched"
        print(f"  {flag:9s} {orig['id']} {orig['title'][:40]!r} -> "
              f"{best['title'][:40] if best else '-'} ({best['total'] if best else 0})")

    with open(os.path.join(OUT, "matches.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump({"originals": len(originals), "results": results}, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT, "matches.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["original_id", "original_title", "original_published", "matched",
                    "rehost_guid", "rehost_title", "postdates_original", "score", "page_url"])
        for r in results:
            b = r["best_match"] or {}
            w.writerow([r["original"]["id"], r["original"]["title"], r["original"]["published_at"],
                        r["accepted"], b.get("guid", ""), b.get("title", ""),
                        b.get("rehost_postdates_original", ""), b.get("total", ""), b.get("page_url", "")])

    matched = sum(1 for r in results if r["accepted"])
    print(f"{matched}/{len(originals)} matched; wrote {OUT}/matches.json + matches.csv")


if __name__ == "__main__":
    main()
