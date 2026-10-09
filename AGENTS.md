# AGENTS.md

This repo is a **copyright evidence-collection project** (see `HANDOVER.md`
for the full brief and `TODO.md` for the plan). Read `HANDOVER.md` first.

## Non-negotiable rules
- **Legality gate:** content is plain consensual adult age-play, no depiction of
  a minor (real or simulated). If that ever changes, stop — it is a criminal
  matter, not a civil-case input.
- **Read-only public access only.** Use the site's own published Supabase anon
  key. Never bypass auth, use a `service_role` key, write data, call the
  auth-gated Netlify functions, or probe partner infrastructure
  (`AbdlMatch.com`). This is not legal advice.
- **Be invisible:** keep collection low-profile (per-host pacing, caching,
  browser headers). Re-runs should make ~0 requests.
- **Never alter or hand-edit tracked evidence.** Append; re-snapshot rather than
  edit. Keep `evidence/*.json` and `captures/**` pinned `-text` in
  `.gitattributes` so hashes survive checkout.
- **Commit early and often.** Do not rewrite history.

## Common commands
```powershell
python sophie_scrape.py --verify --out sophie_little_all_videos.csv --live-out sophie_little_live_videos.csv
python osint_recon.py
python osint/public_exposure.py
python evidence_store.py evidence      # verify all SHA-256 hashes -> all OK
python timestamp.py                    # RFC 3161 timestamp
python capture.py ; python archive.py  # page captures / Wayback
python takedown.py ; python damages.py ; python package.py --zip
```

## Environment
Windows / pwsh, Python 3.11. `openssl`/`ots` are absent; Playwright + Chromium
are installed. `.cache/` is gitignored. Key IDs and the API map are in
`HANDOVER.md` §4 and §13.
