// The headline finding, said big and plain: what Google Maps shows for each office, one square per office.
import { motion, useInView, useReducedMotion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useRef } from "react";
import { Link } from "react-router";
import { CountUp } from "../bits";
import type { MapsStatus, Overview } from "../../lib/api";
import { MAPS, cn } from "../../lib/ui";

// Best to worst, so the squares read left to right like a bar.
const ORDER: MapsStatus[] = ["official", "helpline", "other", "no_phone", "no_listing"];
const SQUARE: Record<MapsStatus, string> = {
  official: "bg-kept", helpline: "bg-amber/55", other: "bg-amber", no_phone: "bg-broken", no_listing: "bg-transparent ring-2 ring-inset ring-broken/70",
};
const ease = [0.16, 1, 0.3, 1] as const;

function Stat({ a, b, children }: { a: number; b: number; children: string }) {
  return (
    <div className="border-t border-rule pt-5">
      <p className="display text-[clamp(2.6rem,5vw,3.6rem)] tracking-[-0.03em]"><CountUp value={a} /> <span className="text-muted">of {b}</span></p>
      <p className="mt-2 max-w-xs text-[15px] leading-relaxed text-ink-2">{children}</p>
    </div>
  );
}

export function Finding({ overview }: { overview: Overview | null }) {
  const reduce = useReducedMotion();
  const grid = useRef<HTMLDivElement>(null);
  const shown = useInView(grid, { once: true, margin: "-15% 0px" });
  const t = overview?.totals;
  const offices = overview ? [...overview.offices].sort((x, y) => ORDER.indexOf(x.maps) - ORDER.indexOf(y.maps)) : [];
  const count = (s: MapsStatus) => offices.filter((o) => o.maps === s).length;
  const summary = ORDER.filter(count).map((s) => `${count(s)} ${MAPS[s].label.toLowerCase()}`).join(", ");

  return (
    <section className="mx-auto max-w-[1280px] px-5 py-24 sm:px-8 sm:py-36" aria-labelledby="finding-title">
      <div className="grid items-end gap-12 lg:grid-cols-[1.25fr_1fr] lg:gap-20">
        <div>
          <h2 id="finding-title" className="display text-[clamp(2.6rem,5.6vw,5rem)] leading-[0.98] tracking-[-0.035em]">
            {t ? <><span className="text-kept">{t.official} of {t.listed}</span> Google Maps listings show the office's own number.</>
              : <span className="invisible">Loading the finding</span>}
          </h2>
          <p className="mt-6 max-w-lg text-lg leading-relaxed text-ink-2">
            We matched the phone on each listing against the department's own directory.
          </p>
        </div>

        <div>
          <div ref={grid} role="img" aria-label={t ? `${offices.length} offices: ${summary}.` : "Loading"} className="grid grid-cols-10 gap-1.5 sm:gap-2">
            {(offices.length ? offices : Array.from({ length: 60 }, () => null)).map((o, i) => (
              <motion.div key={o?.id ?? i} title={o ? `${o.label}: ${MAPS[o.maps].label}` : undefined}
                initial={reduce ? false : { opacity: 0, scale: 0.4 }} animate={shown && o ? { opacity: 1, scale: 1 } : undefined}
                transition={{ duration: 0.8, delay: (i % 10) * 0.03 + Math.floor(i / 10) * 0.06, ease }}
                className={cn("aspect-square rounded-[28%]", o ? SQUARE[o.maps] : "bg-paper-2")} />
            ))}
          </div>
          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-ink-2">
            {ORDER.filter(count).map((s) => (
              <li key={s} className="flex items-center gap-2">
                <span className={cn("size-3 rounded-[28%]", SQUARE[s])} aria-hidden />{MAPS[s].label} <span className="tnum font-semibold text-ink">{count(s)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[13px] text-muted">One square per office.</p>
        </div>
      </div>

      {t && (
        <div className="mt-20 grid gap-10 sm:grid-cols-2 sm:gap-8 lg:grid-cols-[1.25fr_1fr] lg:gap-20">
          <Stat a={t.ai_right} b={t.ai}>Google AI Overview answers led with the office's own number.</Stat>
          <Stat a={t.ai_mode_right} b={t.ai_mode}>Google AI Mode answers led with the office's own number.</Stat>
        </div>
      )}
      <div className="mt-14 flex flex-wrap gap-3">
        <Link to="/offices" className="group inline-flex items-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-medium text-paper transition hover:bg-brand">
          See every office<ArrowRight className="size-4 transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:translate-x-1" />
        </Link>
        <Link to="/map" className="inline-flex items-center gap-2 rounded-full border border-rule bg-card px-5 py-3 text-sm font-medium text-ink transition hover:border-brand">Open the map</Link>
      </div>
    </section>
  );
}
