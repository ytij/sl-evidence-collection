# ABDL-HUB — OSINT technology catalog

_Collected 2026-10-09T04:11:21.796139+00:00 from public endpoints only._

## 1. Summary

`abdlhub.com` is a single-page application distributed via **Netlify** (edge + serverless functions), backed by **Supabase/PostgREST** for metadata and **Bunny Stream** for video. Monetisation is **ExoClick/ExoAds**. The stack is the pattern of an AI-assisted template build: one large inline-JS `index.html`, a public anon key, and third-party SaaS glued together.

## 2. Hosting, DNS and TLS

| Layer | Finding |
| --- | --- |
| Netlify | Server: Netlify; x-nf-request-id; Cache-Status: Netlify Edge; DNS SOA domains+netlify.netlify.com; NS *.nsone.net |
| Netlify Functions | Serverless endpoints under /.netlify/functions/ |
| Netlify DNS | Apex NS = dns{1..4}.p08.nsone.net; SOA mname dns1.p01.nsone.net |

**DNS**

- `A`: 18.208.88.157, 98.84.224.111
- `NS`: dns3.p08.nsone.net, dns2.p08.nsone.net, dns1.p08.nsone.net, dns4.p08.nsone.net
- `SOA`: dns1.p01.nsone.net

**TLS**

| Host | Subject | Issuer | Expires | SANs |
| --- | --- | --- | --- | --- |
| abdlhub.com | abdlhub.com | Let's Encrypt | Nov 26 17:45:14 2026 GMT | *.abdlhub.com, abdlhub.com |
| hbvwlzjxsmhreeqwypwp.supabase.co | supabase.co | Google Trust Services | Nov 24 12:15:45 2026 GMT | supabase.co, *.supabase.co |
| vz-e81debcf-c73.b-cdn.net | *.b-cdn.net | Sectigo Limited | Nov 11 23:59:59 2026 GMT | *.b-cdn.net, b-cdn.net |

## 3. HTTP response headers

**homepage** — `https://abdlhub.com/` → 200

| Header | Value |
| --- | --- |
| Server | Netlify |
| Content-Type | text/html; charset=UTF-8 |
| Cache-Status | "Netlify Edge"; hit; ttl=31520745 |
| Age | 15255 |
| Vary | Accept-Encoding |
| ETag | "f3c61ef8b3825974fa247f26e228d4c2-ssl-df" |
| X-Nf-Request-Id | 01M4FDQGSS5J3AA21WVZ7C5XHK |
| Strict-Transport-Security | max-age=31536000 |
| X-Content-Type-Options | nosniff |
| Referrer-Policy | strict-origin-when-cross-origin |

**netlify_function_bunny_videos** — `https://abdlhub.com/.netlify/functions/bunny-videos?page=1&perPage=1` → 200

| Header | Value |
| --- | --- |
| Server | Netlify |
| Content-Type | application/json |
| Cache-Status | "Netlify Durable"; hit; ttl=1486, "Netlify Edge"; fwd=miss; fwd-status=200; stored |
| Age | 315 |
| Vary | Accept-Encoding |
| X-Nf-Request-Id | 01M4FDQHE1YPM8P23QWZSVXKXQ |
| Strict-Transport-Security | max-age=31536000 |
| Access-Control-Allow-Origin | https://abdlhub.com |

**supabase_rest_root** — `https://hbvwlzjxsmhreeqwypwp.supabase.co/rest/v1/` → 401

| Header | Value |
| --- | --- |
| Server | cloudflare |
| Content-Type | application/json;charset=UTF-8 |
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload |
| X-Content-Type-Options | nosniff |
| Access-Control-Allow-Origin | * |
| Alt-Svc | h3=":443"; ma=86400 |

**supabase_auth_settings** — `https://hbvwlzjxsmhreeqwypwp.supabase.co/auth/v1/settings` → 200

| Header | Value |
| --- | --- |
| Server | cloudflare |
| Content-Type | application/json |
| Vary | Origin, Accept-Encoding |
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload |
| X-Content-Type-Options | nosniff |
| CF-Cache-Status | DYNAMIC |
| Alt-Svc | h3=":443"; ma=86400 |

**bunny_pull_zone_thumbnail** — `https://vz-e81debcf-c73.b-cdn.net/f045560b-be22-491d-8b12-a8629c6fdd74/thumbnail.jpg?width=480` → 200

| Header | Value |
| --- | --- |
| Server | BunnyCDN-IL1-894 |
| Content-Type | image/jpeg |
| Access-Control-Allow-Origin | * |

**bunny_embed_iframe** — `https://iframe.mediadelivery.net/embed/621930/f045560b-be22-491d-8b12-a8629c6fdd74` → 200

| Header | Value |
| --- | --- |
| Server | Kestrel |
| Content-Type | text/html; charset=utf-8 |
| Access-Control-Allow-Origin | * |

**fluidplayer_cdn** — `https://cdn.fluidplayer.com/v3/current/fluidplayer.min.js` → 200

| Header | Value |
| --- | --- |
| Server | CDN77-Turbo |
| Content-Type | application/javascript |
| Age | 6267016 |
| Vary | Accept-Encoding |
| ETag | W/"6a69f28b-42e2b" |
| Access-Control-Allow-Origin | * |
| Alt-Svc | h3=":443"; ma=86400 |

