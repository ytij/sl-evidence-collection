#!/usr/bin/env python3
"""Build a Notion-import-ready CSV that unifies our automated works with the
client's manual JFF sheet.

Emits:
    notion/abdlhub_stolen_videos.csv   union of both datasets, one schema
    notion/NOTION_SCHEMA.md            property types + import steps

Design: Notion maps CSV headers to database properties by name. We keep the
client's exact property names (ABDL Hub Title, JFF Video ID, Fingerprinted?,
Site screenshot, Line #) so a fresh import lands cleanly, and append our
columns. See JFF_MATCHING.md §3.

Usage:
    python notion_export.py
"""

import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "notion")
OURS = os.path.join(HERE, "sophie_little_all_videos.csv")
HERS = os.path.join(HERE, "manual", "abdlhub_stolen_videos_manual_all.csv")

COLUMNS = [
    "ABDL Hub Title", "JFF Video ID", "Fingerprinted?", "Site screenshot", "Line #",
    "GUID", "Abdlhub Page URL", "Media URL", "Thumbnail URL",
    "Upload Date", "Uploader", "Status", "Duration (s)", "Views",
    "Normalized Title", "Record Source", "Match Confidence",
]


def norm_title(s):
    s = (s or "").lower()
    s = re.sub(r"\.mp4$", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def load_headered(path):
    with open(path, encoding="utf-8-sig") as fh:
        rdr = csv.reader(fh)
        header = [h.strip() for h in next(rdr)]
        return [dict(zip(header, row)) for row in rdr if any(c.strip() for c in row)]


def attributed_uploaders():
    m = {}
    p = os.path.join(HERE, "evidence", "video_submissions.json")
    if os.path.exists(p):
        for row in json.load(open(p, encoding="utf-8"))["rows"]:
            m[re.search(r"([0-9a-f-]{36})", row.get("video_url", "")).group(1)] = row.get("user_id")
    return m


def blank_row():
    return {c: "" for c in COLUMNS}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ours = list(csv.DictReader(open(OURS, encoding="utf-8-sig")))
    hers = load_headered(HERS)
    uploaders = attributed_uploaders()

    rows = []
    for r in ours:
        row = blank_row()
        row["ABDL Hub Title"] = r.get("title", "")
        row["GUID"] = r.get("guid", "")
        row["Abdlhub Page URL"] = r.get("page_url", "")
        row["Media URL"] = r.get("stream_url", "")
        row["Thumbnail URL"] = r.get("thumbnail_url", "")
        row["Upload Date"] = (r.get("upload_date") or "")[:10]
        row["Uploader"] = uploaders.get(r.get("guid", ""), "")
        row["Status"] = "Live" if r.get("stream_http_status") == "200" else "Delisted"
        row["Duration (s)"] = r.get("duration_seconds", "")
        row["Views"] = r.get("views", "")
        row["Normalized Title"] = norm_title(r.get("title", ""))
        row["Record Source"] = "Automated"
        rows.append(row)

    for r in hers:
        row = blank_row()
        row["ABDL Hub Title"] = r.get("ABDL Hub Title", "")
        row["JFF Video ID"] = r.get("JFF Video ID", "")
        row["Fingerprinted?"] = r.get("Fingerprinted?", "")
        row["Site screenshot"] = r.get("Site screenshot", "")
        row["Line #"] = r.get("Line #", "")
        row["Normalized Title"] = norm_title(r.get("ABDL Hub Title", ""))
        row["Record Source"] = "Manual-JFF"
        rows.append(row)

    path = os.path.join(OUT_DIR, "abdlhub_stolen_videos.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    write_schema(len(ours), len(hers), len(rows))
    print(f"wrote {path} ({len(rows)} rows = {len(ours)} automated + {len(hers)} manual)")
    print(f"wrote {os.path.join(OUT_DIR, 'NOTION_SCHEMA.md')}")


def write_schema(n_ours, n_hers, n_total):
    L = [
        "# Notion import schema",
        "",
        f"_Generated {__import__('datetime').date.today().isoformat()} by `notion_export.py`._ "
        "[`REPO_MAP`](../REPO_MAP.md) · [`JFF_MATCHING`](../JFF_MATCHING.md)",
        "",
        "## How to import (fresh)",
        "1. In Notion: **New page → Import → CSV** (or, to add to the existing",
        "   collection, open it and **… → Merge with CSV**).",
        "2. Import **fresh** into an empty database first so the property types",
        "   below are created, then decide what to merge into the live DB.",
        "3. After import, merge duplicates using `Normalized Title` (and `GUID`",
        "   once the matcher fills it).",
        "",
        "## Property types",
        "| Column | Notion type | Notes |",
        "| --- | --- | --- |",
        "| ABDL Hub Title | **Title** | The primary title property. |",
        "| JFF Video ID | Text | 24-hex JustForFans id. |",
        "| Fingerprinted? | Select (Yes/No) | Client's flag. |",
        "| Site screenshot | Text | Filename; attach the file manually (see caveat). |",
        "| Line # | Number | Client's original sequence. |",
        "| GUID | Text | abdlhub media guid. |",
        "| Abdlhub Page URL / Media URL / Thumbnail URL | URL | Live links. |",
        "| Upload Date | Date | ISO `YYYY-MM-DD`. |",
        "| Uploader | Text | Supabase user_id where attributed. |",
        "| Status | Select (Live/Delisted) | Stream reachable today. |",
        "| Duration (s) / Views | Number | From the catalog. |",
        "| Normalized Title | Text | Dedupe/group key. |",
        "| Record Source | Select (Automated/Manual-JFF) | Provenance. |",
        "| Match Confidence | Number | Filled by the matcher. |",
        "",
        "## Caveats",
        "- **Files:** Notion cannot populate a *Files* property from CSV. Keep",
        "  `Site screenshot` as **Text** and attach the PNGs manually, or import it",
        "  as a URL if the images are hosted.",
        "- **Dates** must be ISO (`YYYY-MM-DD`) — already formatted.",
        "- **Checkboxes** do not import reliably from CSV; `Fingerprinted?` is kept",
        "  as a Select.",
        "",
        "## Counts",
        f"- Automated rows: **{n_ours}**",
        f"- Manual-JFF rows: **{n_hers}**",
        f"- Total (pre-dedupe): **{n_total}**",
        "",
    ]
    with open(os.path.join(OUT_DIR, "NOTION_SCHEMA.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
