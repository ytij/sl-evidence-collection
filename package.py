#!/usr/bin/env python3
"""Assemble a lawyer-ready case package.

Gathers the infringement table, damages, attribution, evidence inventory,
chain-of-custody hashes and RFC 3161 timestamps into ``case_package/`` with a
single ``INDEX.md``. Text artifacts are copied; bulk media (captures) is
referenced by path + hash (add ``--include-media`` to copy it in).

Usage:
    python package.py
    python package.py --include-media --zip
"""

import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import takedown  # noqa: E402

PKG = os.path.join(HERE, "case_package")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, HERE).replace("\\", "/")


def load(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return default


def copy_text(src_dir, patterns):
    dest = os.path.join(PKG, os.path.basename(src_dir))
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(src_dir):
        if any(name.endswith(p) for p in patterns):
            shutil.copy2(os.path.join(src_dir, name), os.path.join(dest, name))
    return dest


def main():
    include_media = "--include-media" in sys.argv
    do_zip = "--zip" in sys.argv

    if os.path.exists(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)

    works = takedown.build_works()
    damages = load(os.path.join(HERE, "damages", "damages.json"), {})
    matches = load(os.path.join(HERE, "matches", "matches.json"), {})
    ev = load(os.path.join(HERE, "evidence", "manifest.json"), {"tables": {}})
    ts = load(os.path.join(HERE, "evidence", "timestamps", "index.json"), [])

    # Infringement table.
    with open(os.path.join(PKG, "infringements.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        import csv
        w = csv.DictWriter(fh, fieldnames=list(works[0].keys()))
        w.writeheader()
        w.writerows(works)

    # Works of authorship (originals), if JFF matching has been run.
    results = matches.get("results", [])
    with open(os.path.join(PKG, "works_of_authorship.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["original_id", "original_title", "original_published", "source_url",
                    "matched_rehost_guid", "matched_rehost_title", "score"])
        for r in results:
            o, b = r["original"], (r.get("best_match") or {})
            w.writerow([o["id"], o["title"], o["published_at"], o["source_url"],
                        b.get("guid", ""), b.get("title", ""), b.get("total", "")])

    # Text artifacts.
    copy_text(os.path.join(HERE, "takedowns"), (".txt",))

    # Legal instruments (court-facing drafts).
    legal_src = os.path.join(HERE, "legal")
    legal_dst = os.path.join(PKG, "legal")
    os.makedirs(os.path.join(legal_dst, "preservation"), exist_ok=True)
    for name in os.listdir(legal_src):
        src = os.path.join(legal_src, name)
        if os.path.isfile(src) and name.endswith((".md", ".json")):
            shutil.copy2(src, os.path.join(legal_dst, name))
    pres_src = os.path.join(legal_src, "preservation")
    if os.path.isdir(pres_src):
        for name in os.listdir(pres_src):
            shutil.copy2(os.path.join(pres_src, name), os.path.join(legal_dst, "preservation", name))
    ex_src = os.path.join(legal_src, "exhibits")
    if os.path.isdir(ex_src):
        os.makedirs(os.path.join(legal_dst, "exhibits"), exist_ok=True)
        for name in os.listdir(ex_src):
            shutil.copy2(os.path.join(ex_src, name), os.path.join(legal_dst, "exhibits", name))

    # Evidence inventory.
    with open(os.path.join(PKG, "evidence_index.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        import csv
        w = csv.writer(fh)
        w.writerow(["evidence", "row_count", "sha256", "fetched_at", "note"])
        for name, entry in sorted(ev.get("tables", {}).items()):
            l = entry.get("latest", {})
            w.writerow([name, l.get("row_count", ""), l.get("sha256", ""),
                        l.get("fetched_at", ""), l.get("note", "")])

    if include_media:
        for d in ("captures", "evidence"):
            dst = os.path.join(PKG, d)
            if os.path.exists(d):
                shutil.copytree(os.path.join(HERE, d), dst)

    # Chain of custody: hash everything we produced/copied.
    manifest = []
    for root, _dirs, files in os.walk(PKG):
        for f in files:
            p = os.path.join(root, f)
            manifest.append((rel(p), sha256(p)))
    with open(os.path.join(PKG, "manifest.sha256"), "w", encoding="utf-8", newline="") as fh:
        for r, h in manifest:
            fh.write(f"{h}  {r}\n")

    write_index(works, damages, results, ev, ts, manifest)

    print(f"package: {PKG}")
    print(f"  works: {len(works)} | prompts: {len(results)} | files: {len(manifest)}")

    if do_zip:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        zpath = os.path.join(HERE, f"case_package_{stamp}.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _dirs, files in os.walk(PKG):
                for f in files:
                    p = os.path.join(root, f)
                    z.write(p, os.path.relpath(p, HERE))
        print(f"  zip: {zpath} ({os.path.getsize(zpath):,} bytes)")


def write_index(works, damages, results, ev, ts, manifest):
    L = []
    L.append("# ABDL-HUB — case package")
    L.append("")
    L.append(f"_Generated {datetime.now(timezone.utc).isoformat()}._")
    L.append("")
    L.append("## Parties & attribution")
    L.append("")
    L.append("- **Target site:** https://abdlhub.com (Netlify edge/functions, Supabase backend, Bunny Stream media).")
    L.append("- **Uploader of the subject works:** `Creator1` — Supabase user_id `a89bb9dc-d09f-4475-b9ed-ae398edf928b`.")
    L.append("- **Operator / staff accounts:** `Admin` `46a556ca-…`; mods `babycakesabdl`, `LightSwitch` (see `osint/PUBLIC_EXPOSURE.md`).")
    L.append("- **Defendant location:** Florida (per client); identity to be obtained by subpoena (see `osint/SUBPOENA_TARGETS.md`).")
    L.append("")
    L.append("## Works and infringing copies")
    L.append("")
    L.append("| # | Infringing page | Media | Uploaded | Bytes | Live |")
    L.append("| --- | --- | --- | --- | --- | --- |")
    for i, w in enumerate(works, 1):
        L.append(f"| {i} | {w['page_url']} | {w['stream_url']} | {w['submitted_at'][:10]} | "
                 f"{w['file_size_bytes']} | {'yes' if w['live'] else 'no'} |")
    L.append("")
    if results:
        L.append(f"- Original works matched: **{sum(1 for r in results if r.get('accepted'))}** of {len(results)} "
                 "(see `works_of_authorship.csv` / `matches/`).")
        L.append("")
    else:
        L.append("- Original works (JFF) not yet matched — run `match.py --originals <JFF export>` "
                 "to populate `works_of_authorship.csv`.")
        L.append("")
    if damages:
        L.append("## Damages")
        L.append("")
        sd = damages.get("statutory_damages_usd", {})
        L.append(f"- {damages.get('attributed_works')} works, {damages.get('total_gib')} GiB, "
                 f"{damages.get('total_views'):,} views.")
        L.append(f"- Statutory range/work: ${sd.get('per_work_min'):,}–${sd.get('per_work_max'):,}; "
                 f"willful max ${sd.get('per_work_willful_max'):,} → **aggregate willful max "
                 f"${sd.get('aggregate_willful_max'):,}**.")
        L.append("")
    L.append("## Chain of custody")
    L.append("")
    L.append("- Per-table SHA-256 hashes and fetch provenance: `evidence/manifest.json`.")
    L.append(f"- RFC 3161 trusted timestamps ({len(ts)}): `evidence/timestamps/` (tokens verifiable with `openssl ts -verify`).")
    L.append("- Page captures (HTML+PNG+PDF) hashed in `captures/<run>/manifest.json`.")
    L.append("- Package integrity: `manifest.sha256`.")
    L.append("")
    L.append("## Legal instruments")
    L.append("")
    L.append("- `legal/DECLARATION_1746.md` — custodian declaration (28 U.S.C. § 1746).")
    L.append("- `legal/METHODOLOGY.md` — collection methodology (authentication foundation).")
    L.append("- `legal/SUBPOENA_512h.md` — § 512(h) identification-subpoena package.")
    L.append("- `legal/EXHIBIT_INDEX.md` — Exhibits A–I with hashes and timestamp references.")
    L.append("- `legal/preservation/` — preservation / legal-hold letters (Supabase, Bunny, Netlify, ExoClick).")
    L.append("- `legal/AUTHORITIES.md` — each required element mapped to controlling authority (verified sources).")
    L.append("")
    L.append("## Counsel must supply")
    L.append("")
    L.append("- Complainant identity & contact; copyright registration numbers; the description of each original work.")
    L.append("- Confirm venue; complete and sign the notices in `takedowns/`.")
    L.append("")
    with open(os.path.join(PKG, "INDEX.md"), "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    main()
