# Portugal Villa Finder — customizable daily search

**Dashboard:** https://assafmarom.github.io/yellow/

**Search editor:** https://assafmarom.github.io/yellow/search.html

**Daily workflow:** https://github.com/Assafmarom/yellow/actions/workflows/publish.yml

## Edit any search requirement without writing code

1. Open the **Search editor** above.
2. Adjust minimum and maximum price, bedroom/bathroom minimums, max driving time, Porto/Lisbon selection and the required garden, garage or renovation switches.
3. Use **Add any requirement** or the presets for supermarket, medical clinic, pharmacy, school, public transport and park.
4. Choose a rule type:
   - **Nearby service:** enter any service such as `supermarket`, `medical clinic` or `physiotherapist`, set distance in km and choose required/optional. Uses Google Places API (New) and estimates **straight-line distance**, not walking/driving distance.
   - **Listing keywords:** a text phrase searched in listing descriptions; a missing phrase is **unverified**, not evidence that the feature is absent. Portuguese spelling may be required.
   - **Free-text wish:** any requirement not covered by structured checks, such as `quiet neighborhood` or `south-facing garden`. Will be flagged for manual verification.
5. Click **Save draft** to store locally in your browser, or **Apply to daily search** to prefill a GitHub issue. Review it and click **Submit new issue** in GitHub. GitHub Actions validates that **the repository owner** created the issue, validates the JSON values, commits `search-config.json`, closes the request and replies with a confirmation.
6. The updated configuration takes effect on the **next daily search** at 06:15 UTC. For an immediate search, manually run the daily workflow via its GitHub Actions page.

Search settings are shared in `search-config.json`. Changes are public to repo viewers if the repository is public. There is **no need to expose any GitHub access token in the website**. GitHub Issues must remain enabled. A maximum of 20 extra rules can be submitted per search to bound API cost and URL length.

## Run a search immediately from the website

Click **▶ Run Search Now** on the [dashboard](https://assafmarom.github.io/yellow/) or [search editor](https://assafmarom.github.io/yellow/search.html).

- The button opens a **pre-filled GitHub issue**. Sign in with your repository-owner account and click **Submit new issue** to approve the request. You don't need to enter API keys or GitHub access tokens in the website.
- The `.github/workflows/run-now.yml` handler accepts only requests from the repository owner with the exact command marker, then dispatches `publish.yml` and closes the GitHub issue with a status link.
- Follow [Search workflow status](https://github.com/Assafmarom/yellow/actions/workflows/publish.yml). The dashboard publishes updated properties when the workflow completes successfully **and** the property API credentials are configured.
- The **Refresh data** button does not run a new search; it only reloads the latest published `properties.json`.
- Run Search Now always uses **already published** `search-config.json` settings. After editing prices or requirements, submit and confirm the settings issue **before** requesting a new search.

## API keys and location checks

Open: https://github.com/Assafmarom/yellow/settings/secrets/actions

- `SCRAPPA_API_KEY` — independent Casa SAPO provider (https://scrappa.co/docs/casa-sapo-api/casa_sapo_search).
- `IDEALISTA_RAPIDAPI_KEY` — subscription to the **exact compatible** Idealista RapidAPI provider. The collector currently expects `idealista-real-estate.p.rapidapi.com` endpoints. Verify compatibility and actual endpoint availability before paying; a key for a different provider is not enough.
- `GOOGLE_MAPS_API_KEY` — optional; for the current collector, enable **both Routes API and Places API (New)** for that Google Cloud project, and restrict the key to those APIs. Only enabling Routes is **not enough** for nearby service requirements. Costs depend on request volumes, quotas and provider billing.

**Without listing API keys the daily workflow cannot retrieve fresh properties.** It will keep the dated initial snapshot rather than manufacturing results. With listing APIs but no Google key, drive times and nearby services remain unverified. A Google Places search may be incomplete; no returned place does not prove the service is absent. The workflow caps Google Places checks at 60 requests per run, and checks at most the newest configured pages from each listing portal.

## Data and status

- `search-config.json`: shared daily search settings.
- `properties.json`: published listings, verification gaps, active search configuration and last updated time.
- `history.json`: first-seen dates and historical prices.
- `scripts/collect.py`: daily collection, listing verification and optional Google Routes/Places checks.
- `.github/workflows/publish.yml`: scheduled collection, tests and Pages deployment.
- `.github/workflows/update-search.yml`: owner-only validation and activation of editor changes.
- `scripts/apply_request.py`: accepts only validated config JSON.
- `search.html`: browser-based search editor.
- `tests/test_collector.py`: tests for configurable prices, bedrooms, custom and nearby rules.

**Important:** Listing details come from providers and require independent confirmation, including the legal status of garages and the accuracy of map coordinates. Nearby medical services do not establish emergency-care access or response times. Automatic WhatsApp alerts are not configured. Existing ChatGPT notifications operate separately.
