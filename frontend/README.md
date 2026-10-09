# Kal Aana web app

The React app (TypeScript, Vite, Tailwind CSS). It is built into `../kalaana/static/app/`, which is committed, so running
Kal Aana needs no Node. To change it, see [Changing the app](../docs/setup.md#changing-the-app).

The live site (kalaana.gradestone.in) is the same build with `VITE_API_BASE` set to the hosted API and `VITE_OUT_DIR=dist`,
served from Cloudflare Workers static assets (`wrangler.jsonc`). `worker.js` runs in front of `/api/*` only and caches the
snapshot's read-only data at the edge; `public/_headers` lets browsers keep the hashed files in `/assets/` for a year. See
[Hosting](../docs/setup.md#hosting-the-live-site).