## 4. Third-party services

### Video platform

| Service | Evidence |
| --- | --- |
| Bunny Stream | video.bunnycdn.com API; library id 621930; iframe/assets.mediadelivery.net |
| Bunny CDN (pull zone) | vz-e81debcf-c73.b-cdn.net serves thumbnails + HLS; *.b-cdn.net cert (Sectigo) |
| Bunny Storage | storage.bunnycdn.com for image uploads |
| HLS + AES-128 | playlist.m3u8 master -> {res}/video.m3u8 -> *.dts segments; #EXT-X-KEY AES-128 |
| TUS resumable uploads | tus-js-client@4 from cdn.jsdelivr.net (Bunny TUS endpoint) |

### Backend / data

| Service | Evidence |
| --- | --- |
| Supabase PostgREST | https://hbvwlzjxsmhreeqwypwp.supabase.co/rest/v1/... ; public anon JWT embedded in page source |
| Supabase Auth (GoTrue) | https://hbvwlzjxsmhreeqwypwp.supabase.co/auth/v1/settings ; email provider, signup enabled |
| Postgres tables | video_meta, video_submissions, user_profiles, likes/views/comments, site_config, ... |

### Frontend

| Service | Evidence |
| --- | --- |
| Vanilla-JS SPA | single index.html, hash/query routing (?v=guid), no framework bundle |
| Fluid Player | cdn.fluidplayer.com/v3 (HLS + VAST ad support) |
| hls.js | HLS engine bundled inside Fluid Player |
| playerjs | assets.mediadelivery.net/playerjs (drives the Bunny iframe) |
| PWA | theme-color, apple-mobile-web-app-* meta tags |
| Google Fonts | Inter + Syne via fonts.googleapis.com |

### Advertising

| Service | Evidence |
| --- | --- |
| ExoClick / ExoAds | a.magsrv.com/ad-provider.js; s.magsrv.com VAST; a.pemsrv.com popunder; site-verification meta |
| Zones | banner zone 6009644; VAST idzone 6016956; grid ad every 5 cards; pre-roll gate + sticky banner |

### Analytics

| Service | Evidence |
| --- | --- |
| Umami (self-configurable) | settings.analyticsSrc/analyticsId; default cloud.umami.is |

### Comms

| Service | Evidence |
| --- | --- |
| Discord | discord.gg invite fetched via discord.com/api/v10/invites |

### Referenced hosts (from index.html)

`a.magsrv.com`, `a.pemsrv.com`, `abdlhub.com`, `assets.mediadelivery.net`, `cdn.fluidplayer.com`, `cdn.jsdelivr.net`, `cloud.umami.is`, `discord.com`, `discord.gg`, `fonts.googleapis.com`, `hbvwlzjxsmhreeqwypwp.supabase.co`, `iframe.mediadelivery.net`, `s.magsrv.com`, `schema.org`, `storage.bunnycdn.com`, `video.bunnycdn.com`, `vz-e81debcf-c73.b-cdn.net`, `www.google.com`

### Netlify functions

- `/.netlify/functions/bunny-videos`
- `/.netlify/functions/request-upload`
- `/.netlify/functions/set-title`
- `/.netlify/functions/upload-avatar`

### Ad zones

`6009644`, `6016956`

## 5. Supabase / PostgREST

Project: `https://hbvwlzjxsmhreeqwypwp.supabase.co` (region resolved via TLS to Google Trust Services). Reported user count (public RPC `count_users`): **728**.

Auth settings (public `/auth/v1/settings`): email provider enabled, signup enabled, external OAuth providers: none, SMS provider: twilio.

**Exposed tables and columns**

| Table | Columns |
| --- | --- |
| comments | body, created_at, id, likes, name, user_id, video_guid |
| favorites | (empty/denied) |
| model_requests | (empty/denied) |
| poll_votes | choice, created_at, poll_id, user_id, username |
| site_config | key, value |
| title_suggestions | (empty/denied) |
| user_profiles | bio, created_at, is_admin, is_mod, profile_picture_url, public_profile, show_watch_history, supporter_tier, supporter_until, updated_at, user_id, username, username_locked |
| video_dislikes | count, guid |
| video_likes | count, guid |
| video_meta | category, description, episode, guid, series_name, tags |
| video_reactions | count, emoji, video_guid |
| video_reports | (empty/denied) |
| video_submissions | category, created_at, description, file_size, id, rejection_reason, status, thumbnail_url, title, user_id, video_url |
| video_views | guid, views |
| watch_history | (empty/denied) |

## 6. Analyst notes

- **Attack surface:** the Supabase **anon JWT is embedded in the page source**, so every table with permissive RLS is readable without authentication. The media CDN needs only a `Referer: https://abdlhub.com/` header.
- **Inconsistency indicative of AI/quick build:** tags are stored in `video_meta.tags` but applied inconsistently (creator content often carries only a title, not a tag), and several historical tag rows reference videos already deleted from the Bunny library.
- **Monetisation:** ExoClick banner + popunder + VAST pre-roll, all client-side; none of it gates the underlying media URL.
- **See also:** `osint/PUBLIC_EXPOSURE.md` for the uploader-attribution and public-data-exposure review (read-only via the published anon key).

_Raw evidence: `osint/site_catalog.json`._
