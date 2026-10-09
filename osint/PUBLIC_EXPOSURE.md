# ABDL-HUB — public exposure & attribution

_Read-only via the site's own published anon key. No authentication was bypassed, no privileged key used, nothing written, no action endpoint invoked._

## 1. What the backend exposes publicly

- **364 user profiles** (usernames, admin/mod flags, supporter tier, signup date).
- **83 video submissions** — each with the **uploader's `user_id`**, title, description, file size, timestamp and the Bunny Stream embed URL.
- **93 comments** with author names.
- `site_config` (settings, polls, donation address).

Properly protected (RLS returns no rows to the anon key): `favorites`, `watch_history`, `video_reports`, `model_requests`, `title_suggestions`. The Supabase admin API (`/auth/v1/admin/*`) is not exposed — it needs the service key, which is not present anywhere in the client.

**No secret material leaked in `site_config`** (keys checked: poll_votes, polls, settings). The anon JWT itself is public by design.

## 2. Operator & staff accounts

| Role | Username | user_id |
| --- | --- | --- |
| mod | babycakesabdl | `5c86b4b8-5f02-4d6a-a649-aebac3d99a78` |
| admin | Admin | `46a556ca-1789-4dd9-a72d-bbe6df94e5c9` |
| mod | LightSwitch | `0b607c1d-5bb3-4ee3-a26e-e7180ed7af13` |

## 3. Attribution of the Sophie Little / "Sofia" rehosts

All **12** submissions titled *sofia* were uploaded by account **`Creator1`** (`a89bb9dc-d09f-4475-b9ed-ae398edf928b`).

| Submission | Date | Size (bytes) | Guid | Live now | Leaked links |
| --- | --- | --- | --- | --- | --- |
| 9 | 2026-07-15 |  | `8f71399f-5565-497a-944f-466ad42b0271` | yes |  |
| 10 | 2026-07-15 |  | `9627aedf-d3d6-4a5a-8141-6467c764a33a` | yes |  |
| 33 | 2026-07-20 |  | `4478076e-76ec-42d9-886b-a61ba179235a` | yes |  |
| 34 | 2026-07-20 |  | `39b63ca2-4e5a-406c-94bd-3fb72d55a879` | yes |  |
| 70 | 2026-07-28 | 1343474743 | `710142df-923e-4ad3-80d0-c7a87391fc3e` | yes |  |
| 71 | 2026-07-28 | 945168761 | `cbc1420c-cd65-4f92-b06c-73092650ab13` | yes |  |
| 72 | 2026-08-03 | 79043763 | `c1904e3e-e123-4ddb-8830-b53a7c55a31e` | yes |  |
| 73 | 2026-08-03 | 472250821 | `f64107b2-9919-4c19-99ce-115eaf90432a` | yes |  |
| 80 | 2026-08-24 | 1404796613 | `02f46a22-2881-4dfa-a888-7f0dfbf3aefb` | yes |  |
| 86 | 2026-09-16 | 1430901714 | `50e8212f-eec5-465a-a080-42f4e09fd7f6` | yes |  |
| 87 | 2026-09-25 | 1392753733 | `26cf42e4-3fb8-44da-9822-7758b3a692fc` | yes | REDDIT, Thisvid:findrascalandfindherold |
| 88 | 2026-09-29 | 1661093606 | `03bfd473-3c67-4bae-aee1-ee7120b6664c` | yes |  |

The submission **descriptions** leak the original creator's other identities (e.g. a Reddit handle and a ThisVid account) and the provenance of the files (2015 Samsung Galaxy captures), which supports a chain-of-custody narrative.

## 4. Evidence the operator ignores takedowns

> **Wildboy** (2026-09-04): Too young! Not cool.
Fuck this twisted site.im reporting it

> **lkxentertainmentltd** (2026-09-29): To the person who runs this site if you don’t take down every single one of my videos I will sue you. I already have all of your personal information because my videos are completely traceable so I know who you are. Remove my videos or you’re going to be in serious legal trouble

> **lkxentertainmentltd** (2026-09-29): To the person who runs this site if you don’t take down every single one of my videos I will sue you. I already have all of your personal information because my videos are completely traceable so I know who you are. Remove my videos or you’re going to be in serious legal trouble

> **lkxentertainmentltd** (2026-09-29): To the person who runs this site if you don’t take down every single one of my videos I will sue you. I already have all of your personal information because my videos are completely traceable so I know who you are. Remove my videos or you’re going to be in serious legal trouble

> **lkxentertainmentltd** (2026-09-29): To the person who runs this site if you don’t take down every single one of my videos I will sue you. I already have all of your personal information because my videos are completely traceable so I know who you are. Remove my videos or you’re going to be in serious legal trouble

## 5. Operator pivot points (OSINT leads)

- **Bitcoin donation address** in `site_config.settings.donate`.
- **Sponsor / affiliated site**: `AbdlMatch.com` (image served from a second Bunny zone, `abdlhub-images.b-cdn.net`).
- **Discord** invite in the page header (currently expired).
