# Notion import schema

_Generated 2026-10-09 by `notion_export.py`._ [`REPO_MAP`](../REPO_MAP.md) · [`JFF_MATCHING`](../JFF_MATCHING.md)

## How to import (fresh)
1. In Notion: **New page → Import → CSV** (or, to add to the existing
   collection, open it and **… → Merge with CSV**).
2. Import **fresh** into an empty database first so the property types
   below are created, then decide what to merge into the live DB.
3. After import, merge duplicates using `Normalized Title` (and `GUID`
   once the matcher fills it).

## Property types
| Column | Notion type | Notes |
| --- | --- | --- |
| ABDL Hub Title | **Title** | The primary title property. |
| JFF Video ID | Text | 24-hex JustForFans id. |
| Fingerprinted? | Select (Yes/No) | Client's flag. |
| Site screenshot | Text | Filename; attach the file manually (see caveat). |
| Line # | Number | Client's original sequence. |
| GUID | Text | abdlhub media guid. |
| Abdlhub Page URL / Media URL / Thumbnail URL | URL | Live links. |
| Upload Date | Date | ISO `YYYY-MM-DD`. |
| Uploader | Text | Supabase user_id where attributed. |
| Status | Select (Live/Delisted) | Stream reachable today. |
| Duration (s) / Views | Number | From the catalog. |
| Normalized Title | Text | Dedupe/group key. |
| Record Source | Select (Automated/Manual-JFF) | Provenance. |
| Match Confidence | Number | Filled by the matcher. |

## Caveats
- **Files:** Notion cannot populate a *Files* property from CSV. Keep
  `Site screenshot` as **Text** and attach the PNGs manually, or import it
  as a URL if the images are hosted.
- **Dates** must be ISO (`YYYY-MM-DD`) — already formatted.
- **Checkboxes** do not import reliably from CSV; `Fingerprinted?` is kept
  as a Select.

## Counts
- Automated rows: **624**
- Manual-JFF rows: **74**
- Total (pre-dedupe): **698**
