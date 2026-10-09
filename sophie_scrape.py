#!/usr/bin/env python3
"""ABDL-HUB copyright evidence collector.

Finds videos belonging to a creator (default: the model "Sophie Little") on
abdlhub.com and exports the identifying URLs needed for a takedown / court
filing:

  * page_url          - the public page that hosts the infringing copy
  * thumbnail_url     - the still image shown for the copy
  * stream_url        - the HLS master playlist that actually serves the video
  * variant_playlists - per-resolution playlists referenced by the master

Why there is no browser automation
----------------------------------
The site is a single-page app over two public, unauthenticated services:

  * Bunny Stream  - the video library + pull-zone CDN (the real media)
  * Supabase      - PostgREST tables; creator tags live in video_meta.tags

The page's age-gate, infinite-scroll pagination and the pre-roll ad before a
video are all client-side UI concerns. The underlying media URL never depends
on any of them, so talking to the same JSON APIs the page itself uses yields
identical results while:

  * never loading an ad impression (no ExoClick/ExoAds calls),
  * never driving a headless browser (much lighter + less fingerprintable),
  * issuing a handful of API calls instead of hundreds of page loads.

The only access control on the media is a ``Referer: https://abdlhub.com/``
header, which is set on every request below.

Staying under the radar
-----------------------
* Every request is globally rate-limited (``--delay``) and retried with
  exponential backoff on 429/5xx.
* Catalog + tag metadata are cached in ``.cache/`` (``--cache-ttl`` hours).
* URL probes are cached per-URL (``--probe-ttl`` hours), so repeated runs and
  incremental refreshes only touch what actually changed.
* ``--refresh`` / ``--recheck`` force a full re-fetch when you want one.

Usage:
    python sophie_scrape.py --verify
    python sophie_scrape.py --verify --out sophie_little_all_videos.csv \
        --live-out sophie_little_live_videos.csv
    python sophie_scrape.py --refresh --recheck --verify   # force fresh run
"""

import argparse
import csv
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")

# The creator's own uploads are titled "Sofia"/"princess Sofia"/"Abdl Sofia".
# A bare /sofia/ deliberately does NOT match "Sophie Ladder" or "SophiaQuin";
# the exclude list is belt-and-braces against renames.
DEFAULT_TAG = "Sophie Little"
DEFAULT_TITLE = r"sofia"
DEFAULT_EXCLUDE = r"kiki\s*cali|sophie\s*ladder|sophiaquin"

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


class RateLimiter:
    """Spaces out request starts so the whole process averages <= 1/delay req/s."""

    def __init__(self, min_interval):
        self.min_interval = max(0.0, min_interval)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
            jitter = random.uniform(0, self.min_interval * 0.25)
            self._next = max(now, self._next) + self.min_interval + jitter


