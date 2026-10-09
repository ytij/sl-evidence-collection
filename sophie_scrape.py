#!/usr/bin/env python3
"""ABDL-HUB copyright evidence collector.

Finds every video tagged with a given creator tag (default "Sophie Little") on
abdlhub.com and exports the identifying URLs needed for a takedown / court
filing:

  * page_url       - the public page that hosts the infringing copy
  * thumbnail_url  - the still image shown for the copy
  * stream_url     - the HLS master playlist that actually serves the video
  * variant_playlists - per-resolution playlists referenced by the master

The site is a single-page app backed by two public, unauthenticated services:

  * Bunny Stream  - the video library + pull-zone CDN (the real media)
  * Supabase      - PostgREST tables; tags live in video_meta.tags (text[])

Because both are plain HTTP APIs, no browser automation and no ad interaction
are required. The CDN requires a Referer of the site itself, which is set on
every request below.

Usage:
    python sophie_scrape.py
    python sophie_scrape.py --tag "Sophie Little" --out sophie_little_videos.csv
    python sophie_scrape.py --verify            # HEAD/GET-check every URL
    python sophie_scrape.py --verify --workers 16
"""

import argparse
import csv
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

SITE = "https://abdlhub.com"
SUPA = "https://hbvwlzjxsmhreeqwypwp.supabase.co"
SUPA_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhidndsemp4c21ocmVlcXd5cHdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI1ODA2OTksImV4cCI6MjA5ODE1NjY5OX0."
    "6ZM61TwLh1X5VuT0Q-X0y_Rs9RAzRrIQqg9J7DbB9rA"
)
PULL_ZONE = "vz-e81debcf-c73.b-cdn.net"
BUNNY_FN = f"{SITE}/.netlify/functions/bunny-videos"
REFERER = f"{SITE}/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

PAGE_SIZE = 1000
BUNNY_PAGE_SIZE = 500
REQUEST_TIMEOUT = 60

CSV_FIELDS = [
    "guid",
    "title",
    "matched_by",
    "page_url",
    "thumbnail_url",
    "stream_url",
    "variant_playlists",
    "duration_seconds",
    "duration_hms",
    "views",
    "upload_date",
    "category",
    "tags",
    "series_name",
    "episode",
    "width",
    "height",
    "available_resolutions",
    "in_catalog",
    "thumbnail_http_status",
    "stream_http_status",
    "thumbnail_content_type",
    "stream_content_type",
]


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Referer": REFERER})
    return s


def supa_headers():
    return {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}


