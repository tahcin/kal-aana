import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

// The app is built into the Python package and served by FastAPI at /, so running
// Kal Aana never needs Node. In development, `pnpm dev` proxies the API to `kalaana serve`.
/** Preload the two fonts every page opens with (Newsreader for headlines, Inter for text, Latin subsets), so the
 *  headline doesn't wait for the stylesheet to be parsed before its font starts downloading. */
function preloadFonts(): Plugin {
  return {
    name: "preload-fonts",
    transformIndexHtml: {
      order: "post",
      handler(_html, ctx) {
        const fonts = Object.keys(ctx.bundle ?? {}).filter((f) => /assets\/(newsreader-latin-opsz-normal|inter-latin-wght-normal)-[\w-]+\.woff2$/.test(f));
        return fonts.map((f) => ({ tag: "link", attrs: { rel: "preload", as: "font", type: "font/woff2", href: `/${f}`, crossorigin: "" }, injectTo: "head" as const }));
      },
    },
  };
}

export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss(), preloadFonts()],
  build: {
    // Into the Python package by default; a separate static host (Cloudflare) builds into dist/ instead.
    outDir: process.env.VITE_OUT_DIR ?? "../kalaana/static/app",
    emptyOutDir: true,
    chunkSizeWarningLimit: 2200,
    // The framework in its own files: they change far less often than the app, so a returning visitor keeps them
    // cached across redeploys and only fetches the app's own code again.
    rollupOptions: {
      output: {
        manualChunks: (id) => /node_modules\/(react|react-dom|scheduler)\//.test(id) ? "react"
          : /node_modules\/(motion|motion-dom|motion-utils|framer-motion)\//.test(id) ? "motion"
          : /node_modules\/react-router\//.test(id) ? "router" : undefined,
      },
    },
  },
  server: { proxy: { "/api": process.env.KALAANA_API ?? "http://127.0.0.1:8000" } },
});