class JsonCache:
    def __init__(self, path):
        self.path = path
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    self.data = json.load(fh)
            except (OSError, ValueError):
                self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh)
        os.replace(tmp, self.path)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def age_seconds(iso_ts):
    if not iso_ts:
        return float("inf")
    try:
        dt = datetime.fromisoformat(iso_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds()
    except ValueError:
        return float("inf")


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Referer": REFERER})
    retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    return s


def supa_headers():
    return {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"}


def fetch_all_meta(session, limiter, cache, ttl, refresh):
    """Every row of video_meta (guid, tags, category, series, episode)."""
    entry = cache.get("video_meta")
    if entry and not refresh and age_seconds(entry.get("fetched_at")) < ttl:
        sys.stderr.write("  video_meta: cached\n")
        return entry["rows"]

    rows = []
    offset = 0
    select = "guid,description,tags,category,series_name,episode"
    while True:
        limiter.wait()
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
    cache.set("video_meta", {"fetched_at": now_iso(), "rows": rows})
    sys.stderr.write(f"  video_meta: fetched {len(rows)} rows\n")
    return rows


def fetch_catalog(session, limiter, cache, ttl, refresh):
    """{guid: bunny_item} for the entire Bunny Stream library."""
    entry = cache.get("catalog")
    if entry and not refresh and age_seconds(entry.get("fetched_at")) < ttl:
        sys.stderr.write("  catalog: cached\n")
        return entry["items"]

    items = {}
    page = 1
    while True:
        limiter.wait()
        r = session.get(
            BUNNY_FN,
            params={"page": page, "perPage": BUNNY_PAGE_SIZE},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        batch = (r.json().get("items") or [])
        for it in batch:
            if it.get("guid"):
                items[it["guid"]] = it
        if not batch or len(batch) < BUNNY_PAGE_SIZE:
            break
        page += 1
    cache.set("catalog", {"fetched_at": now_iso(), "items": items})
    sys.stderr.write(f"  catalog: fetched {len(items)} items\n")
    return items


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


def re_matches(text, pattern):
    if not text or not pattern:
        return False
    return re.search(pattern, str(text), re.IGNORECASE) is not None


def hms(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def build_rows(meta_rows, catalog, tag, mode, title_pattern, exclude_pattern):
    """Union of tag matches (video_meta) and title matches (catalog), minus exclusions."""
    meta_by_guid = {m["guid"]: m for m in meta_rows}
    matched = {}
    for meta in meta_rows:
        if tag_matches(meta.get("tags"), tag, mode):
            matched[meta["guid"]] = {"tag": True, "title": False}
    if title_pattern:
        for guid, item in catalog.items():
            if re_matches(item.get("title"), title_pattern):
                matched.setdefault(guid, {"tag": False, "title": False})["title"] = True

    rows = []
    for guid, how in matched.items():
        meta = meta_by_guid.get(guid, {})
        item = catalog.get(guid, {})
        title = item.get("title", "")
        tags = meta.get("tags") or []
        # Drop known false positives (different creators) unless the exact tag
        # says otherwise.
        if exclude_pattern and not how["tag"]:
            if re_matches(title, exclude_pattern) or re_matches(" ".join(map(str, tags)), exclude_pattern):
                continue
        thumb_file = item.get("thumbnailFileName") or "thumbnail.jpg"
        resolutions = [
            res for res in str(item.get("availableResolutions") or "").split(",") if res
        ]
        rows.append(
            {
                "guid": guid,
                "title": title,
                "matched_by": "+".join(k for k in ("tag", "title") if how[k]),
                "page_url": f"{SITE}/?v={guid}",
                "thumbnail_url": f"https://{PULL_ZONE}/{guid}/{thumb_file}?width=480",
                "stream_url": f"https://{PULL_ZONE}/{guid}/playlist.m3u8",
                "variant_playlists": ";".join(
                    f"https://{PULL_ZONE}/{guid}/{res}/video.m3u8" for res in resolutions
                ),
                "duration_seconds": item.get("length", ""),
                "duration_hms": hms(item.get("length")),
                "views": item.get("views", ""),
                "upload_date": item.get("dateUploaded", ""),
                "category": item.get("category") or meta.get("category") or "",
                "tags": "; ".join(tags),
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


def probe(session, limiter, url):
    limiter.wait()
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        status = r.status_code
        ctype = r.headers.get("Content-Type", "")
        r.close()
        return status, ctype
    except requests.RequestException as exc:
        return f"ERR:{exc.__class__.__name__}", ""


def seed_probes_from_csv(cache, path):
    """Populate the probe cache from a previously written CSV (avoids re-hitting)."""
    if not os.path.exists(path):
        return 0
    n = 0
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            for url_key, status_key, ctype_key in (
                ("thumbnail_url", "thumbnail_http_status", "thumbnail_content_type"),
                ("stream_url", "stream_http_status", "stream_content_type"),
            ):
                url = row.get(url_key)
                if url and row.get(status_key):
                    cache.set(url, {
                        "status": row[status_key],
                        "content_type": row.get(ctype_key, ""),
                        "checked_at": now_iso(),
                    })
                    n += 1
    return n


def verify_rows(rows, session, limiter, probe_cache, workers, probe_ttl, refresh):
    """Probe each thumbnail/stream URL, reusing cached results when fresh."""
    jobs = []
    for row in rows:
        for url_key, status_key, ctype_key in (
            ("thumbnail_url", "thumbnail_http_status", "thumbnail_content_type"),
            ("stream_url", "stream_http_status", "stream_content_type"),
        ):
            url = row[url_key]
            cached = probe_cache.get(url)
            if cached and not refresh and age_seconds(cached.get("checked_at")) < probe_ttl:
                row[status_key] = cached.get("status", "")
                row[ctype_key] = cached.get("content_type", "")
            else:
                jobs.append((row, url_key, status_key, ctype_key, url))

    if not jobs:
        sys.stderr.write("  all URLs satisfied from cache\n")
        return

    def work(job):
        row, url_key, status_key, ctype_key, url = job
        status, ctype = probe(session, limiter, url)
        return job, status, ctype

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, j) for j in jobs]
        done = 0
        for fut in as_completed(futures):
            (row, url_key, status_key, ctype_key, url), status, ctype = fut.result()
            row[status_key] = status
            row[ctype_key] = ctype
            probe_cache.set(url, {"status": status, "content_type": ctype, "checked_at": now_iso()})
            done += 1
            if done % 25 == 0 or done == len(futures):
                sys.stderr.write(f"\r  probed {done}/{len(futures)} URLs")
                sys.stderr.flush()
    sys.stderr.write("\n")
    probe_cache.save()


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default=DEFAULT_TAG, help=f'tag to match (default: "{DEFAULT_TAG}")')
    ap.add_argument("--match", choices=["exact", "substring"], default="exact",
                    help="how to match the tag (default: exact, case-insensitive)")
    ap.add_argument("--title", default=DEFAULT_TITLE,
                    help=f"also include catalog videos whose title matches this regex (default: /{DEFAULT_TITLE}/)")
    ap.add_argument("--exclude", default=DEFAULT_EXCLUDE,
                    help="drop title matches matching this regex (default excludes other creators)")
    ap.add_argument("--out", default="sophie_little_all_videos.csv", help="output CSV path")
    ap.add_argument("--live-out", default="sophie_little_live_videos.csv",
                    help="also write stream=200 rows to this CSV (requires --verify)")
    ap.add_argument("--verify", action="store_true", help="probe each URL and record HTTP status")
    ap.add_argument("--workers", type=int, default=4, help="parallel probe workers (default: 4)")
    ap.add_argument("--delay", type=float, default=0.35,
                    help="minimum seconds between any two requests (default: 0.35)")
    ap.add_argument("--cache-ttl", type=float, default=12.0,
                    help="hours to reuse catalog/metadata cache (default: 12)")
    ap.add_argument("--probe-ttl", type=float, default=24.0,
                    help="hours to reuse a cached URL probe (default: 24)")
    ap.add_argument("--refresh", action="store_true", help="ignore catalog/metadata cache")
    ap.add_argument("--recheck", action="store_true", help="ignore cached URL probes")
    ap.add_argument("--seed-probes", default="", help="seed probe cache from an existing CSV")
    ap.add_argument("--limit", type=int, default=0, help="only process N matches (0 = all)")
    args = ap.parse_args()

    session = make_session()
    limiter = RateLimiter(args.delay)
    os.makedirs(CACHE_DIR, exist_ok=True)
    meta_cache = JsonCache(os.path.join(CACHE_DIR, "sources.json"))
    probe_cache = JsonCache(os.path.join(CACHE_DIR, "probes.json"))
    started = time.time()

    if args.seed_probes:
        seeded = seed_probes_from_csv(probe_cache, args.seed_probes)
        sys.stderr.write(f"Seeded {seeded} probe results from {args.seed_probes}\n")
        probe_cache.save()

    sys.stderr.write("Fetching tag metadata (Supabase)...\n")
    meta_rows = fetch_all_meta(session, limiter, meta_cache, args.cache_ttl * 3600, args.refresh)

    sys.stderr.write("Fetching video catalog (Bunny Stream)...\n")
    catalog = fetch_catalog(session, limiter, meta_cache, args.cache_ttl * 3600, args.refresh)
    meta_cache.save()

    rows = build_rows(meta_rows, catalog, args.tag, args.match, args.title, args.exclude)
    if args.limit:
        rows = rows[: args.limit]
    sys.stderr.write(f"Matched {len(rows)} videos (tag '{args.tag}'"
                     + (f", title /{args.title}/" if args.title else "")
                     + (f", exclude /{args.exclude}/" if args.exclude else "") + ")\n")

    if args.verify:
        sys.stderr.write(f"Verifying URLs (workers={args.workers}, delay={args.delay}s)...\n")
        verify_rows(rows, session, limiter, probe_cache, args.workers,
                    args.probe_ttl * 3600, args.recheck)

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
