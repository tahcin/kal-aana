import { motion, useReducedMotion } from "motion/react";
import { isRouteErrorResponse, useRouteError } from "react-router";
import { Wordmark } from "./Shell";

/**
 * The token you get at a public office counter, stamped. Decorative: it illustrates the joke in the name
 * ("kal aana", come back tomorrow) on the pages that have nothing else to show.
 */
export function TokenTicket({ token, stamp }: { token: string; stamp: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.svg viewBox="0 0 380 240" className="w-full max-w-[420px] overflow-visible drop-shadow-[0_30px_40px_rgb(40_22_80/0.22)]" aria-hidden
      animate={reduce ? undefined : { y: [0, -8, 0], rotate: [-3, -1.5, -3] }} transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }} style={{ rotate: -3 }}>
      <defs>
        <linearGradient id="ticket-fill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--color-brand)" /><stop offset="1" stopColor="var(--color-brand-2)" />
        </linearGradient>
      </defs>
      {/* Ticket body with a notch on each side, like the logo. */}
      <path d="M24 20h332a14 14 0 0 1 14 14v58a28 28 0 0 0 0 56v58a14 14 0 0 1-14 14H24a14 14 0 0 1-14-14v-58a28 28 0 0 0 0-56V34a14 14 0 0 1 14-14Z" fill="url(#ticket-fill)" />
      <line x1="262" y1="34" x2="262" y2="206" stroke="var(--color-paper)" strokeOpacity="0.45" strokeWidth="2" strokeDasharray="2 7" strokeLinecap="round" />
      <text x="44" y="68" className="fill-paper/75 text-[13px] font-semibold uppercase tracking-[0.22em]">Token no.</text>
      <text x="40" y="160" className="fill-paper font-serif text-[96px] tracking-[-0.04em]">{token}</text>
      <text x="44" y="190" className="fill-paper/70 text-[12px] tracking-[0.06em]">Please wait for your turn</text>
      {/* The stub: a counter clock whose minute hand keeps going round. */}
      <circle cx="316" cy="120" r="30" fill="none" stroke="var(--color-paper)" strokeWidth="3" />
      <line x1="316" y1="120" x2="330" y2="128" stroke="var(--color-paper)" strokeWidth="3" strokeLinecap="round" />
      <motion.line x1="316" y1="120" x2="316" y2="98" stroke="var(--color-pop)" strokeWidth="3" strokeLinecap="round" style={{ transformOrigin: "316px 120px" }}
        animate={reduce ? undefined : { rotate: 360 }} transition={{ duration: 8, repeat: Infinity, ease: "linear" }} />
      <circle cx="316" cy="120" r="3.5" fill="var(--color-pop)" />
      {/* The stamp lands with a thunk. */}
      <motion.g initial={reduce ? false : { opacity: 0, scale: 1.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.7, type: "spring", stiffness: 500, damping: 22 }}
        style={{ transformOrigin: "250px 205px" }}>
        <g transform="rotate(-9 250 205)">
          <rect x="128" y="182" width="244" height="46" rx="10" fill="var(--color-paper)" stroke="var(--color-pop)" strokeWidth="3" />
          <text x="250" y="211" textAnchor="middle" className="fill-ink text-[14px] font-bold uppercase tracking-[0.16em]">{stamp}</text>
        </g>
      </motion.g>
    </motion.svg>
  );
}

/** Shown when a page throws while rendering, so the app never goes blank. A plain link (a full reload) is the surest way back. */
export default function ErrorPage() {
  const error = useRouteError();
  const detail = isRouteErrorResponse(error) ? `${error.status} ${error.statusText}` : error instanceof Error ? error.message : "";
  return (
    <div className="min-h-dvh bg-paper text-ink">
      <header>
        <div className="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-6">
          <a href="/" className="flex items-center gap-2.5" aria-label="Kal Aana home">
            <Wordmark className="h-8 text-ink" />
          </a>
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl items-center gap-14 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <div>
          <h1 className="headline text-[clamp(2.6rem,6vw,4.75rem)] leading-[0.98] tracking-[-0.035em]">This page didn't load. Come back to the story.</h1>
          <p className="mt-6 max-w-[46ch] text-lg leading-relaxed text-ink-2">Reloading usually clears this. The saved data is unaffected.</p>
          <p className="mt-9 flex flex-wrap gap-3">
            <a href="/" className="inline-flex rounded-full bg-brand px-5 py-3 font-semibold text-paper shadow-[var(--shadow-soft)] transition hover:brightness-110">Back to the story</a>
            <a href="/offices" className="inline-flex rounded-full border border-rule bg-card px-5 py-3 font-semibold transition hover:border-ink-2">Every office</a>
          </p>
          {detail && <p className="mt-10 break-words font-mono text-xs text-muted">{detail}</p>}
        </div>
        <div className="flex justify-center px-2 lg:justify-end"><TokenTicket token="!" stamp="Out of order" /></div>
      </main>
    </div>
  );
}
