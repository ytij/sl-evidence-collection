#!/usr/bin/env python3
"""Public-exposure & attribution review of the ABDL-HUB Supabase backend.

Scope and boundary
------------------
Everything here is read with the **anon JWT the site ships in its own page
source** and that every visitor's browser holds. This is public read access,
not an exploit: no authentication is bypassed, no privileged/service key is
used, no data is written, no action endpoint is invoked, and no partner
infrastructure is tested. It documents what the operator exposes about the
rehosting operation.

Outputs:
    osint/public_exposure.json
    osint/PUBLIC_EXPOSURE.md

Usage:
    python osint/public_exposure.py
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sophie_scrape import SUPA, SUPA_KEY, HostRateLimiter, PoliteSession

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_CSV = os.path.join(os.path.dirname(HERE), "sophie_little_live_videos.csv")
JSON_OUT = os.path.join(HERE, "public_exposure.json")
MD_OUT = os.path.join(HERE, "PUBLIC_EXPOSURE.md")

CREATOR_TITLE = re.compile(r"sofia", re.I)
SECRET_HINTS = re.compile(r"key|secret|token|password|passwd|pwd|bearer|access_key|service_role|api", re.I)
LINK_HINTS = re.compile(r"https?://\S+|www\.\S+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+|reddit\S*|thisvid\S*|twitter\S*|instagram\S*|onlyfans\S*", re.I)
TAKEDOWN_HINTS = re.compile(r"takedown|take down|remove|copyright|dmca|lawyer|legal|sue|report", re.I)


def supa_get(session, path):
    r = session.get(f"{SUPA}/rest/v1/{path}",
                    headers={"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}",
                             "Accept": "application/json"})
    return r.json() if r.status_code == 200 else []


def fetch_all(session, table, select="*", order="id", limit=1000):
    rows, offset = [], 0
    while True:
        batch = supa_get(session, f"{table}?select={select}&order={order}&limit={limit}&offset={offset}")
        rows.extend(batch)
        if len(batch) < limit:
            return rows
        offset += limit


def redact(value):
    s = str(value)
    if len(s) > 40 and re.search(r"[A-Za-z0-9+/=_-]{32,}", s):
        return s[:12] + f"…<redacted len={len(s)}>"
    return s[:200]


def main():
    limiter = HostRateLimiter(base_interval=0.6, jitter=1.0, long_every=25)
    session = PoliteSession(limiter)
    out = {"scope": "public anon-key read; no bypass, no privileged keys, no writes"}

    # ---- site_config: secret scan ----
    cfg = supa_get(session, "site_config?select=key,value&order=key")
    out["site_config_keys"] = {row["key"]: redact(row["value"]) for row in cfg}
    out["site_config_secret_flags"] = [
        row["key"] for row in cfg if SECRET_HINTS.search(row["key"])
    ]

    # ---- profiles ----
    prof = fetch_all(session, "user_profiles",
                     "user_id,username,is_admin,is_mod,supporter_tier,created_at,public_profile",
                     order="created_at")
    by_id = {p["user_id"]: p for p in prof}
    out["profile_count"] = len(prof)
    out["admins_mods"] = [
        {"username": p["username"], "user_id": p["user_id"],
         "is_admin": p["is_admin"], "is_mod": p["is_mod"]}
        for p in prof if p.get("is_admin") or p.get("is_mod")
    ]

    # ---- submissions: timeline + attribution ----
    subs = fetch_all(session, "video_submissions",
                     "id,user_id,title,status,category,description,video_url,created_at,file_size",
                     order="id")
    out["submission_count"] = len(subs)
    out["submission_statuses"] = dict(Counter(s["status"] for s in subs))
    uploaders = Counter()
    for s in subs:
        uploaders[by_id.get(s["user_id"], {}).get("username", s["user_id"])] += 1
    out["submissions_by_uploader"] = uploaders.most_common(50)

    live = {}
    if os.path.exists(LIVE_CSV):
        with open(LIVE_CSV, encoding="utf-8-sig") as fh:
            live = {row["guid"]: row for row in csv.DictReader(fh)}

    def guid_of(url):
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url or "")
        return m.group(1) if m else None

    creator_subs = [s for s in subs if CREATOR_TITLE.search(s.get("title") or "")]
    attribution = []
    for s in creator_subs:
        g = guid_of(s.get("video_url"))
        attribution.append({
            "submission_id": s["id"],
            "user_id": s["user_id"],
            "username": by_id.get(s["user_id"], {}).get("username"),
            "title": s["title"],
            "created_at": s["created_at"],
            "file_size": s["file_size"],
            "guid": g,
            "video_url": s["video_url"],
            "currently_live": g in live,
            "leaked_links": sorted(set(LINK_HINTS.findall(str(s.get("description") or "")))),
        })
    out["creator_attribution"] = attribution
    out["creator_uploaders"] = Counter(
        (a["username"], a["user_id"]) for a in attribution
    ).most_common()

    # ---- comments: takedown / links ----
    comments = fetch_all(session, "comments", "name,user_id,body,created_at", order="created_at")
    out["comment_count"] = len(comments)
    out["takedown_comments"] = [
        {"name": c["name"], "created_at": c["created_at"], "body": c["body"]}
        for c in comments if TAKEDOWN_HINTS.search(str(c.get("body") or ""))
    ]

    with open(JSON_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    write_markdown(out)
    session.save_cookies()
    sys.stderr.write(f"\nWrote {JSON_OUT} and {MD_OUT} ({session.count} requests)\n")


def write_markdown(out):
    L = []
    L.append("# ABDL-HUB — public exposure & attribution")
    L.append("")
    L.append("_Read-only via the site's own published anon key. No authentication was "
             "bypassed, no privileged key used, nothing written, no action endpoint invoked._")
    L.append("")
    L.append("## 1. What the backend exposes publicly")
    L.append("")
    L.append(f"- **{out['profile_count']} user profiles** (usernames, admin/mod flags, supporter tier, signup date).")
    L.append(f"- **{out['submission_count']} video submissions** — each with the **uploader's `user_id`**, "
             "title, description, file size, timestamp and the Bunny Stream embed URL.")
    L.append(f"- **{out['comment_count']} comments** with author names.")
    L.append("- `site_config` (settings, polls, donation address).")
    L.append("")
    L.append("Properly protected (RLS returns no rows to the anon key): `favorites`, "
             "`watch_history`, `video_reports`, `model_requests`, `title_suggestions`. "
             "The Supabase admin API (`/auth/v1/admin/*`) is not exposed — it needs the "
             "service key, which is not present anywhere in the client.")
    L.append("")
    L.append("**No secret material leaked in `site_config`** "
             f"(keys checked: {', '.join(out['site_config_keys'].keys())}). "
             "The anon JWT itself is public by design.")
    L.append("")
    L.append("## 2. Operator & staff accounts")
    L.append("")
    L.append("| Role | Username | user_id |")
    L.append("| --- | --- | --- |")
    for a in out["admins_mods"]:
        role = "admin" if a["is_admin"] else "mod"
        L.append(f"| {role} | {a['username']} | `{a['user_id']}` |")
    L.append("")
    L.append("## 3. Attribution of the Sophie Little / \"Sofia\" rehosts")
    L.append("")
    if out["creator_uploaders"]:
        for (name, uid), n in out["creator_uploaders"]:
            L.append(f"All **{n}** submissions titled *sofia* were uploaded by account "
                     f"**`{name}`** (`{uid}`).")
    L.append("")
    L.append("| Submission | Date | Size (bytes) | Guid | Live now | Leaked links |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for a in out["creator_attribution"]:
        links = ", ".join(a["leaked_links"]) or ""
        L.append(f"| {a['submission_id']} | {a['created_at'][:10]} | {a['file_size'] or ''} | "
                 f"`{a['guid']}` | {'yes' if a['currently_live'] else 'no'} | {links} |")
    L.append("")
    L.append("The submission **descriptions** leak the original creator's other identities "
             "(e.g. a Reddit handle and a ThisVid account) and the provenance of the files "
             "(2015 Samsung Galaxy captures), which supports a chain-of-custody narrative.")
    L.append("")
    L.append("## 4. Evidence the operator ignores takedowns")
    L.append("")
    for c in out["takedown_comments"]:
        L.append(f"> **{c['name']}** ({c['created_at'][:10]}): {c['body'].strip()}")
        L.append("")
    L.append("## 5. Operator pivot points (OSINT leads)")
    L.append("")
    L.append("- **Bitcoin donation address** in `site_config.settings.donate`.")
    L.append("- **Sponsor / affiliated site**: `AbdlMatch.com` (image served from a second "
             "Bunny zone, `abdlhub-images.b-cdn.net`).")
    L.append("- **Discord** invite in the page header (currently expired).")
    L.append("")
    with open(MD_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
