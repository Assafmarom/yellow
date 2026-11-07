# Portugal Villa Finder

Live dashboard for houses/villas near Porto or Lisbon.

## Website

After GitHub Pages is enabled at **Settings → Pages → Build and deployment → GitHub Actions**, the site will be at:

https://assafmarom.github.io/yellow/

**Repository currently private:** standard free GitHub Pages public hosting requires a public repository. Open Settings → General → Danger Zone → Change repository visibility → Public. Do this only if you are comfortable publishing this website and listing data.

## Daily search

GitHub Actions workflow: `.github/workflows/publish.yml`; scheduled at **06:15 UTC daily**.

Search criteria: €350,000–€400,000, 4+ bedrooms, 2+ bathrooms, new or fully renovated, garden and enclosed garage; estimated 40-minute drive to Porto or Lisbon where Google Routes and property coordinates allow verification.

The current three listings are a **7 November 2026 historical snapshot**, not verified as currently available. Until provider credentials are configured, the site will continue to show that dated snapshot.

## Required API secrets

Settings → Secrets and variables → Actions → New repository secret:

- `SCRAPPA_API_KEY`: independent Scrappa Casa SAPO API: https://scrappa.co/docs/casa-sapo-api/casa_sapo_search
- `IDEALISTA_RAPIDAPI_KEY`: independent apidea Idealista RapidAPI endpoint: https://apidea.es/en/idealista-api-python
- `GOOGLE_MAPS_API_KEY`: optional Google Routes API for travel-time verification.

At least one property API key is needed for new listings. Both are recommended. These are independent third-party services; fees, quotas and actual compatibility must be verified with the providers. If Idealista district autocomplete fails, add repository variable `IDEALISTA_LOCATION_IDS` (comma-separated approved Portugal district IDs).

## Launch

1. Make the repository public if appropriate.
2. Enable Pages (GitHub Actions source).
3. Add API credentials as secrets (never commit credentials).
4. Run Actions → **Update and publish Portugal Villa Finder** → Run workflow.
5. Visit https://assafmarom.github.io/yellow/

The site reads `properties.json` when opened and every five minutes while open. The scheduled collector updates the JSON and stores price changes in `history.json`.

**Notes:** API results do not guarantee listing freshness, full geographical coverage or property attributes. A missing garden/garage or unverified drive time must not be interpreted as a confirmed match. The ChatGPT daily search and its notifications are separate from this workflow. WhatsApp delivery is not configured.
