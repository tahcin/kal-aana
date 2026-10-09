# Setup and running

How to run Kal Aana locally, choose the model that answers the chat, collect live data, connect AI assistants over MCP, change the app, host it and run the tests.

[Back to README](../README.md)

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

## Choosing a reader

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

### Question limits and spend cap

With any model reader, each visitor gets 20 questions per 10 minutes, and `KALAANA_DAILY_QUESTIONS` can cap the questions a day across all visitors (IST; off by default). A cloud model's total spend is estimated in `data/private/ask-spend.json` (gitignored), from the token usage the API reports, with any model not on Kal Aana's price list charged at the top of the range; once it reaches `KALAANA_ASK_BUDGET_USD` (default 10), the chat falls back to rules, so a public demo can't run up the key's bill. A model on localhost is free and isn't counted. A typical answer takes two to four model calls; with prompt caching it cost us about 2.6 US cents with Sonnet 5.5 (so $10 is roughly 380 answers), or under a fifth of a cent with `KALAANA_CHAT_MODEL=claude-haiku-5-5`, which follows the honesty rules less reliably. Through Anthropic's OpenAI-compatible endpoint there is no prompt caching, so the same answer costs more (about 4 US cents for a two-call answer in one measured case).

### Live search allowance

Live searches are rationed separately, because each costs a SerpApi credit. Saved data comes first: a web search about anything the snapshot covers (phones, time limits, Sakala, reviews, bribes, agents, busy hours, timings, the address) is refused before it runs, in the chat and the MCP server, and the model is pointed to the saved-data tool instead (`chat.saved_data_covers`). The model is told to make one search per reply and a second only if the first found nothing (the code stops at two). A repeat within the hour (same words, ignoring case and spacing) is served from the cache and costs no credit and no allowance (`live.is_cached`). Each visitor gets 5 live searches per 10 minutes; in all, `KALAANA_LIVE_TOTAL` (default 300), `KALAANA_LIVE_DAILY` a day (default 40, IST), and none once the account has `KALAANA_LIVE_RESERVE` credits or fewer left (default 250, read from SerpApi's free Account API), so the credits kept for refreshing the dataset are never touched. Counts are kept in `data/private/live-searches.json` (gitignored). Without a SerpApi key, live search is off and the chat says so.

### Conversation history

Earlier replies in a conversation come back from the visitor's browser (the last 12 turns), and each is cut to about 600 characters on a sentence end and marked "[Shortened here to save space]", so the model never mistakes the trim for a reply that broke off.

## Live data (needs a SerpApi key)

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

For an office type with many offices, `--targeted N`, `--sample-offices N` (collect) and `--offices N` (citizen) keep a sweep inside a budget (without them, a sub-registrar sweep plans at least 97 more searches on top of the cached ones), as in [adding an office type](add-an-office-type.md). Offices left out say "not sampled" or "not checked", never "no problems".

A run never spends more than `--budget` fresh searches (or `KALAANA_SEARCH_BUDGET` in `.env`). Cached responses are free, so a re-run costs nothing. Raw responses are kept in `data/cache/` and full collections in `data/collected/`; both are gitignored because they hold unmasked review text. What each run costs, and what another city or all of India would: [SerpApi usage](serpapi.md).

## AI assistants (MCP)

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

Restart Claude Desktop and ask "How do I reach RTO Bengaluru South?" or "What's the time limit for an encumbrance certificate?". The tools are read-only; ten of the twelve work offline from the snapshot (the two live searches need `SERPAPI_API_KEY` in the server's environment), and they refuse to guess: "Koramangala RTO" is a neighbourhood, not an office, so the tool asks which office you mean instead of returning the wrong office's number. "Yelahanka" has both an RTO and a sub-registrar office, so it asks which. [`docs/mcp-example.md`](mcp-example.md) shows real output from the server. The full tool list is in [What you get](features.md).

To host it, `kalaana-mcp --http 127.0.0.1:8096` serves Streamable HTTP at `/mcp`; behind a proxy, list its public host names in `KALAANA_MCP_HOSTS` so requests for any other host are refused.

## Changing the app

The app's source is in `frontend/`. With Node and pnpm:

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:5173, with /api proxied to `kalaana serve` on port 8000
pnpm build      # writes kalaana/static/app/, which is committed
```

## Hosting (the live site)

- **Pages:** [kalaana.gradestone.in](https://kalaana.gradestone.in) is the same React build, served from Cloudflare Workers static assets (`frontend/wrangler.jsonc`). Hashed files in `/assets/` are cached for a year (`frontend/public/_headers`; `kalaana serve` sends the same header). A small worker in front of `/api/*` only (`frontend/worker.js`) keeps the snapshot's read-only data (`/api/overview`, `/api/method`, `/api/snapshot`, `/api/office/<id>`, `/api/story/<id>`) in Cloudflare's cache near the visitor for an hour; anything that depends on today or the visitor (an application date, the chat, a letter) goes straight to the API.
- **API and MCP:** `kalaana serve` at `https://kalaana-api.gradestone.in` and `kalaana-mcp --http` at `https://kalaana-mcp.gradestone.in/mcp`, on a small VPS behind a Cloudflare Tunnel, each a systemd service with memory and CPU limits, listening only on 127.0.0.1.
- **Redeploy the pages:** from `frontend/`, `VITE_API_BASE=https://kalaana-api.gradestone.in VITE_OUT_DIR=dist pnpm build && npx wrangler deploy`. `VITE_API_BASE` points the pages at the API; `VITE_OUT_DIR` builds into `dist/` instead of the package.
- **Redeploy the API:** copy the code to the server and restart both services.

### Environment variables

The server's settings, in its `.env`:

| Variable | What it does |
|---|---|
| `KALAANA_PROXY=cloudflare` | Read the visitor's address from Cloudflare's `CF-Connecting-IP` header, so the per-visitor limits work behind the tunnel (trust it only when the server is reachable through the tunnel alone) |
| `KALAANA_CORS` | Comma-separated origins allowed to call the API from a browser (the pages' own origins); off by default |
| `KALAANA_DAILY_QUESTIONS` | Questions a day across all visitors, when a model answers |
| `KALAANA_ASK_BUDGET_USD` | A cloud model's total spend before the chat falls back to the rules |
| `KALAANA_LIVE_DAILY`, `KALAANA_LIVE_TOTAL`, `KALAANA_LIVE_RESERVE` | The live-search allowance (see [Live search allowance](#live-search-allowance)) |
| `KALAANA_MCP_HOSTS` | The MCP server's public host names; requests for any other host are refused |
| `KALAANA_READER`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `KALAANA_MODEL`, `KALAANA_CHAT_MODEL`, `ANTHROPIC_API_KEY`, `SERPAPI_API_KEY` | The reader, its endpoint and model, and the keys |

## Tests

```bash
pip install -e ".[dev]"
pytest          # 655 passed on October 9, 2026
```

The tests use fixtures shaped like SerpApi's JSON, never real calls. The real `SearchClient` runs, with its cache, budget, dry run and key redaction, and only the HTTP call is stubbed.
