# Kal Aana

[![Kal Aana's home page: "Namaskara, Bengaluru." over a soft lilac panel where published office landlines drift and a rotary dial turns; a marigold glow settles round the ask box after the call goes unanswered](docs/hero.png)](https://kalaana.gradestone.in)

**"Kal aana": come back tomorrow.** Every Indian has heard it at a government counter.

**Only 2 of 58 Google Maps listings for Bengaluru's public offices show the phone number the department publishes; 41 show no phone at all. Google's AI Overview didn't lead with the office's own number in 40 of 47 answers.** We measured this with 628 SerpApi searches across six engines, checking each office's official promises (its phone numbers, and the working days the law gives it for each service) against what citizens find on Google and report in reviews.

Kal Aana turns that evidence into help: ask it about your own application and it counts your working days against the legal limit, gives the office's own number, shows what Google told you instead, and drafts the complaint letter. For anything the saved data doesn't cover, it runs a live search of government sites. It covers the 13 RTOs, 43 sub-registrar offices and 4 passport offices that serve Bengaluru, and [a new office type takes five steps](docs/add-an-office-type.md). The same tools are an MCP server for AI assistants.

Built for the SerpApi India Hackathon 2026 (Knowledge & Public Interest track).

**Live:** [kalaana.gradestone.in](https://kalaana.gradestone.in). **MCP server, nothing to install:** `https://kalaana-mcp.gradestone.in/mcp` (see [AI assistants (MCP)](#ai-assistants-mcp)).

**Try it in 60 seconds** (Python 3.11+, no API key, no Node):

```bash
git clone https://github.com/tahcin/kal-aana && cd kal-aana
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e . && kalaana serve                      # then open http://127.0.0.1:8000
```

Without keys, the chat answers from the saved data, labelled "Answered from Kal Aana's saved data (no AI model)"; with a model key (any OpenAI-compatible API, such as Claude, OpenAI or Gemini, or a local Ollama), the model writes the answers, and with a SerpApi key it can search live. See [Choosing a reader](#choosing-a-reader).

![Asking Kal Aana on the live site: "Applied for my learner's licence at RTO South 3 weeks ago, still waiting". Claude Sonnet 5.5 picks the tools; the cards come from the data: 17 working days against a 7-day limit, and a reviewer's "20days" at the same office](docs/chat-answer.png)

## Why

I passed my learner's licence test at RTO Bengaluru South (KA-05). The approval didn't come, and the official numbers I tried didn't work. Karnataka's Sakala Act gives that office **7 working days** to issue a learner's licence.

This isn't one office. Indian public offices publish service promises: statutory time limits under Right to Services laws (in Karnataka, the Sakala Services Act), phone numbers and grievance officers. What citizens actually experience is scattered across thousands of Google Maps reviews. Nobody measures the promise against the reality, office by office. Surveys are national and periodic, and grievance portals only see complaints people bother to file.

Kal Aana uses search data as a measuring instrument: many searches across offices and sources, each checked against the official record.

## What it found (Bengaluru, October 8, 2026)

### RTOs: all 13 that serve Bengaluru

- **The government publishes a landline for all 13. On Google Maps, 9 of the 12 RTO listings show no phone number at all**, and 11 of 12 are marked unclaimed (no verified owner manages them). KA-59 Chandapura has no listing of its own that our searches found.
- **Google's AI Overview did not lead with the office's own number in 4 of the 9 searches where it answered. Asked the same question, Google's AI Mode led with the office's own number in all 13**, with the right PIN wherever it gave one: Google has the number, but the answer on the normal results page doesn't always show it. For KA-41 (Jnanabharathi) none of its numbers is KA-41's, and one is the Devanahalli office's landline. For KA-57 it says a direct landline is "typically unlisted"; the department publishes two. For KA-01 and KA-05 it gives an address with a different PIN from the official one.
![What Google's AI told citizens about the Jayanagar sub-registrar office: both numbers in the AI Overview, and the one AI Mode leads with, are not in the department's directory](docs/chat-ai.png)

- **Bing Maps shows the same gap.** Of the 7 RTOs we could match on Bing, 5 show no phone; the 2 that do (KA-04 and KA-50) are the same 2 whose Google listings show the office's own number.
- **Reviewers report the phones going unanswered.** At KA-05: "their land line numbers is not working".
- **Possible statutory breaches, in reviewers' own words:** a learner's licence at KA-05 "20days also over" (Sakala allows 7 working days), and driving licence renewals at KA-03 ("nearly 4 weeks") and KA-04 ("over 45 days") against 10 working days. Each is one person's account, not a rate.

### Sub-registrar offices: all 43

![Varthuru sub-registrar office: the promise (the department's office mobile) against the reality (a different number on its Google Maps listing, which Google's AI Overview and AI Mode both lead with)](docs/office-varthur.png)

- **The Department of Stamps and Registration publishes a phone number for all 43 (one office mobile number each). On Google Maps, 30 of the 42 listings show no phone, and none of the 12 numbers that are shown is in the department's directory.** 41 of 42 are unclaimed. A citizen who finds the office on Google has no way to tell which number, if any, is the one the department stands behind.
- **One mobile number that isn't in the department's directory is the phone on two different offices' listings, Varthur and J P Nagar.** Searched for each office's number, Google's AI calls it "the official phone number" for Varthur and gives it for J P Nagar too. It is not in the directory.
- **Google showed an AI Overview for 35 of the 42 offices searched, and none led with a number from the directory.** 33 led with a number that isn't in it; 7 repeat the number on the office's Maps listing. **AI Mode did no better here**: 1 of 42 led with the directory number. The department lists one office mobile per office and no landlines, and Google's AI doesn't find those mobiles.
- **Bing Maps:** of the 35 offices matched on Bing, 26 show no phone and none shows a directory number.
- **Reviews tell a quieter story than the surveys.** In a LocalCircles survey (September 2026), 73% of families who paid a bribe to transfer a deceased relative's assets paid it at property registration or land offices ([source](https://www.moneylife.in/article/73-percentage-families-paying-bribes-at-property-registration-land-offices-to-transfer-deceased-relatives-assets-survey/81571.html)). In the newest reviews of all 42 listed offices (333 with text from the last year), 12 report a bribe and 22 report agents or brokers, while 71 praise the office. Gandhinagara's recent reviewers mostly praise it (11 of 18). Most bribe accounts found by searching reviews for "bribe" are older (2021 to 2023). Reviews can't say whether that is a real change, fewer people writing about it, or how Google ranks keyword matches, and the lexicon is untested on sub-registrar reviews.

### Passport offices: the RPO and its 3 Bengaluru centres

Passport offices are run by the Ministry of External Affairs, so their time limits come from its Citizen's Charter (counted from complete documentation; fresh passports leave out police verification), not the Sakala law.

- **None of the 4 Google Maps listings shows the office's own number.** Two show the national call centre (1800-258-1800), and two show no phone, though the RPO's site lists a phone for every centre (for Jalahalli, the RPO's own main line).
- **9 Google Maps listings in Bengaluru are named like a passport office ("Passport Seva Kendra", "PASSPORT OFFICE") but aren't among the 4 on the RPO's list.** Google itself files 5 of them as passport agents or internet cafes. Kal Aana shows them, without their phone numbers.
- **PSK Sai Arcade moved to Whitefield on October 5.** The new centre's listing exists but shows no phone. Asked for its number, both Google's AI Overview and AI Mode say the centre has no publicly listed number of its own and lead with the national helpline, while the RPO's site lists a landline for it (080 2563 9137).

Every claim links to its source: the department's directory, the Sakala Service Compendium page, the Google Maps listing, the review, or the SerpApi search ID. Reviews are self-selected, so the app says "reviewers report", shows sample sizes and date ranges, and says "too few reviews" below 10.

| Report card | Office page | Complaint letter in the chat |
|---|---|---|
| ![The RTO report card: 9 of 12 listings show no phone, then every office ranked by listing score](docs/offices.png) | ![KA-05's office page: the verdict in three sentences, then the promise against the reality](docs/office-ka05.png) | ![A complaint letter about a late passport re-issue, addressed to the RPO's grievance address](docs/chat-letter.png) |

## What you get

1. **Ask** (`/`): a chat for anything about RTO, passport and sub-registrar matters in Karnataka. Describe your problem in your own words ("applied for my learner's licence at RTO South 3 weeks ago, still waiting", "what documents do I need for a learner's licence?", "is Sarathi down today?") and the answer builds itself as cards: your working days against the limit, the office's own numbers set against what Google Maps and Bing show, what Google's AI told citizens (typed out, the office's own number in green, anything else in red), what reviewers report, a complaint letter addressed to the right officer (for a passport centre, the RPO's grievance address), and, for anything the saved data doesn't cover (documents, fees, procedures, tracking, outages), a **live SerpApi search**: Google restricted to government sites first, or Google News, each result linked and marked "Government site" or "Other site". Ask follow-ups. With a model reader, the model picks the tools and writes a few connecting sentences, naming the site for every fact from a search; **the cards come from the data, not the model** (the model only passes along the date and application number you gave), and a guard withholds any number in its words that no tool returned and any phone number you typed, so even a crafted message can't make Kal Aana vouch for a number. Without a key, Kal Aana's rules choose the same cards. Every reply says which reader answered. Passport limits come with the charter's terms, and a re-issue is only called past the limit "if no police verification was needed". A letter is offered only once an application is past its limit. Kal Aana keeps no record of the conversation (it stays in your browser tab); with a model reader, your messages are sent to that model's API to write the reply, and a live search sends a short query to SerpApi. Links: `/#ask=<question>` puts a question in the box for the visitor to send, and `/?office=<id>` asks about one office.
   The chat also answers in Hindi, Hinglish and Kannada (with a model; without one, the rules still read the office, service and date from Hindi or Kannada script), and for five RTOs it shows **when the office is usually less crowded**, from Google's typical busyness by hour in our saved searches (a weekday from 10 am to 4 pm; offices are closed on Sundays and the 2nd and 4th Saturdays). The home page opens on "the unanswered call": published 080 office landlines from the departments' directories float around the headline, one is dialled and rings, and a marigold light carries to the ask box.
   ![A live search: "What documents do I need for a learner's licence in Karnataka?" Google results from government sites only, each marked "Government site", with the search ID; the answer names the site for each fact](docs/chat-search.png)
2. **The map** (`/map`): every office on a vector map of Bengaluru, coloured by what its Google Maps listing shows, with the one number shared by two offices drawn as an arc. A "Lookalikes" filter adds the 9 listings named like a passport office but not on the RPO's list, as hollow rings (shown without their phone numbers). Selecting an office opens a card with what Google Maps, the AI Overview, AI Mode and Bing Maps each show for it.
3. **Report cards** (`/offices`): every office of a type, sortable by listing score or reported problems: the official number, what Maps shows, what Google's AI leads with, and how many recent reviews report a problem.
4. **Office pages** (`/office/rto-ka05`): the verdict in plain sentences, a "promise" panel (the published numbers and time limit) against a "reality" panel (what Google Maps, the AI Overview, AI Mode, Bing Maps and recent reviews show), and the evidence: what the AI Overview, AI Mode and Bing Maps each show, every number Google showed, six checks of the listing, quotes by issue, and every SerpApi search behind the page. They also give where to escalate (the Sakala appeal officers, or for passports the grievance channels), the department's own notes on the office, and any lookalike listings nearby.
5. **The method** (`/method`): a diagram of the pipeline, each step explained, and the classifier's accuracy computed live from the labelled reviews.
6. **MCP server** for AI assistants, with the chat's own tools: `how_to_reach`, `office_report`, `compare_offices`, `statutory_timeline`, `read_a_complaint`, `check_wait`, `google_ai_answers`, `office_reviews`, `draft_complaint`, `best_time_to_visit`, and the two live searches, `search_official_sites` and `search_news` (marked open-world; they need a SerpApi key and share the chat's rationed allowance). So an assistant asked "how do I contact RTO South?" answers with the official number and the evidence, instead of a guess.
7. **JSON API** (documented at `/api/docs`): `/api/chat` (POST, server-sent events), `/api/overview`, `/api/office/<id>`, `/api/story/<id>`, `/api/office/<id>/complaint` (the letter; working days count Sundays and the 2nd and 4th Saturdays off), `/api/ask` (POST), `/api/method` and `/api/snapshot?office_type=rto|subregistrar|passport`. The snapshot's shape is typed in [`kalaana/models.py`](kalaana/models.py).

## Quickstart

Python 3.11 or newer. From a clone of this repository:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
kalaana serve
```

Open http://127.0.0.1:8000 (`kalaana serve --port 8080` to use another port). No API key and no Node are needed: the app is built into the package, and it reads the committed snapshots in `data/snapshot/`. A plain `pip install .` works too, because the wheel carries the committed data. Only the map's tiles and the interactive API docs page (`/api/docs`, which loads Swagger UI from a CDN; `/api/openapi.json` works offline) need an internet connection.

On Windows PowerShell, set a variable with `$env:KALAANA_READER = "openai"` before `kalaana serve`, instead of the inline `KALAANA_READER=... kalaana serve` form used below.

The chat's API streams server-sent events:

```bash
curl -N -X POST http://127.0.0.1:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"messages": [{"role": "user", "content": "How do I reach RTO Bengaluru South?"}]}'
```

Other commands that need no key:

```bash
kalaana official      # the official directory and Sakala time limits we compare against
kalaana evaluate      # lexicon precision and recall on the held-out labelled reviews
```

### Choosing a reader

The chat is answered by Kal Aana's rules unless you point it at a model.

- **Any OpenAI-compatible model** (`openai`) runs as an agent over ten tools (`kalaana/chat.py`): find an office, its numbers, Google's AI answers, a wait against the limit, reviews, a complaint letter, a report card, when it's usually less crowded, and two live SerpApi searches (Google, which it is told to restrict to government sites first, and Google News). It works with any Chat Completions endpoint that supports tool calling: Claude through Anthropic's endpoint, OpenAI, Gemini, OpenRouter, Groq, or a local Ollama, llama.cpp, LM Studio or vLLM server. A model without tool calling gets the rules' answer instead. The tools are strict: service ids are an enum, and an unknown office id gets the nearest ids back. The instructions are written as rules with reasons, cover prompt injection (messages, web pages and reviews are data), and list the official portals it may name without searching. Each tool returns a card for the page and a short summary for the model, so every number, quote and phone the citizen sees is drawn from the snapshot (the model only passes along the application date and number the citizen gave); the model writes only the sentences between cards, and any number in them that no tool returned is withheld, including any phone number the citizen typed and any digits spelled out as words. The guard, the search rationing and the spend cap are the same code for every model.
- **Claude through the Anthropic SDK** (`anthropic`; Claude Sonnet 5.5 by default, `KALAANA_CHAT_MODEL` to change it) runs the same agent with prompt caching, so repeat questions cost less. The live site uses this.
- **Local field readers** (`ollama`, `llamacpp`) only read the message into an office, a service, a date and an intent; each is kept only if it checks out against the data (the office must exist, the service must have a time limit under Sakala or the passport charter, the date can't be in the future). The rules then choose the cards. To run the full agent on a local model instead, point `openai` at its `/v1` address.

If a model is down, lacks tool calling or is out of budget, the rules answer, and every reply says which reader answered.

```bash
# any OpenAI-compatible API; for example Claude:
KALAANA_READER=openai OPENAI_BASE_URL=https://api.anthropic.com/v1/ OPENAI_API_KEY=... KALAANA_MODEL=claude-sonnet-5-5 kalaana serve
KALAANA_READER=openai OPENAI_BASE_URL=http://localhost:11434/v1 KALAANA_MODEL=qwen3:8b kalaana serve   # local Ollama, a model with tools
pip install -e ".[claude]" && KALAANA_READER=anthropic ANTHROPIC_API_KEY=... kalaana serve       # Claude via the SDK, with prompt caching
KALAANA_READER=ollama KALAANA_MODEL=gemma3:4b kalaana serve                     # local field reader only
KALAANA_READER=llamacpp LLAMACPP_URL=http://localhost:8080 kalaana serve          # local field reader, a llama.cpp server
```

With any model reader, each visitor gets 20 questions per 10 minutes, and `KALAANA_DAILY_QUESTIONS` can cap the questions a day across all visitors (IST; off by default). A cloud model's total spend is estimated in `data/private/ask-spend.json` (gitignored), from the token usage the API reports, with any model not on Kal Aana's price list charged at the top of the range; once it reaches `KALAANA_ASK_BUDGET_USD` (default 10), the chat falls back to rules, so a public demo can't run up the key's bill. A model on localhost is free and isn't counted. A typical answer takes two to four model calls; with prompt caching it cost us about 2.6 US cents with Sonnet 5.5 (so $10 is roughly 380 answers), or under a fifth of a cent with `KALAANA_CHAT_MODEL=claude-haiku-5-5`, which follows the honesty rules less reliably. Through Anthropic's OpenAI-compatible endpoint there is no prompt caching, so the same answer costs more (about 4 US cents for a two-call answer in one measured case).

Live searches are rationed separately, because each costs a SerpApi credit. Saved data comes first: a web search about anything the snapshot covers (phones, time limits, Sakala, reviews, bribes, agents, busy hours, timings, the address) is refused before it runs, in the chat and the MCP server, and the model is pointed to the saved-data tool instead (`chat.saved_data_covers`). The model is told to make one search per reply and a second only if the first found nothing (the code stops at two). A repeat within the hour (same words, ignoring case and spacing) is served from the cache and costs no credit and no allowance (`live.is_cached`). Each visitor gets 5 live searches per 10 minutes; in all, `KALAANA_LIVE_TOTAL` (default 300), `KALAANA_LIVE_DAILY` a day (default 40, IST), and none once the account has `KALAANA_LIVE_RESERVE` credits or fewer left (default 250, read from SerpApi's free Account API), so the credits kept for refreshing the dataset are never touched. Counts are kept in `data/private/live-searches.json` (gitignored). Without a SerpApi key, live search is off and the chat says so.

Earlier replies in a conversation come back from the visitor's browser (the last 12 turns), and each is cut to about 600 characters on a sentence end and marked "[Shortened here to save space]", so the model never mistakes the trim for a reply that broke off.

### Live data (needs a SerpApi key)

```bash
pip install -e ".[live]"
cp .env.example .env              # then paste your key into SERPAPI_API_KEY
kalaana collect rto --plan        # how many fresh searches a run would cost; spends nothing
kalaana collect rto --budget 100  # Maps listings and reviews, every response cached on disk
kalaana citizen rto --budget 30   # Google Search, AI Overview and AI Mode for each office
kalaana crosscheck rto --budget 15 # the same offices on Bing Maps
kalaana report rto                # the report card in the terminal
kalaana snapshot rto              # rebuild data/snapshot/ for the web app and MCP server
```

For an office type with many offices, `--targeted N`, `--sample-offices N` (collect) and `--offices N` (citizen) keep a sweep inside a budget (without them, a sub-registrar sweep plans at least 97 more searches on top of the cached ones), as in [adding an office type](docs/add-an-office-type.md). Offices left out say "not sampled" or "not checked", never "no problems".

A run never spends more than `--budget` fresh searches (or `KALAANA_SEARCH_BUDGET` in `.env`). Cached responses are free, so a re-run costs nothing. Raw responses are kept in `data/cache/` and full collections in `data/collected/`; both are gitignored because they hold unmasked review text.

### AI assistants (MCP)

**Hosted, nothing to install.** The server runs at `https://kalaana-mcp.gradestone.in/mcp` (Streamable HTTP, no sign-in):

- Claude (claude.ai or Claude Desktop): Settings, Connectors, Add custom connector, and paste the URL.
- Claude Code: `claude mcp add --transport http kal-aana https://kalaana-mcp.gradestone.in/mcp`
- Any other client that speaks Streamable HTTP: the same URL.

The hosted server's two live-search tools share the public site's rationed allowance; the other ten answer from the saved snapshot.

**Run it yourself** (stdio, the way Claude Desktop launches local servers):

```bash
pip install -e ".[mcp]"
```

Add this to `claude_desktop_config.json` (Settings, Developer, Edit Config), with the full path to the `kalaana-mcp` program in your virtual environment (on Windows, `.venv\Scripts\kalaana-mcp.exe`):

```json
{
  "mcpServers": {
    "kal-aana": {
      "command": "/full/path/to/your/clone/.venv/bin/kalaana-mcp"
    }
  }
}
```

Restart Claude Desktop and ask "How do I reach RTO Bengaluru South?" or "What's the time limit for an encumbrance certificate?". The tools are read-only; ten of the twelve work offline from the snapshot (the two live searches need `SERPAPI_API_KEY` in the server's environment), and they refuse to guess: "Koramangala RTO" is a neighbourhood, not an office, so the tool asks which office you mean instead of returning the wrong office's number. "Yelahanka" has both an RTO and a sub-registrar office, so it asks which. [`docs/mcp-example.md`](docs/mcp-example.md) shows real output from the server.

To host it, `kalaana-mcp --http 127.0.0.1:8096` serves Streamable HTTP at `/mcp`; behind a proxy, list its public host names in `KALAANA_MCP_HOSTS` so requests for any other host are refused.

### Changing the app

The app's source is in `frontend/`. With Node and pnpm:

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:5173, with /api proxied to `kalaana serve` on port 8000
pnpm build      # writes kalaana/static/app/, which is committed
```

### Hosting (the live site)

- **Pages:** [kalaana.gradestone.in](https://kalaana.gradestone.in) is the same React build, served from Cloudflare Workers static assets (`frontend/wrangler.jsonc`). Hashed files in `/assets/` are cached for a year (`frontend/public/_headers`; `kalaana serve` sends the same header). A small worker in front of `/api/*` only (`frontend/worker.js`) keeps the snapshot's read-only data (`/api/overview`, `/api/method`, `/api/snapshot`, `/api/office/<id>`, `/api/story/<id>`) in Cloudflare's cache near the visitor for an hour; anything that depends on today or the visitor (an application date, the chat, a letter) goes straight to the API.
- **API and MCP:** `kalaana serve` at `https://kalaana-api.gradestone.in` and `kalaana-mcp --http` at `https://kalaana-mcp.gradestone.in/mcp`, on a small VPS behind a Cloudflare Tunnel, each a systemd service with memory and CPU limits, listening only on 127.0.0.1.
- **Redeploy the pages:** from `frontend/`, `VITE_API_BASE=https://kalaana-api.gradestone.in VITE_OUT_DIR=dist pnpm build && npx wrangler deploy`. `VITE_API_BASE` points the pages at the API; `VITE_OUT_DIR` builds into `dist/` instead of the package.
- **Redeploy the API:** copy the code to the server and restart both services.

The server's settings, in its `.env`:

| Variable | What it does |
|---|---|
| `KALAANA_PROXY=cloudflare` | Read the visitor's address from Cloudflare's `CF-Connecting-IP` header, so the per-visitor limits work behind the tunnel (trust it only when the server is reachable through the tunnel alone) |
| `KALAANA_CORS` | Comma-separated origins allowed to call the API from a browser (the pages' own origins); off by default |
| `KALAANA_DAILY_QUESTIONS` | Questions a day across all visitors, when a model answers |
| `KALAANA_ASK_BUDGET_USD` | A cloud model's total spend before the chat falls back to the rules |
| `KALAANA_LIVE_DAILY`, `KALAANA_LIVE_TOTAL`, `KALAANA_LIVE_RESERVE` | The live-search allowance (see [Choosing a reader](#choosing-a-reader)) |
| `KALAANA_MCP_HOSTS` | The MCP server's public host names; requests for any other host are refused |
| `KALAANA_READER`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `KALAANA_MODEL`, `KALAANA_CHAT_MODEL`, `ANTHROPIC_API_KEY`, `SERPAPI_API_KEY` | The reader, its endpoint and model, and the keys |

### Tests

```bash
pip install -e ".[dev]"
pytest          # 648 passed on October 9, 2026
```

The tests use fixtures shaped like SerpApi's JSON, never real calls. The real `SearchClient` runs, with its cache, budget, dry run and key redaction, and only the HTTP call is stubbed.

## How it uses SerpApi

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

Choices that save credits:

- **No place-details calls.** The Maps search result already has the phone, hours and `unclaimed_listing`. For KA-05 it matched the place-details call field for field, which saves one credit per office.
- **Adaptive review paging.** We read newest-first pages until an office has 15 reviews with text (at most 4 pages), because about two in three recent reviews are stars only.
- **Keyword pages are skipped** when the newest-first pages already returned every review the listing has.
- **`--plan`** counts the fresh searches a run would make before it spends anything.

### Credits per run

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

### Another city

Nothing in the audit is tied to Bengaluru, and it costs about **10.5 searches per office** (628 for 60 offices):

| Offices audited | Searches, about |
|---|---|
| 10 (a smaller city's RTOs) | 105 |
| 25 | 260 |
| 60 (this Bengaluru pilot) | 628 |
| 100 | 1,050 |

SerpApi's free plan (250 searches a month) covers about 23 offices a month. To add a city:

1. Add it to `CITIES` in `kalaana/offices.py`: its Google Maps centre, its Google Search `location` and its STD code (no credits).
2. Write its offices from the department's own directory into `data/official/`, as in [Adding an office type](docs/add-an-office-type.md), step 1 (no credits).
3. Price the run, then run it within a budget: `kalaana collect rto --city <City> --plan`, then the same with `--budget`, followed by `citizen` and `crosscheck`.
4. `kalaana snapshot`, and the report card, office pages, chat and MCP server read it. (The web app shows one city at a time, set by `CITY` in `kalaana/views.py`.)

The time limits carry over within Karnataka, where the Sakala Act covers every office in the state, and the passport Citizen's Charter is national. Another state needs its own Right to Services schedule, written into `data/official/` with its source.

### All of India

The same 10.5 searches per office, measured on the Bengaluru pilot, price a national sweep. Of the pilot's 628 searches, 342 were Google Maps Reviews, the bulk of the cost. India has, approximately, 1,500 RTOs and district transport offices, 5,000 to 6,000 sub-registrar offices and 550 passport offices (regional offices, PSKs and Post Office PSKs). These counts are rough estimates, not a census.

| Scope | Offices, approximately | Searches, about | Cost, roughly |
|---|---|---|---|
| All three office types, all of India | 7,000 to 8,000 | 80,000 | $1,000 ($800 to $1,300) |
| RTOs and passport offices only | 2,000 | 21,000 | $250 to $350 |

Costs assume SerpApi's published paid plans at the time of writing, which work out to roughly one to one and a half US cents per search at volume; check current prices before relying on them. Reading fewer reviews per office could cut a sweep roughly in half.

The searches are not the hard part. Each state's official office directories and its Right to Services time limits have to be found, written into `data/official/` with their sources, and the findings checked. Some states don't publish office phone numbers, so the phone checks can't run there.

## How it works

```mermaid
flowchart LR
  O[data/official/*.toml<br>directory, Sakala timelines,<br>every row with a source URL] --> M
  S[SerpApi<br>Maps, Reviews, Search,<br>AI Overview, AI Mode, Bing Maps] --> C[client.py<br>cache, budget,<br>key redaction]
  C --> M[collect.py + offices.py<br>sweep, match listings<br>to official offices]
  C --> Z[citizen.py<br>Search and AI Overview<br>vs the directory]
  M --> T[taxonomy.py<br>9 issue categories,<br>7 languages and scripts]
  T --> R[score.py<br>listing score, counts,<br>possible breaches]
  R --> N[snapshot.py<br>masked quotes only]
  Z --> N
  N --> V[views.py + web.py<br>JSON API, complaint letters]
  V --> H[chat.py<br>a model over ten tools<br>(any OpenAI-compatible API),<br>or the rules; cards from data]
  S --> L[live.py<br>rationed live search:<br>gov sites first, news]
  L --> H
  H --> F[frontend/<br>React app: chat, map,<br>offices, method]
  V --> F
  V -.-> W[frontend/worker.js<br>live site only: edge cache<br>for read-only API data]
  W -.-> F
  N --> P[mcp_server.py<br>12 read-only tools]
  N --> Q[ask.py + reader.py<br>free text to office,<br>service, date; optional model]
```

- **Official ground truth** (`data/official/`): the Karnataka Transport Department's RTO directory (landlines, official mobiles, email), the Sakala Service Compendium of May 5, 2026 (each time limit cites its PDF page), the appeal path, the national Parivahan helpdesk, the Department of Stamps and Registration's sub-registrar directory, and the passport offices for the next office type. The loader is strict: a row without a source is an error.
- **Matching** (`offices.py`): a Maps listing counts as an office only if its category fits and it matches on a phone number, the office code or the location. Agents named "RTO Services" next door are kept separate and never treated as the office.
- **Issue lexicon** (`taxonomy.py`): nine categories (can't reach by phone, bribe, agents or brokers, delay, staff, portal, closed or wrong hours, queues, helpful) across English, Kannada, Hindi, Tamil, Telugu and romanised Kannada and Hindi. It handles denials ("didn't have to pay any bribe"), denials that are really claims ("without bribe nothing moves"), hypotheticals, warnings and 1-star sarcasm. Every hit carries the exact words it matched, which become the highlighted evidence.
- **Listing score** (`score.py`): 0 to 100 from six named checks of the Maps listing: a phone shown (25), the number is the office's own (20), a government website (10), opening hours (10), managed by its owner (10), and no recent review reporting failure to get through (25). Checks that can't be decided are left out, and the basis is shown ("5 of 6 checks"). It measures what citizens find on Google, not how good the office is.
- **Possible statutory breach**: a review from the last 2 years reporting a wait at least 25% past the Sakala time limit for a service named in the same sentence. Waits that went through an agent are set aside, and promised durations ("will take 30 days") are ignored.

## Evaluation

Two sets of real reviews were labelled by hand, blind to the lexicon's output: a development set of 100 (used for tuning) and a held-out set of 60, labelled after tuning and scored once. Details and per-category figures are in [`data/labels/README.md`](data/labels/README.md).

| On the held-out set | Precision | Recall |
|---|---|---|
| Phrase lexicon (used for every count) | **95%** (55 of 58 flags right) | **74%** (55 of 74 reports found) |
| gemma3:4b, a local LLM via Ollama | 71% | 62% |
| Lexicon or gemma3:4b | 76% | 88% |

When the lexicon says a review reports a problem, it is almost always right, so the counts aren't inflated. It misses about a quarter of reports, so they are, if anything, an undercount.

**A local LLM, tested and not used.** We ran gemma3:4b locally on an 8 GB M1 Mac (`kalaana refine`): temperature 0, output forced into a JSON schema of the nine categories, the review passed as delimited data, and every label required to come with a quote that appears verbatim in the review (labels whose quote wasn't there were rejected). It labels by topic rather than by what happened ("staff were polite" becomes a staff complaint), so it adds false reports. Because every count is a claim about a named office, precision wins and the lexicon stays. The model's cached readings are in `data/refined/`, so `kalaana evaluate --model gemma3:4b` reproduces the table without Ollama.

Some categories have only a handful of labelled examples (one each for "can't reach by phone" and "portal"), so their individual figures mean little. The labels are one labeller's reading (Claude's, see below), and borderline calls are marked `ambiguous` in the files and left out of the scores.

### The chat's honesty, tested

The chat's model-written sentences are the part most likely to slip, so they are tested too. `kalaana chat-eval` sends 23 tricky conversations through the configured reader and checks every reply with plain code, no model judging a model: a number not in the directory is never called wrong or fake, nobody claims a number works, no one is named, a planted phone number is never repeated, a passport wait comes with its police-verification condition, the reply comes back in the citizen's language (Hindi, Hinglish and Kannada are in the set), out-of-scope questions say what Kal Aana covers, a vague question gets a question back, no letter is drafted for an application still within its limit, no web address appears that a tool didn't return, a Saturday visit is never suggested without the 2nd and 4th Saturday closures, and no number had to be withheld. With Claude Sonnet 5.5 on October 9, 2026: **23 of 23 passed**. Through Anthropic's OpenAI-compatible endpoint, the same model also passed 23 of 23 ([`docs/chat-eval-openai-compatible.md`](docs/chat-eval-openai-compatible.md)). Every answer is in [`docs/chat-eval.md`](docs/chat-eval.md), so you can check the checks. Getting there caught real slips, now fixed: an eligibility rule stated from memory, and a Saturday suggested when that Saturday was a closed one.

## Limitations

- **Reviews are self-selected.** People with a bad experience write more of them. Counts are shown with their denominator and date range, never as a rate for the office.
- **Samples are small.** Google's newest-first paging stops after about 25 reviews on some listings. 8 of 13 RTOs and 15 of 42 sub-registrar listings have 10 or more recent reviews with text; the rest say "too few reviews".
- **The lexicon was measured on RTO reviews only.** Its 95% precision comes from hand-labelled RTO reviews; on sub-registrar reviews it is untested, so treat those counts as indicative.
- **AI answers change** with the query and the day. The AI Overviews and AI Mode answers shown are what Google returned on October 8, 2026, for the exact query shown, with the search ID.
- **Bing matching is by location.** A Bing place counts as the office only within 400 m of its Google listing (or by name when Google has none), so offices we couldn't match say so rather than "no listing".
- **Matching can miss duplicates.** "People also search for" panels show listings our sweep didn't return. KA-59 and the BDA sub-registrar office weren't found at all, which is not proof they have no listing. Some matches rest on location alone (the same PIN or place name); the office card says so.
- **Directories go out of date.** The sub-registrar directory lists one office mobile number per office, which can change when officers move. "Not in the directory" means exactly that, not that a number is wrong.
- **Name masking is pattern-based.** It catches names next to a cue (Mr, officer, madam, "named", "kudos to"). Every committed quote was also read in full by a separate AI reviewer (Claude, in a fresh session) looking for names and identifiers. Names found that way are masked through a local list that is never committed, because a list of names is exactly what must not be published.
- **Facilities complaints** (cleanliness, parking, washrooms) aren't counted, because no statutory promise covers them.
- **Tamil and Telugu** patterns are tested but unmeasured on real text: in our RTO collection (not committed), only 5 of the 438 reviews with text are in Indian scripts.
- **One city so far.** All three office types are Bengaluru's; another city needs its own directories and searches (see [Another city](#another-city)), and the web app shows one city at a time.

## Ethics

- **Offices, not individuals.** No staff member or private individual is named anywhere. (Businesses appear only by the names on their own Google listings, for example listings named like a passport office.) Names, mobile numbers that aren't in an official directory, vehicle registrations and agents' shop numbers are masked in every quote. Officers' official numbers stay visible because they are the published public contact points.
- **No reviewer identities.** No reviewer's name or profile is in any committed file or shown anywhere; the committed snapshot and labelled sets hold masked text only. (The raw search cache, which is never committed, holds SerpApi's responses as received.)
- **No record of conversations.** The chat keeps no record on the server; the conversation lives in the visitor's browser tab. With a model reader, messages go to that model's API, and a live search sends a short query to SerpApi; live results are cached for an hour, then deleted.
- **Careful wording.** "Reviewers report", "possible breach" and "listing score", never "this office is corrupt".
- **Nothing is sent on anyone's behalf.** The complaint letter is a draft the citizen reads, edits and sends.
- **Untrusted text stays data.** Review text never reaches a model as instructions, and the MCP tools label quotes as data.

## Project layout

```
kalaana/          the package: client, collect, offices, official, citizen, crosscheck, phones, taxonomy, redact,
                  score, snapshot, models, evaluate, refine, lookup, ask, reader, chat, chat_eval, live, views,
                  web, mcp_server, paths, cli
data/official/    official directories and Sakala time limits, every row with its source
data/snapshot/    the committed snapshots (one per office type) the web app and MCP server read
data/labels/      hand-labelled reviews for evaluation (masked)
data/refined/     the local LLM's cached readings (masked)
frontend/         the React app's source (React, TypeScript, Vite, Tailwind, Motion, MapLibre, deck.gl; the home
                  hero is plain WebGL2), plus worker.js and wrangler.jsonc for the live site
kalaana/static/app/  the app, built and committed so running it needs no Node
tests/            pytest suite
docs/             screenshots, an MCP transcript, the chat eval report, and how to add an office type
```

## Credits and AI use

- Data from [SerpApi](https://serpapi.com) (Google Maps, Google Maps Reviews, Google Search, Google AI Overview, Google AI Mode, Bing Maps), the Karnataka Transport Department, the Karnataka Department of Stamps and Registration, the Karnataka Sakala Services portal and the Ministry of External Affairs. Reviews are by members of the public on Google Maps; each quote links to the original.
- Built with **Claude Code** (Anthropic's Claude), which wrote most of the code, the tests and the documentation, researched the official sources, and hand-labelled the evaluation sets under the author's direction. **gemma3:4b** (Google, run locally with Ollama) was used only for the evaluation above.
- Libraries: FastAPI, Uvicorn, phonenumbers, python-dotenv, and optionally serpapi, the Anthropic SDK (for prompt caching; any OpenAI-compatible API needs no extra library) and the MCP Python SDK. The app: React, React Router, Vite, Tailwind CSS, Motion, MapLibre GL, deck.gl, cmdk, Radix UI and lucide icons (all MIT, ISC or similar permissive licences), the Inter, Newsreader and JetBrains Mono fonts, and the wordmark lettered from Shadows Into Light Two (Kimberly Geswein) and Hubballi (Kannada) (all SIL Open Font License 1.1). Map data &copy; OpenStreetMap contributors (ODbL), tiles by OpenFreeMap.

## Data and content notice

The snapshots in `data/snapshot/` are a dated research capture (October 8, 2026) made through SerpApi, for citizen information and public-interest research. Review quotes are short, masked excerpts that belong to their authors and Google, and each links to the original. Google's AI Overview and AI Mode text is shown as captured, with unverified mobile numbers, emails and listed names masked. Official contact details and time limits come from the departments' own published directories and the Sakala Service Compendium (May 5, 2026), retrieved October 8, 2026, with each source linked in `data/official/`. If you are named or quoted and want something removed, open an issue on this repository.

## Licence

MIT. See [LICENSE](LICENSE).
