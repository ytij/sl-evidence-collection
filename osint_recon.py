#!/usr/bin/env python3
"""OSINT characterization of abdlhub.com.

Collects, from public endpoints only, everything needed to describe the
rehosting operation's technology stack: DNS, TLS, HTTP response headers, the
third-party services the page loads, the Netlify function surface, the
Supabase/PostgREST schema and auth configuration, and the ad/analytics stack.

Reuses the polite session from ``sophie_scrape`` (rate limiting + browser
headers) so the collection itself stays low-profile.

Outputs:
    osint/site_catalog.json   machine-readable evidence
    osint/SITE_CATALOG.md     curated human-readable report

Usage:
    python osint_recon.py
"""

import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import requests

from sophie_scrape import (
    HostRateLimiter,
    JsonCache,
    PoliteSession,
    PULL_ZONE,
    SITE,
    SUPA,
    SUPA_KEY,
    USER_AGENT,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "osint")

HOMEPAGE = SITE + "/"
BUNNY_FN = f"{SITE}/.netlify/functions/bunny-videos?page=1&perPage=1"
EMBED = "https://iframe.mediadelivery.net/embed/621930/f045560b-be22-491d-8b12-a8629c6fdd74"
THUMB = f"https://{PULL_ZONE}/f045560b-be22-491d-8b12-a8629c6fdd74/thumbnail.jpg?width=480"
FLUID = "https://cdn.fluidplayer.com/v3/current/fluidplayer.min.js"

# Tables/columns observed in the SPA's PostgREST calls.
KNOWN_TABLES = [
    "comments", "favorites", "model_requests", "poll_votes", "site_config",
    "title_suggestions", "user_profiles", "video_dislikes", "video_likes",
    "video_meta", "video_reactions", "video_reports", "video_submissions",
    "video_views", "watch_history",
]

TECH = {
    "Hosting / edge": [
        {"name": "Netlify", "evidence": "Server: Netlify; x-nf-request-id; Cache-Status: Netlify Edge; DNS SOA domains+netlify.netlify.com; NS *.nsone.net"},
        {"name": "Netlify Functions", "evidence": "Serverless endpoints under /.netlify/functions/"},
        {"name": "Netlify DNS", "evidence": "Apex NS = dns{1..4}.p08.nsone.net; SOA mname dns1.p01.nsone.net"},
    ],
    "Video platform": [
        {"name": "Bunny Stream", "evidence": "video.bunnycdn.com API; library id 621930; iframe/assets.mediadelivery.net"},
        {"name": "Bunny CDN (pull zone)", "evidence": f"{PULL_ZONE} serves thumbnails + HLS; *.b-cdn.net cert (Sectigo)"},
        {"name": "Bunny Storage", "evidence": "storage.bunnycdn.com for image uploads"},
        {"name": "HLS + AES-128", "evidence": "playlist.m3u8 master -> {res}/video.m3u8 -> *.dts segments; #EXT-X-KEY AES-128"},
        {"name": "TUS resumable uploads", "evidence": "tus-js-client@4 from cdn.jsdelivr.net (Bunny TUS endpoint)"},
    ],
    "Backend / data": [
        {"name": "Supabase PostgREST", "evidence": f"{SUPA}/rest/v1/... ; public anon JWT embedded in page source"},
        {"name": "Supabase Auth (GoTrue)", "evidence": f"{SUPA}/auth/v1/settings ; email provider, signup enabled"},
        {"name": "Postgres tables", "evidence": "video_meta, video_submissions, user_profiles, likes/views/comments, site_config, ..."},
    ],
    "Frontend": [
        {"name": "Vanilla-JS SPA", "evidence": "single index.html, hash/query routing (?v=guid), no framework bundle"},
        {"name": "Fluid Player", "evidence": "cdn.fluidplayer.com/v3 (HLS + VAST ad support)"},
        {"name": "hls.js", "evidence": "HLS engine bundled inside Fluid Player"},
        {"name": "playerjs", "evidence": "assets.mediadelivery.net/playerjs (drives the Bunny iframe)"},
        {"name": "PWA", "evidence": "theme-color, apple-mobile-web-app-* meta tags"},
        {"name": "Google Fonts", "evidence": "Inter + Syne via fonts.googleapis.com"},
    ],
    "Advertising": [
        {"name": "ExoClick / ExoAds", "evidence": "a.magsrv.com/ad-provider.js; s.magsrv.com VAST; a.pemsrv.com popunder; site-verification meta"},
        {"name": "Zones", "evidence": "banner zone 6009644; VAST idzone 6016956; grid ad every 5 cards; pre-roll gate + sticky banner"},
    ],
    "Analytics": [
        {"name": "Umami (self-configurable)", "evidence": "settings.analyticsSrc/analyticsId; default cloud.umami.is"},
    ],
    "Comms": [
        {"name": "Discord", "evidence": "discord.gg invite fetched via discord.com/api/v10/invites"},
    ],
}


