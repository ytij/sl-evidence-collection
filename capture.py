#!/usr/bin/env python3
"""Capture each infringing page as served (HTML + full-page PNG + PDF).

The API snapshots in ``evidence/`` prove the backend data; a court usually
also wants the page *as rendered to a visitor*. This drives a headless
Chromium through the age gate and saves each video page, then hashes the
artifacts into a manifest.

Requires Playwright (not installed by default):
    pip install playwright
    playwright install chromium

Usage:
    python capture.py                # all attributed works
    python capture.py --limit 2
    python capture.py --headed       # watch it run
"""

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "captures")

ATTRIBUTED_GUIDS = [
    "8f71399f-5565-497a-944f-466ad42b0271", "9627aedf-d3d6-4a5a-8141-6467c764a33a",
    "4478076e-76ec-42d9-886b-a61ba179235a", "39b63ca2-4e5a-406c-94bd-3fb72d55a879",
    "710142df-923e-4ad3-80d0-c7a87391fc3e", "cbc1420c-cd65-4f92-b06c-73092650ab13",
    "c1904e3e-e123-4ddb-8830-b53a7c55a31e", "f64107b2-9919-4c19-99ce-115eaf90432a",
    "02f46a22-2881-4dfa-a888-7f0dfbf3aefb", "50e8212f-eec5-465a-a080-42f4e09fd7f6",
    "26cf42e4-3fb8-44da-9822-7758b3a692fc", "03bfd473-3c67-4bae-aee1-ee7120b6664c",
]


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright not installed. Run: pip install playwright && playwright install chromium")

    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    headed = "--headed" in sys.argv
    guids = ATTRIBUTED_GUIDS[:limit] if limit else ATTRIBUTED_GUIDS

    run_dir = os.path.join(OUT, time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    os.makedirs(run_dir, exist_ok=True)
    records = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"),
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        for i, g in enumerate(guids, 1):
            url = f"https://abdlhub.com/?v={g}"
            rec = {"guid": g, "page_url": url, "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Dismiss the age gate if present.
                btn = page.query_selector("#ageGate .btn-enter")
                if btn and btn.is_visible():
                    btn.click()
                page.wait_for_timeout(3500)
                html = page.content()
                html_path = os.path.join(run_dir, f"{g}.html")
                with open(html_path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(html)
                png_path = os.path.join(run_dir, f"{g}.png")
                page.screenshot(path=png_path, full_page=True)
                pdf_path = os.path.join(run_dir, f"{g}.pdf")
                page.pdf(path=pdf_path, format="A4", print_background=True)
                rec.update({
                    "html": os.path.relpath(html_path, HERE).replace("\\", "/"),
                    "png": os.path.relpath(png_path, HERE).replace("\\", "/"),
                    "pdf": os.path.relpath(pdf_path, HERE).replace("\\", "/"),
                    "html_sha256": sha256(html_path),
                    "png_sha256": sha256(png_path),
                    "pdf_sha256": sha256(pdf_path),
                    "status": "ok",
                })
                print(f"[{i}/{len(guids)}] ok {g}")
            except Exception as exc:  # noqa: BLE001 - record and continue
                rec.update({"status": f"ERR:{exc.__class__.__name__}", "error": str(exc)[:200]})
                print(f"[{i}/{len(guids)}] ERR {g}: {exc}")
            records.append(rec)
            time.sleep(2)
        browser.close()

    manifest = os.path.join(run_dir, "manifest.json")
    with open(manifest, "w", encoding="utf-8", newline="") as fh:
        json.dump({"count": len(records), "records": records}, fh, indent=2, ensure_ascii=False)
    print(f"wrote {manifest}")


if __name__ == "__main__":
    main()
