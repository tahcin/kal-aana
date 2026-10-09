# How it uses SerpApi

Every engine and parameter Kal Aana uses, the choices that save credits, what each run costs, and what another city or all of India would cost.

[Back to README](../README.md)

## Engines and parameters

| Engine | Parameters | What it measures |
|---|---|---|
| `google_maps` | `q="Regional Transport Office"` or `"Sub Registrar Office"`, `ll=@12.9716,77.5946,11z`, `gl=in`, `hl=en`, `google_domain=google.co.in`, 2 to 3 pages | Every listing a citizen might find: phone, hours, website, rating, review count, the `unclaimed_listing` flag |
| `google_maps` | `q="<office name>"` (one targeted search for each office the sweep didn't confirm) | The office's real listing, told apart from agents trading on its name |
| `google_maps_reviews` | `data_id`, `sort_by=newestFirst`, `next_page_token`, `num=20` | An unbiased sample of recent reviews: the only sample the counts come from |
| `google_maps_reviews` | `data_id`, `query=phone`, `bribe` or `agent` (per office type) | Targeted evidence for quotes. Biased by design, so it never counts towards shares |
| `google` | `q="<office> phone number"`, `location=Bengaluru,Karnataka,India` | What a citizen sees when they search: knowledge panel, local pack, snippets |
| `google_ai_overview` | `page_token` from the search above | What Google's AI tells the citizen, with every number and PIN checked against the directory |
| `google_ai_mode` | the same `q`, `location`, `gl=in`, `hl=en` | Google's other AI answer to the same question, checked the same way, to compare the two |
| `bing_maps` | `q="<office name>"`, `cp=12.9716~77.5946` | The office outside Google, matched to its Google listing by location (within 400 m) or by name |

Every result keeps its `search_metadata.id`, so each finding can be traced back to the search behind it.

### Live searches in the chat and MCP server

For questions the saved data doesn't cover (documents, fees, procedures, tracking, outages), the chat and the MCP server's two live tools search at the moment of asking (`kalaana/live.py`):

| Engine | Parameters | Why |
|---|---|---|
| `google` | `q`, `location=Bengaluru,Karnataka,India`, `gl=in`, `hl=en`, `num=10`, and `as_sitesearch=gov.in` for the government-sites-first search | Answers from official sites first; each result is marked "Government site" or "Other site". A `site:` operator in the query was ignored in testing, so the parameter is used instead |
| `google_news` | `q`, `gl=in`, `hl=en` | Recent news, for questions such as whether a portal is down today |

These searches are rationed (see [Live search allowance](setup.md#live-search-allowance)).

### The SDK and the Account API

All calls go through SerpApi's Python SDK, the `serpapi` package (the optional extra `live`, `pip install -e ".[live]"`). `kalaana/client.py` creates a `serpapi.Client` on the first live search and calls its `search()` with the parameters above, wrapped in Kal Aana's own on-disk cache, per-run budget, dry run (`--plan`) and key redaction. The live search reads the remaining credits from SerpApi's free Account API (the SDK's `account()`, checked at most once a minute) and stops once the account has `KALAANA_LIVE_RESERVE` credits or fewer left (default 250), so the credits kept for refreshing the dataset are never touched.

## Choices that save credits

- **No place-details calls.** The Maps search result already has the phone, hours and `unclaimed_listing`. For KA-05 it matched the place-details call field for field, which saves one credit per office.
- **Adaptive review paging.** We read newest-first pages until an office has 15 reviews with text (at most 4 pages), because about two in three recent reviews are stars only.
- **Keyword pages are skipped** when the newest-first pages already returned every review the listing has.
- **`--plan`** counts the fresh searches a run would make before it spends anything.

## Credits per run

| Run | Fresh searches (empty cache) | Re-run |
|---|---|---|
| `collect rto`: 13 offices, Maps listings plus reviews | 88 (8 `google_maps`, 80 `google_maps_reviews`) | 0 |
| `citizen rto`: Search, AI Overview and AI Mode per office | 36 (13 `google`, 10 `google_ai_overview`, 13 `google_ai_mode`) | 0 |
| `crosscheck rto`: Bing Maps per office | 13 `bing_maps` | 0 |
| **The whole RTO report card** | **137, about 10.5 per office** | **0** |
| `collect subregistrar --sample-offices 43`: 3 Maps pages, targeted searches, reviews for every listed office | 286 (45 `google_maps`, 241 `google_maps_reviews`) | 0 |
| `citizen subregistrar` | 118 (42 `google`, 34 `google_ai_overview`, 42 `google_ai_mode`; one more AI Overview came inside its Google search, so 35 are shown) | 0 |
| `crosscheck subregistrar` | 43 `bing_maps` | 0 |
| **The whole sub-registrar report card** | **447, about 10.4 per office** | **0** |
| `collect passport --pages 2`, `citizen passport`, `crosscheck passport`: 4 offices | 44 (8 `google_maps`, 21 `google_maps_reviews`, 4 `google`, 3 `google_ai_overview`, 4 `google_ai_mode`, 4 `bing_maps`) | 0 |

SerpApi's Account API shows 647 searches used in all; 628 are behind the three report cards (each listed by engine in the snapshots). The rest went on the RTO pilot, one-off tests of the AI Mode and Bing Maps engines, and early review pages from agents' listings that the matcher now rejects. Failed calls (SerpApi returned 503 four times) cost nothing; one office, Halasooru, is marked "not checked" because its Google search kept failing.

## Another city

Nothing in the audit is tied to Bengaluru, and it costs about **10.5 searches per office** (628 for 60 offices):

| Offices audited | Searches, about |
|---|---|
| 10 (a smaller city's RTOs) | 105 |
| 25 | 260 |
| 60 (this Bengaluru pilot) | 628 |
| 100 | 1,050 |

SerpApi's free plan (250 searches a month) covers about 23 offices a month. To add a city:

1. Add it to `CITIES` in `kalaana/offices.py`: its Google Maps centre, its Google Search `location` and its STD code (no credits).
2. Write its offices from the department's own directory into `data/official/`, as in [Adding an office type](add-an-office-type.md), step 1 (no credits).
3. Price the run, then run it within a budget: `kalaana collect rto --city <City> --plan`, then the same with `--budget`, followed by `citizen` and `crosscheck`.
4. `kalaana snapshot`, and the report card, office pages, chat and MCP server read it. (The web app shows one city at a time, set by `CITY` in `kalaana/views.py`.)

The time limits carry over within Karnataka, where the Sakala Act covers every office in the state, and the passport Citizen's Charter is national. Another state needs its own Right to Services schedule, written into `data/official/` with its source.

## All of India

The same 10.5 searches per office, measured on the Bengaluru pilot, price a national sweep. Of the pilot's 628 searches, 342 were Google Maps Reviews, the bulk of the cost. India has, approximately, 1,500 RTOs and district transport offices, 5,000 to 6,000 sub-registrar offices and 550 passport offices (regional offices, PSKs and Post Office PSKs). These counts are rough estimates, not a census.

| Scope | Offices, approximately | Searches, about | Cost, roughly |
|---|---|---|---|
| All three office types, all of India | 7,000 to 8,000 | 80,000 | $1,000 ($800 to $1,300) |
| RTOs and passport offices only | 2,000 | 21,000 | $250 to $350 |

Costs assume SerpApi's published paid plans at the time of writing, which work out to roughly one to one and a half US cents per search at volume; check current prices before relying on them. Reading fewer reviews per office could cut a sweep roughly in half.

The searches are not the hard part. Each state's official office directories and its Right to Services time limits have to be found, written into `data/official/` with their sources, and the findings checked. Some states don't publish office phone numbers, so the phone checks can't run there.