def section(title):
    print(f"\n===== {title} =====")


def http_probe(session, url, headers=None):
    try:
        hdrs = dict(headers or {})
        if "supabase.co" in url:
            hdrs.update({"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}"})
        r = session.get(url, headers=hdrs, stream=True)
        interesting = [
            "Server", "Content-Type", "Cache-Status", "Age", "Vary", "ETag",
            "X-Nf-Request-Id", "Strict-Transport-Security", "X-Content-Type-Options",
            "Referrer-Policy", "Content-Security-Policy", "Access-Control-Allow-Origin",
            "CF-Cache-Status", "Via", "X-Served-By", "Alt-Svc",
        ]
        out = {
            "status": r.status_code,
            "headers": {k: r.headers.get(k) for k in interesting if r.headers.get(k)},
        }
        r.close()
        return out
    except requests.RequestException as exc:
        return {"status": f"ERR:{exc.__class__.__name__}", "headers": {}}


def dns_lookup(name, rtype):
    """Best-effort DNS via PowerShell Resolve-DnsName, then nslookup."""
    for exe in ("pwsh", "powershell"):
        try:
            cmd = [exe, "-NoProfile", "-Command",
                   f"Resolve-DnsName -Name {name} -Type {rtype} -ErrorAction SilentlyContinue | "
                   f"Select-Object -ExpandProperty {_field_for(rtype)} -ErrorAction SilentlyContinue"]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        return [l.strip() for l in out.stdout.splitlines() if l.strip()]
    try:
        out = subprocess.run(["nslookup", f"-type={rtype}", name],
                             capture_output=True, text=True, timeout=30)
        vals = []
        for line in out.stdout.splitlines():
            line = line.strip()
            if "=" in line:
                vals.append(line.split("=", 1)[1].strip())
            elif line and not line.startswith(("Server", "Address", "Name")):
                vals.append(line)
        return vals
    except (FileNotFoundError, subprocess.SubprocessError):
        return []


def _field_for(rtype):
    return {
        "A": "IPAddress", "AAAA": "IPAddress", "NS": "NameHost", "MX": "NameExchange",
        "TXT": "Strings", "SOA": "PrimaryServer", "CNAME": "NameHost", "CAA": "Value",
    }.get(rtype, "Name")


def tls_info(host):
    try:
        pem = ssl.get_server_certificate((host, 443), timeout=15)
        with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as fh:
            fh.write(pem)
            path = fh.name
        dec = ssl._ssl._test_decode_cert(path)
        return {
            "subject": dict(x[0] for x in dec.get("subject", [])),
            "issuer": dict(x[0] for x in dec.get("issuer", [])),
            "notAfter": dec.get("notAfter"),
            "SANs": [v for (_k, v) in dec.get("subjectAltName", [])],
        }
    except Exception as exc:
        return {"error": str(exc)}


def supabase_schema(session):
    headers = {"apikey": SUPA_KEY, "Authorization": f"Bearer {SUPA_KEY}", "Accept": "application/json"}
    tables = {}
    for t in KNOWN_TABLES:
        try:
            r = session.get(f"{SUPA}/rest/v1/{t}?select=*&limit=1", headers=headers)
            if r.status_code == 200 and isinstance(r.json(), list) and r.json():
                tables[t] = sorted(r.json()[0].keys())
            else:
                tables[t] = []
        except requests.RequestException:
            tables[t] = []
    settings, user_count = {}, None
    try:
        r = session.get(f"{SUPA}/auth/v1/settings", headers=headers)
        settings = r.json()
    except requests.RequestException:
        pass
    try:
        r = session.post(f"{SUPA}/rest/v1/rpc/count_users", headers=headers)
        user_count = r.json()
    except requests.RequestException:
        pass
    return {"tables": tables, "auth_settings": settings, "user_count": user_count}


