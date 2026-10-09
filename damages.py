#!/usr/bin/env python3
"""Aggregate the factual damages inputs from the collected evidence.

Produces damages/damages.json and damages/damages.md: work count, sizes,
durations, views, the infringement timeline, a clearly-labelled illustrative
revenue model, and the § 504(c) statutory matrix.

Usage:
    python damages.py
"""

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "evidence")
OUT = os.path.join(HERE, "damages")
ALL_CSV = os.path.join(HERE, "sophie_little_all_videos.csv")
LIVE_CSV = os.path.join(HERE, "sophie_little_live_videos.csv")

ATTRIBUTED_UPLOADER = "a89bb9dc-d09f-4475-b9ed-ae398edf928b"
TITLE_PATTERN = re.compile(r"sofia", re.I)

# Illustrative ad monetization (EDIT before relying on it); USD per 1000 views.
RPM_SCENARIOS = {"low": 1.0, "mid": 3.0, "high": 8.0}
STATUTORY = {"min": 750, "max": 30000, "willful_max": 150000}


def load_rows(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        return {r["guid"]: r for r in csv.DictReader(fh)}


def guid_of(url):
    m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", url or "")
    return m.group(1) if m else None


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def main():
    os.makedirs(OUT, exist_ok=True)
    subs = json.load(open(os.path.join(EVIDENCE, "video_submissions.json"), encoding="utf-8"))["rows"]
    live = load_rows(LIVE_CSV)

    works = []
    for s in subs:
        if s.get("user_id") != ATTRIBUTED_UPLOADER and not TITLE_PATTERN.search(s.get("title") or ""):
            continue
        g = guid_of(s.get("video_url"))
        row = live.get(g, {})
        works.append({
            "submission_id": s["id"],
            "title": s["title"],
            "guid": g,
            "submitted_at": s["created_at"],
            "file_size_bytes": to_int(s.get("file_size")),
            "duration_seconds": to_int(row.get("duration_seconds")),
            "views": to_int(row.get("views")),
            "live": g in live,
        })

    total_bytes = sum(w["file_size_bytes"] for w in works)
    total_duration = sum(w["duration_seconds"] for w in works)
    total_views = sum(w["views"] for w in works)
    dates = sorted(w["submitted_at"] for w in works if w["submitted_at"])

    revenue = {k: round(total_views / 1000 * rpm, 2) for k, rpm in RPM_SCENARIOS.items()}
    n = len(works)

    report = {
        "attributed_works": n,
        "live_works": sum(1 for w in works if w["live"]),
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / (1024 ** 3), 2),
        "total_duration_seconds": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2),
        "total_views": total_views,
        "first_upload": dates[0] if dates else None,
        "last_upload": dates[-1] if dates else None,
        "illustrative_ad_revenue_usd": revenue,
        "statutory_damages_usd": {
            "per_work_min": STATUTORY["min"],
            "per_work_max": STATUTORY["max"],
            "per_work_willful_max": STATUTORY["willful_max"],
            "aggregate_min": STATUTORY["min"] * n,
            "aggregate_max": STATUTORY["max"] * n,
            "aggregate_willful_max": STATUTORY["willful_max"] * n,
        },
        "works": works,
    }

    with open(os.path.join(OUT, "damages.json"), "w", encoding="utf-8", newline="") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    L = [
        "# Damages inputs — ABDL-HUB",
        "",
        f"- **Attributed works:** {n} ({report['live_works']} currently live)",
        f"- **Infringement window:** {report['first_upload'][:10]} → {report['last_upload'][:10]}",
        f"- **Total media:** {report['total_gib']} GiB across {n} works",
        f"- **Total runtime:** {report['total_duration_hours']} hours",
        f"- **Recorded views (live works):** {total_views:,}",
        "",
        "## § 504(c) statutory damages (17 U.S.C.)",
        "",
        f"| Basis | Per work | × {n} works |",
        "| --- | --- | --- |",
        f"| Ordinary minimum | ${STATUTORY['min']:,} | ${report['statutory_damages_usd']['aggregate_min']:,} |",
        f"| Ordinary maximum | ${STATUTORY['max']:,} | ${report['statutory_damages_usd']['aggregate_max']:,} |",
        f"| **Willful maximum** | **${STATUTORY['willful_max']:,}** | **${report['statutory_damages_usd']['aggregate_willful_max']:,}** |",
        "",
        "_Statutory damages require timely registration (17 U.S.C. § 412)._",
        "",
        "## Illustrative ad revenue (NOT evidence — editable assumptions)",
        "",
        f"Assumes {total_views:,} views at USD per 1,000 views:",
        "",
        "| Scenario | RPM | Implied revenue |",
        "| --- | --- | --- |",
    ]
    for k, rpm in RPM_SCENARIOS.items():
        L.append(f"| {k} | ${rpm:.2f} | ${revenue[k]:,.2f} |")
    L += [
        "",
        "Excludes affiliate (`AbdlMatch.com`), supporter subscriptions, and Bitcoin donations — "
        "all additional profit channels (§ 504(b)). Replace with actual figures in discovery.",
        "",
        "## Works",
        "",
        "| # | Title | Submitted | Size (GiB) | Views | Live |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for i, w in enumerate(works, 1):
        L.append(f"| {i} | {w['title'][:60]} | {w['submitted_at'][:10]} | "
                 f"{w['file_size_bytes'] / 1024**3:.2f} | {w['views']:,} | {'yes' if w['live'] else 'no'} |")
    with open(os.path.join(OUT, "damages.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(L) + "\n")

    print(f"{n} works | {report['total_gib']} GiB | {total_views:,} views | "
          f"willful max ${report['statutory_damages_usd']['aggregate_willful_max']:,}")
    print(f"wrote {OUT}/damages.json and damages.md")


if __name__ == "__main__":
    main()