def fetch_all_meta(session):
    """Return every row of video_meta (guid, tags, category, series, episode)."""
    rows = []
    offset = 0
    select = "guid,description,tags,category,series_name,episode"
    while True:
        url = (
            f"{SUPA}/rest/v1/video_meta?select={select}"
            f"&order=guid&limit={PAGE_SIZE}&offset={offset}"
        )
        r = session.get(url, headers=supa_headers(), timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def fetch_catalog(session):
    """Return {guid: bunny_item} for the entire Bunny Stream library."""
    catalog = {}
    page = 1
    while True:
        r = session.get(
            BUNNY_FN,
            params={"page": page, "perPage": BUNNY_PAGE_SIZE},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items") or []
        for it in items:
            if it.get("guid"):
                catalog[it["guid"]] = it
        if not items or len(items) < BUNNY_PAGE_SIZE:
            break
        page += 1
    return catalog


def text_matches(value, needle, mode):
    if not value:
        return False
    v = str(value).lower()
    n = needle.lower()
    return v == n if mode == "exact" else n in v


def tag_matches(tags, needle, mode):
    if not tags:
        return False
    return any(text_matches(t, needle, mode) for t in tags)


def title_matches(title, pattern):
    if not title or not pattern:
        return False
    return re.search(pattern, str(title), re.IGNORECASE) is not None


def hms(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_rows(meta_rows, catalog, tag, mode, title_pattern):
    """Union of tag matches (from video_meta) and title matches (from catalog)."""
    meta_by_guid = {m["guid"]: m for m in meta_rows}
    matched = {}
    for meta in meta_rows:
        if tag_matches(meta.get("tags"), tag, mode):
            matched[meta["guid"]] = {"tag": True, "title": False}
    if title_pattern:
        for guid, item in catalog.items():
            if title_matches(item.get("title"), title_pattern):
                matched.setdefault(guid, {"tag": False, "title": False})["title"] = True

    rows = []
    for guid, how in matched.items():
        meta = meta_by_guid.get(guid, {})
        item = catalog.get(guid, {})
        thumb_file = item.get("thumbnailFileName") or "thumbnail.jpg"
        resolutions = [
            res for res in str(item.get("availableResolutions") or "").split(",") if res
        ]
        variants = ";".join(
            f"https://{PULL_ZONE}/{guid}/{res}/video.m3u8" for res in resolutions
        )
        rows.append(
            {
                "guid": guid,
                "title": item.get("title", ""),
                "matched_by": "+".join(k for k in ("tag", "title") if how[k]),
                "page_url": f"{SITE}/?v={guid}",
                "thumbnail_url": f"https://{PULL_ZONE}/{guid}/{thumb_file}?width=480",
                "stream_url": f"https://{PULL_ZONE}/{guid}/playlist.m3u8",
                "variant_playlists": variants,
                "duration_seconds": item.get("length", ""),
                "duration_hms": hms(item.get("length")),
                "views": item.get("views", ""),
                "upload_date": item.get("dateUploaded", ""),
                "category": item.get("category") or meta.get("category") or "",
                "tags": "; ".join(meta.get("tags") or []),
                "series_name": meta.get("series_name") or "",
                "episode": meta.get("episode") or "",
                "width": item.get("width", ""),
                "height": item.get("height", ""),
                "available_resolutions": item.get("availableResolutions", ""),
                "in_catalog": bool(item),
                "thumbnail_http_status": "",
                "stream_http_status": "",
                "thumbnail_content_type": "",
                "stream_content_type": "",
            }
        )
    rows.sort(key=lambda r: (r["upload_date"] or "", r["title"] or ""), reverse=True)
    return rows


def probe(session, url):
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        ctype = r.headers.get("Content-Type", "")
        r.close()
        return r.status_code, ctype
    except requests.RequestException as exc:
        return f"ERR:{exc.__class__.__name__}", ""


def verify_rows(rows, workers):
    """Check that each thumbnail and stream URL is actually served."""
    jobs = []
    for row in rows:
        jobs.append((row, "thumbnail_url", "thumbnail_http_status", "thumbnail_content_type"))
        jobs.append((row, "stream_url", "stream_http_status", "stream_content_type"))

    session = make_session()

    def work(job):
        row, url_key, status_key, ctype_key = job
        status, ctype = probe(session, row[url_key])
        return row, status_key, ctype_key, status, ctype

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, j) for j in jobs]
        done = 0
        for fut in as_completed(futures):
            row, status_key, ctype_key, status, ctype = fut.result()
            row[status_key] = status
            row[ctype_key] = ctype
            done += 1
            if done % 50 == 0 or done == len(futures):
                sys.stderr.write(f"\r  verified {done}/{len(futures)} URLs")
                sys.stderr.flush()
    sys.stderr.write("\n")


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="Sophie Little", help='tag to match (default: "Sophie Little")')
    ap.add_argument("--match", choices=["exact", "substring"], default="exact",
                    help="how to match the tag (default: exact, case-insensitive)")
    ap.add_argument("--title", default="", help="also include catalog videos whose title matches this regex")
    ap.add_argument("--only-live", action="store_true",
                    help="after --verify, keep only rows whose stream returns 200")
    ap.add_argument("--live-out", default="", help="also write stream=200 rows to this CSV path")
    ap.add_argument("--out", default="sophie_little_videos.csv", help="output CSV path")
    ap.add_argument("--verify", action="store_true", help="probe each URL and record HTTP status")
    ap.add_argument("--workers", type=int, default=8, help="parallel workers for --verify")
    ap.add_argument("--limit", type=int, default=0, help="only process N matches (0 = all)")
    args = ap.parse_args()

    session = make_session()
    started = time.time()

    sys.stderr.write("Fetching video_meta from Supabase...\n")
    meta_rows = fetch_all_meta(session)
    sys.stderr.write(f"  {len(meta_rows)} metadata rows\n")

    sys.stderr.write("Fetching Bunny Stream catalog...\n")
    catalog = fetch_catalog(session)
    sys.stderr.write(f"  {len(catalog)} catalog items\n")

    rows = build_rows(meta_rows, catalog, args.tag, args.match, args.title)
    if args.limit:
        rows = rows[: args.limit]
    sys.stderr.write(f"Matched {len(rows)} videos (tag '{args.tag}'"
                     + (f", title /{args.title}/" if args.title else "") + ")\n")

    if args.verify:
        sys.stderr.write(f"Verifying URLs with {args.workers} workers...\n")
        verify_rows(rows, args.workers)

    if args.only_live:
        rows = [r for r in rows if str(r["stream_http_status"]) == "200"]
        sys.stderr.write(f"Kept {len(rows)} rows with a live stream\n")

    write_csv(rows, args.out)
    if args.live_out:
        if not args.verify:
            sys.stderr.write("--live-out requires --verify; skipping live-only file\n")
        else:
            live = [r for r in rows if str(r["stream_http_status"]) == "200"]
            write_csv(live, args.live_out)
            sys.stderr.write(f"Wrote {args.live_out} ({len(live)} live rows)\n")
    sys.stderr.write(f"Wrote {args.out} in {time.time() - started:.1f}s\n")


if __name__ == "__main__":
    main()
