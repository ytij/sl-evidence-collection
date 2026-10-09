# Subpoena & preservation target dossier

Who to serve, what to ask for, and by what mechanism. Identifiers below are
those collected in `osint/` and `evidence/`. **Route every request through FL
counsel.**

## Send preservation letters FIRST (today)
The operator is under active takedown pressure (610 of 624 works already
deleted from Bunny). A preservation letter to each party below costs nothing
and stops logs/billing records from aging out while the suit is prepared.

## Targets

| # | Provider | Role / identifier | Request | Mechanism |
|---|----------|-------------------|---------|-----------|
| 1 | **Supabase, Inc.** | Metadata backend, project ref `hbvwlzjxsmhreeqwypwp` | Identity (name, email, IP, timestamps, billing) for uploader `Creator1` = `a89bb9dc-d09f-4475-b9ed-ae398edf928b` and operator `Admin` = `46a556ca-1789-4dd9-a72d-bbe6df94e5c9`; signup/login IPs; the `video_submissions` rows | § 512(h) subpoena + Rule 45 |
| 2 | **Bunny.net (BunnyWay d.o.o.)** | Video host; pull zone `vz-e81debcf-c73.b-cdn.net`, library `621930`, storage zone `abdlhub-images.b-cdn.net` | Account owner identity + billing; upload source IPs/filenames; original file metadata for the 12 Bunny guids | § 512(h) subpoena + Rule 45 |
| 3 | **Netlify, Inc.** | Site host (`Server: Netlify`), DNS (`nsone.net`), serverless functions | Account owner (name, email, billing), domain `abdlhub.com` registration, function invocation logs/IPs | § 512(h) subpoena + Rule 45 |
| 4 | **Domain registrar** (via Netlify Domains) | `abdlhub.com` registration | Registrant name/address/email (unmask WHOIS) | Rule 45 / registrar agent |
| 5 | **ExoClick** | Ad network; zones `6009644`, `6016956`, `6011096`, `6012920` | Payee identity, payout method, revenue for those zones | Rule 45 (monetization → damages) |
| 6 | **Discord, Inc.** | Community; invite `kbnJTj2DB` | Server owner/admin identity behind the invite | Rule 45 |
| 7 | **AbdlMatch.com** | Sponsor/affiliate (`Apache/2.2.15 (CentOS)`) | Registrant + host identity; affiliation with abdlhub | Rule 45 / WHOIS |
| 8 | **Coinbase / exchange** (TBD) | Bitcoin donation address `bc1qmw0zehsntqj0ckwsw4mm44flhcqm7tvzu0xu4h` | Customer identity (only with strong showing; hardest target) | Court order to exchange |
| 9 | **Google / Bing** | Discovery | Delist the infringing `?v=` URLs from search | DMCA § 512(d) (not a subpoena) |

## What each request must establish
1. The account is the **same person/entity** (correlate email, IP, billing across providers — Supabase ↔ Bunny ↔ Netlify ↔ ExoClick).
2. The uploads originated from that account (upload IP logs at Bunny; `video_submissions` provenance at Supabase).
3. The defendant is **in Florida** (billing address, IP geolocation) — confirm venue with Dominic's intel.

## Correlatives we already hold
- Uploader `Creator1` uploaded **all 12** attributed works (see `osint/PUBLIC_EXPOSURE.md`).
- Operator `Admin` `46a556ca-…`; mods `babycakesabdl` (`5c86b4b8-…`, also top uploader), `LightSwitch`.
- Donation BTC address and sponsor domain above.
- Media library id `621930`; Supabase project ref above.
