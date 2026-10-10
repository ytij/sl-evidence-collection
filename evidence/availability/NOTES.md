# Availability audit — correction note

## What happened
`availability.py` misclassified every live work as taken down.

- `probe_stream()` returns the HTTP status as an **int** (`200`), but the
  delta logic compared it to the **string** `"200"`, so `now_live` was always
  `False`. Result: every previously-live work was reported as
  `TAKEN_DOWN_SINCE` and the summary showed `now_live=0`.
- Two snapshots produced with this bug —
  `20261010T070837Z` and `20261010T071037Z` — were **discarded** (they were
  never committed). Do not rely on them.

## What we actually found
- A serial diagnostic (same URLs, gentle pacing) returned **HTTP 200 for all 14
  previously-live works and 40/40 sampled catalog streams** — the content was up.
- After fixing the int/str comparison, a full re-audit
  (**`20261010T071519Z`**) reports:
  - `now_live = 14`, `still_live = 14`, `taken_down_since = 0`, `still_down = 610`
  - catalog still 3215 items; `video_meta` still 2988 rows.

## Conclusion
**The 14 subject works are still up.** No takedown of these has occurred as of
the corrected audit. The earlier "everything taken down" readings were a bug in
our tool, not a change on the site.

## Fix
`availability.py` now compares `str(status) == "200"` (both prior and current).
Re-run any time with:
```
python availability.py --workers 4 --delay 0.25
python timestamp.py evidence/availability/<stamp>/snapshot.json
```
