#!/usr/bin/env python3
"""ABDL-HUB copyright evidence collector (low-profile edition).

Finds videos belonging to a creator (default: the model "Sophie Little") on
abdlhub.com and exports the identifying URLs needed for a takedown / court
filing:

  * page_url          - the public page that hosts the infringing copy
  * thumbnail_url     - the still image shown for the copy
  * stream_url        - the HLS master playlist that actually serves the video
  * variant_playlists - per-resolution playlists referenced by the master

Why there is no browser automation
----------------------------------
The site is a single-page app over public, unauthenticated services (Bunny
Stream for media, Supabase/PostgREST for metadata). The age-gate, infinite
scroll and pre-roll ad are all client-side UI; the media URL never depends on
them. Talking to the same JSON APIs the page uses yields identical results
without loading an ad impression or driving a browser.

Low-profile design ("invisible" to the host)
--------------------------------------------
* Per-host rate limiter: minimum spacing per hostname plus jitter and an
  occasional longer "reading" pause, so traffic never looks like a tight loop.
* Browser-realistic headers on every request (UA, Accept-Language, sec-ch-ua,
  Sec-Fetch-*, Referer) instead of a bare python-requests fingerprint.
* Persistent cookie jar: one warm-up page load establishes a normal session
  that is reused across runs (``.cache/cookies.json``).
* TTL caches for catalog/metadata and per-URL probes, so re-runs usually make
  zero requests. ``--refresh`` / ``--recheck`` force a fresh sweep.
* Incremental catalog refresh: page 1 is compared against the cache and the
  remaining pages are skipped when nothing changed.
* Exponential backoff on 429/5xx; ``--max-requests`` hard budget per run.

Usage:
    python sophie_scrape.py --verify
    python sophie_scrape.py --refresh --recheck --verify   # forced sweep
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
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from evidence_store import EvidenceStore

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
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

PAGE_SIZE = 1000
BUNNY_PAGE_SIZE = 500
REQUEST_TIMEOUT = 60

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, ".cache")
EVIDENCE_DIR = os.path.join(HERE, "evidence")
COOKIE_PATH = os.path.join(CACHE_DIR, "cookies.json")

DEFAULT_TAG = "Sophie Little"
DEFAULT_TITLE = r"sofia"
DEFAULT_EXCLUDE = r"kiki\s*cali|sophie\s*ladder|sophiaquin"

# Baseline browser headers. Per-request overrides tweak Accept / Sec-Fetch-*.
BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="125", "Not.A/Brand";v="24", "Google Chrome";v="125"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

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


class HostRateLimiter:
    """Spaces request starts per hostname, with jitter and periodic long pauses."""

    def __init__(self, base_interval, jitter=1.0, long_every=50, long_range=(4.0, 12.0)):
        self.base = max(0.0, base_interval)
        self.jitter = max(0.0, jitter)
        self.long_every = long_every
        self.long_range = long_range
        self._lock = threading.Lock()
        self._next = {}
        self._count = 0

    def wait(self, host):
        if self.base <= 0:
            return
        with self._lock:
            self._count += 1
            count = self._count
            now = time.monotonic()
            nxt = self._next.get(host, 0.0)
            sleep_for = max(0.0, nxt - now)
            self._next[host] = max(now, nxt) + self.base * (1.0 + random.uniform(0, self.jitter))
        if sleep_for:
            time.sleep(sleep_for)
        if self.long_every and count % self.long_every == 0:
            time.sleep(random.uniform(*self.long_range))


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


class PoliteSession:
    """A requests.Session that looks and behaves like a well-paced browser."""

    def __init__(self, limiter, max_requests=0):
        self.limiter = limiter
        self.max_requests = max_requests
        self.count = 0
        self._count_lock = threading.Lock()
        self.session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self._load_cookies()

    def _load_cookies(self):
        if os.path.exists(COOKIE_PATH):
            try:
                with open(COOKIE_PATH, encoding="utf-8") as fh:
                    self.session.cookies.update(json.load(fh))
            except (OSError, ValueError):
                pass

    def save_cookies(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        try:
            with open(COOKIE_PATH, "w", encoding="utf-8") as fh:
                json.dump(requests.utils.dict_from_cookiejar(self.session.cookies), fh)
        except OSError:
            pass

    def _budget_ok(self):
        with self._count_lock:
            if self.max_requests and self.count >= self.max_requests:
                return False
            self.count += 1
            return True

    def get(self, url, headers=None, referer=None, **kw):
        if not self._budget_ok():
            raise RuntimeError(f"request budget of {self.max_requests} exhausted")
        host = urlparse(url).netloc
        self.limiter.wait(host)
        h = dict(BROWSER_HEADERS)
        h["Referer"] = referer if referer is not None else REFERER
        if headers:
            h.update(headers)
        kw.setdefault("timeout", REQUEST_TIMEOUT)
        return self.session.get(url, headers=h, **kw)

    def post(self, url, headers=None, referer=None, **kw):
        if not self._budget_ok():
            raise RuntimeError(f"request budget of {self.max_requests} exhausted")
        host = urlparse(url).netloc
        self.limiter.wait(host)
        h = dict(BROWSER_HEADERS)
        h["Referer"] = referer if referer is not None else REFERER
        if headers:
            h.update(headers)
        kw.setdefault("timeout", REQUEST_TIMEOUT)
        return self.session.post(url, headers=h, **kw)

    def warm_up(self, last_warm_iso=None, ttl=0):
        """One normal-looking page load to obtain cookies, at most once per TTL."""
        if self.session.cookies:
            return False
        if last_warm_iso and age_seconds(last_warm_iso) < ttl:
            return False
        try:
            self.get(SITE + "/")
        except requests.RequestException:
            pass
        return True


def supa_headers():
    return {
        "apikey": SUPA_KEY,
        "Authorization": f"Bearer {SUPA_KEY}",
        "Accept": "application/json",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }


def fetch_all_meta(session, cache, ttl, refresh, store=None):
    """Every row of video_meta (guid, tags, category, series, episode)."""
    entry = cache.get("video_meta")
    if entry and not refresh and age_seconds(entry.get("fetched_at")) < ttl:
        sys.stderr.write("  video_meta: cached\n")
        return entry["rows"]

    rows = []
    offset = 0
    last_url = ""
    select = "guid,description,tags,category,series_name,episode"
    while True:
        url = (
            f"{SUPA}/rest/v1/video_meta?select={select}"
            f"&order=guid&limit={PAGE_SIZE}&offset={offset}"
        )
        last_url = url
        r = session.get(url, headers=supa_headers(), referer=SITE + "/")
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    cache.set("video_meta", {"fetched_at": now_iso(), "rows": rows})
    if store is not None:
        store.save("video_meta", rows, url=last_url, note="Supabase video_meta full table")
    sys.stderr.write(f"  video_meta: fetched {len(rows)} rows\n")
    return rows


def fetch_catalog(session, cache, ttl, refresh, incremental=True, store=None):
    """{guid: bunny_item} for the entire Bunny Stream library."""
    entry = cache.get("catalog")
    fresh = entry and not refresh and age_seconds(entry.get("fetched_at")) < ttl
    if fresh:
        sys.stderr.write("  catalog: cached\n")
        return entry["items"]

    api_headers = {"Accept": "application/json", "Sec-Fetch-Dest": "empty",
                   "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin"}

    # Incremental: page 1 alone tells us whether the catalog changed.
    if entry and incremental and not refresh:
        r = session.get(BUNNY_FN, params={"page": 1, "perPage": BUNNY_PAGE_SIZE}, headers=api_headers)
        r.raise_for_status()
        d = r.json()
        items = d.get("items") or []
        cached = entry["items"]
        if d.get("totalItems") == entry.get("total_items") and items and cached:
            first_new = items[0].get("guid")
            first_old = next(iter(cached.values()), {}).get("guid")
            if first_new == first_old:
                cache.set("catalog", {**entry, "fetched_at": now_iso()})
                sys.stderr.write("  catalog: unchanged (page-1 check)\n")
                return cached

    items = {}
    page = 1
    total = None
    while True:
        r = session.get(BUNNY_FN, params={"page": page, "perPage": BUNNY_PAGE_SIZE}, headers=api_headers)
        r.raise_for_status()
        d = r.json()
        total = d.get("totalItems", total)
        batch = d.get("items") or []
        for it in batch:
            if it.get("guid"):
                items[it["guid"]] = it
        if not batch or len(batch) < BUNNY_PAGE_SIZE:
            break
        page += 1
    cache.set("catalog", {"fetched_at": now_iso(), "items": items, "total_items": total})
    if store is not None:
        store.save("bunny_catalog", list(items.values()), url=BUNNY_FN,
                   note="Bunny Stream library 621930 catalog")
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
        if exclude_pattern and not how["tag"]:
            if re_matches(title, exclude_pattern) or re_matches(" ".join(map(str, tags)), exclude_pattern):
                continue
        resolutions = [r for r in str(item.get("availableResolutions") or "").split(",") if r]
        rows.append(
            {
                "guid": guid,
                "title": title,
                "matched_by": "+".join(k for k in ("tag", "title") if how[k]),
                "page_url": f"{SITE}/?v={guid}",
                "thumbnail_url": f"https://{PULL_ZONE}/{guid}/{item.get('thumbnailFileName') or 'thumbnail.jpg'}?width=480",
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


def probe(session, url, accept):
    try:
        r = session.get(url, headers={"Accept": accept, "Sec-Fetch-Dest": "empty",
                                      "Sec-Fetch-Mode": "no-cors", "Sec-Fetch-Site": "cross-site"})
        status = r.status_code
        ctype = r.headers.get("Content-Type", "")
        r.close()
        return status, ctype
    except requests.RequestException as exc:
        return f"ERR:{exc.__class__.__name__}", ""


def seed_probes_from_csv(cache, path):
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
                    cache.set(url, {"status": row[status_key],
                                    "content_type": row.get(ctype_key, ""),
                                    "checked_at": now_iso()})
                    n += 1
    return n


def verify_rows(rows, session, probe_cache, workers, probe_ttl, refresh):
    jobs = []
    for row in rows:
        for url_key, status_key, ctype_key, accept in (
            ("thumbnail_url", "thumbnail_http_status", "thumbnail_content_type", "image/avif,image/webp,image/*,*/*;q=0.8"),
            ("stream_url", "stream_http_status", "stream_content_type", "application/vnd.apple.mpegurl,*/*;q=0.8"),
        ):
            url = row[url_key]
            cached = probe_cache.get(url)
            if cached and not refresh and age_seconds(cached.get("checked_at")) < probe_ttl:
                row[status_key] = cached.get("status", "")
                row[ctype_key] = cached.get("content_type", "")
            else:
                jobs.append((row, status_key, ctype_key, url, accept))

    if not jobs:
        sys.stderr.write("  all URLs satisfied from cache\n")
        return

    random.shuffle(jobs)

    def work(job):
        row, status_key, ctype_key, url, accept = job
        status, ctype = probe(session, url, accept)
        return job, status, ctype

    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(work, j) for j in jobs]
            done = 0
            for fut in as_completed(futures):
                (row, status_key, ctype_key, url, accept), status, ctype = fut.result()
                row[status_key] = status
                row[ctype_key] = ctype
                probe_cache.set(url, {"status": status, "content_type": ctype, "checked_at": now_iso()})
                done += 1
                if done % 25 == 0 or done == len(futures):
                    sys.stderr.write(f"\r  probed {done}/{len(futures)} URLs")
                    sys.stderr.flush()
        sys.stderr.write("\n")
    finally:
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
                    help="drop title matches matching this regex")
    ap.add_argument("--out", default="sophie_little_all_videos.csv", help="output CSV path")
    ap.add_argument("--live-out", default="sophie_little_live_videos.csv",
                    help="also write stream=200 rows to this CSV (requires --verify)")
    ap.add_argument("--verify", action="store_true", help="probe each URL and record HTTP status")
    ap.add_argument("--workers", type=int, default=3, help="parallel probe workers (default: 3)")
    ap.add_argument("--delay", type=float, default=0.6,
                    help="base seconds between requests to the same host (default: 0.6)")
    ap.add_argument("--jitter", type=float, default=1.0,
                    help="random extra fraction added to each delay (default: 1.0 = up to +100%%)")
    ap.add_argument("--long-pause-every", type=int, default=50,
                    help="insert a longer pause every N requests (0 disables; default: 50)")
    ap.add_argument("--max-requests", type=int, default=0, help="hard request budget per run (0 = unlimited)")
    ap.add_argument("--cache-ttl", type=float, default=12.0, help="hours to reuse source cache (default: 12)")
    ap.add_argument("--probe-ttl", type=float, default=24.0, help="hours to reuse a URL probe (default: 24)")
    ap.add_argument("--refresh", action="store_true", help="ignore catalog/metadata cache")
    ap.add_argument("--recheck", action="store_true", help="ignore cached URL probes")
    ap.add_argument("--seed-probes", default="", help="seed probe cache from an existing CSV")
    ap.add_argument("--limit", type=int, default=0, help="only process N matches (0 = all)")
    args = ap.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    limiter = HostRateLimiter(args.delay, args.jitter, args.long_pause_every)
    session = PoliteSession(limiter, args.max_requests)
    meta_cache = JsonCache(os.path.join(CACHE_DIR, "sources.json"))
    probe_cache = JsonCache(os.path.join(CACHE_DIR, "probes.json"))
    evidence = EvidenceStore(EVIDENCE_DIR)
    started = time.time()

    warm = meta_cache.get("warmup")
    if session.warm_up(warm and warm.get("at"), args.cache_ttl * 3600):
        meta_cache.set("warmup", {"at": now_iso()})

    if args.seed_probes:
        seeded = seed_probes_from_csv(probe_cache, args.seed_probes)
        sys.stderr.write(f"Seeded {seeded} probe results from {args.seed_probes}\n")
        probe_cache.save()

    sys.stderr.write("Fetching tag metadata (Supabase)...\n")
    meta_rows = fetch_all_meta(session, meta_cache, args.cache_ttl * 3600, args.refresh, evidence)

    sys.stderr.write("Fetching video catalog (Bunny Stream)...\n")
    catalog = fetch_catalog(session, meta_cache, args.cache_ttl * 3600, args.refresh, store=evidence)
    meta_cache.save()

    rows = build_rows(meta_rows, catalog, args.tag, args.match, args.title, args.exclude)
    if args.limit:
        rows = rows[: args.limit]
    sys.stderr.write(f"Matched {len(rows)} videos (tag '{args.tag}'"
                     + (f", title /{args.title}/" if args.title else "")
                     + (f", exclude /{args.exclude}/" if args.exclude else "") + ")\n")

    if args.verify:
        sys.stderr.write(f"Verifying URLs (workers={args.workers}, delay={args.delay}s)...\n")
        verify_rows(rows, session, probe_cache, args.workers, args.probe_ttl * 3600, args.recheck)

    write_csv(rows, args.out)
    if args.live_out:
        if not args.verify:
            sys.stderr.write("--live-out requires --verify; skipping live-only file\n")
        else:
            live = [r for r in rows if str(r["stream_http_status"]) == "200"]
            write_csv(live, args.live_out)
            sys.stderr.write(f"Wrote {args.live_out} ({len(live)} live rows)\n")

    session.save_cookies()
    sys.stderr.write(f"Wrote {args.out} in {time.time() - started:.1f}s "
                     f"({session.count} requests this run)\n")


if __name__ == "__main__":
    main()
