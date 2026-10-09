// The edge in front of the pages on kal-aana.gradestone.in. Static files come straight from Cloudflare's asset store;
// only /api/* runs this. The snapshot's read-only data (overview, offices, method) is the same for every visitor until
// the next deploy, so it is served from Cloudflare's cache near the visitor instead of crossing to the VPS each time.
// Anything that depends on today or on the visitor (an application date, a complaint letter) is passed straight through.
const API = "https://kalaana-api.gradestone.in";
const CACHEABLE = /^\/api\/(overview|method|snapshot|office\/[\w-]+|story\/[\w-]+)$/;
// Part of every cache key: change it when a deploy changes the API's data, and the edge starts afresh at once.
const VERSION = "2026-10-09b";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const upstream = API + url.pathname + url.search;
    if (request.method !== "GET" || !CACHEABLE.test(url.pathname) || url.searchParams.has("applied")) {
      return fetch(new Request(upstream, request));
    }
    const key = new Request(`${url.origin}${url.pathname}?v=${VERSION}&${url.searchParams}`, { method: "GET" });
    const hit = await caches.default.match(key);
    if (hit) {
      const fromCache = new Response(hit.body, hit);
      fromCache.headers.set("X-Kalaana-Cache", "hit");
      return fromCache;
    }
    const origin = await fetch(upstream, { headers: { Accept: "application/json" } });
    const response = new Response(origin.body, origin);
    if (origin.ok) {
      // An hour at the edge, five minutes in the browser: a redeploy shows within the hour. The API's CORS "Vary:
      // Origin" doesn't apply here (same origin), and would stop the edge from storing it.
      response.headers.set("Cache-Control", "public, max-age=300, s-maxage=3600");
      response.headers.delete("Vary");
      response.headers.delete("Set-Cookie");
      ctx.waitUntil(caches.default.put(key, response.clone()));
    }
    response.headers.set("X-Kalaana-Cache", "miss");
    return response;
  },
};