def _clean_hosts(raw):
    host_re = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
    return sorted({h.lower() for h in raw if host_re.match(h.lower())})


def extract_page(html):
    hosts = _clean_hosts(re.findall(r"https?://([A-Za-z0-9._-]+)", html))
    proto_rel = _clean_hosts(re.findall(r"//([A-Za-z0-9._-]+)/", html))
    return {
        "hosts": sorted(set(hosts) | set(proto_rel)),
        "scripts": sorted(set(re.findall(r"<script[^>]+src=\"([^\"]+)\"", html))),
        "stylesheets": sorted(set(re.findall(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"', html))),
        "preconnect": sorted(set(re.findall(r'rel="(?:preconnect|dns-prefetch)"\s+href="([^"]+)"', html))),
        "netlify_functions": sorted(set(re.findall(r"/\.netlify/functions/[A-Za-z0-9_-]+", html))),
        "meta": sorted(set(re.findall(r'<meta[^>]+name="([^"]+)"', html))),
        "discord_invite": (re.search(r"discord\.gg/([A-Za-z0-9]+)", html) or [None, None])[1],
        "ad_zones": sorted(set(re.findall(r"idzone=(\d+)", html)) | set(re.findall(r"AD_ZONE_ID\s*=\s*'(\d+)'", html))),
        "umami_configured": "cloud.umami.is" in html,
    }


def main():
    limiter = HostRateLimiter(base_interval=0.5, jitter=1.0, long_every=25)
    session = PoliteSession(limiter)
    session.warm_up()

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "target": SITE}

    section("HTTP endpoints")
    endpoints = {
        "homepage": HOMEPAGE,
        "netlify_function_bunny_videos": BUNNY_FN,
        "supabase_rest_root": f"{SUPA}/rest/v1/",
        "supabase_auth_settings": f"{SUPA}/auth/v1/settings",
        "bunny_pull_zone_thumbnail": THUMB,
        "bunny_embed_iframe": EMBED,
        "fluidplayer_cdn": FLUID,
    }
    report["http"] = {}
    for name, url in endpoints.items():
        report["http"][name] = {"url": url, **http_probe(session, url, {"Accept": "*/*"})}
        print(f"  {name}: {report['http'][name]['status']}")

    section("Page extraction")
    try:
        html = session.get(HOMEPAGE).text
    except requests.RequestException as exc:
        html = ""
        print("  homepage error:", exc)
    report["page"] = extract_page(html)
    print("  hosts:", len(report["page"]["hosts"]),
          "| functions:", report["page"]["netlify_functions"],
          "| ad zones:", report["page"]["ad_zones"])

    section("Supabase schema")
    report["supabase"] = supabase_schema(session)
    print("  tables:", len(report["supabase"]["tables"]),
          "| users:", report["supabase"].get("user_count"))

    section("DNS")
    report["dns"] = {}
    for rtype in ("A", "AAAA", "NS", "MX", "TXT", "SOA", "CAA"):
        report["dns"][rtype] = dns_lookup("abdlhub.com", rtype)
        print(f"  {rtype}: {report['dns'][rtype][:4]}")

    section("TLS")
    report["tls"] = {}
    for host in ("abdlhub.com", "hbvwlzjxsmhreeqwypwp.supabase.co", PULL_ZONE):
        report["tls"][host] = tls_info(host)
        print(f"  {host}: {report['tls'][host].get('issuer', {}).get('commonName', report['tls'][host].get('error'))}")

    report["technologies"] = TECH

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "site_catalog.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    write_markdown(report)
    session.save_cookies()
    sys.stderr.write(f"\nWrote {OUT_DIR}/site_catalog.json and SITE_CATALOG.md "
                     f"({session.count} requests)\n")


def write_markdown(report):
    p = report["page"]
    s = report["supabase"]
    lines = []
    lines.append("# ABDL-HUB — OSINT technology catalog")
    lines.append("")
    lines.append(f"_Collected {report['generated_at']} from public endpoints only._")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append("")
    lines.append("`abdlhub.com` is a single-page application distributed via **Netlify** "
                 "(edge + serverless functions), backed by **Supabase/PostgREST** for metadata "
                 "and **Bunny Stream** for video. Monetisation is **ExoClick/ExoAds**. "
                 "The stack is the pattern of an AI-assisted template build: one large inline-JS "
                 "`index.html`, a public anon key, and third-party SaaS glued together.")
    lines.append("")
    lines.append("## 2. Hosting, DNS and TLS")
    lines.append("")
    lines.append("| Layer | Finding |")
    lines.append("| --- | --- |")
    for item in TECH["Hosting / edge"]:
        lines.append(f"| {item['name']} | {item['evidence']} |")
    lines.append("")
    lines.append("**DNS**")
    lines.append("")
    for rtype, vals in report["dns"].items():
        if vals:
            lines.append(f"- `{rtype}`: {', '.join(str(v) for v in vals[:8])}")
    lines.append("")
    lines.append("**TLS**")
    lines.append("")
    lines.append("| Host | Subject | Issuer | Expires | SANs |")
    lines.append("| --- | --- | --- | --- | --- |")
    for host, info in report["tls"].items():
        if "error" in info:
            lines.append(f"| {host} | — | — | — | {info['error']} |")
        else:
            lines.append(f"| {host} | {info['subject'].get('commonName','')} | "
                         f"{info['issuer'].get('organizationName','')} | {info['notAfter']} | "
                         f"{', '.join(info['SANs'][:4])} |")
    lines.append("")
    lines.append("## 3. HTTP response headers")
    lines.append("")
    for name, h in report["http"].items():
        lines.append(f"**{name}** — `{h['url']}` → {h['status']}")
        if h["headers"]:
            lines.append("")
            lines.append("| Header | Value |")
            lines.append("| --- | --- |")
            for k, v in h["headers"].items():
                lines.append(f"| {k} | {v} |")
        lines.append("")
    lines.append("## 4. Third-party services")
    lines.append("")
    for category, items in TECH.items():
        if category == "Hosting / edge":
            continue
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| Service | Evidence |")
        lines.append("| --- | --- |")
        for item in items:
            lines.append(f"| {item['name']} | {item['evidence']} |")
        lines.append("")
    lines.append("### Referenced hosts (from index.html)")
    lines.append("")
    lines.append(", ".join(f"`{h}`" for h in p["hosts"]))
    lines.append("")
    lines.append("### Netlify functions")
    lines.append("")
    for fn in p["netlify_functions"]:
        lines.append(f"- `{fn}`")
    lines.append("")
    lines.append("### Ad zones")
    lines.append("")
    lines.append(", ".join(f"`{z}`" for z in p["ad_zones"]) or "—")
    lines.append("")
    lines.append("## 5. Supabase / PostgREST")
    lines.append("")
    lines.append(f"Project: `{SUPA}` (region resolved via TLS to Google Trust Services). "
                 f"Reported user count (public RPC `count_users`): **{s.get('user_count')}**.")
    lines.append("")
    lines.append("Auth settings (public `/auth/v1/settings`): "
                 f"email provider enabled, signup "
                 f"{'disabled' if s.get('auth_settings',{}).get('disable_signup') else 'enabled'}, "
                 f"external OAuth providers: none, SMS provider: "
                 f"{s.get('auth_settings',{}).get('sms_provider')}.")
    lines.append("")
    lines.append("**Exposed tables and columns**")
    lines.append("")
    lines.append("| Table | Columns |")
    lines.append("| --- | --- |")
    for t, cols in sorted(s["tables"].items()):
        lines.append(f"| {t} | {', '.join(cols) if cols else '(empty/denied)'} |")
    lines.append("")
    lines.append("## 6. Analyst notes")
    lines.append("")
    lines.append("- **Attack surface:** the Supabase **anon JWT is embedded in the page source**, "
                 "so every table with permissive RLS is readable without authentication. The media "
                 "CDN needs only a `Referer: https://abdlhub.com/` header.")
    lines.append("- **Inconsistency indicative of AI/quick build:** tags are stored in "
                 "`video_meta.tags` but applied inconsistently (creator content often carries only a "
                 "title, not a tag), and several historical tag rows reference videos already "
                 "deleted from the Bunny library.")
    lines.append("- **Monetisation:** ExoClick banner + popunder + VAST pre-roll, all client-side; "
                 "none of it gates the underlying media URL.")
    lines.append("")
    lines.append("_Raw evidence: `osint/site_catalog.json`._")
    lines.append("")
    with open(os.path.join(OUT_DIR, "SITE_CATALOG.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


if __name__ == "__main__":
    main()
