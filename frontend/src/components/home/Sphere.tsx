// "628 searches into one": a slowly turning globe of real evidence tiles (every office's own number and what Google
// Maps shows for it, and the six search engines), pinned while you scroll, that folds down into one office's answer.
import { motion, useInView, useReducedMotion, useScroll, useTransform } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chip } from "../bits";
import type { OfficeSummary, Overview } from "../../lib/api";
import { featured } from "./shared";
import { AI, MAPS, cn, toneBg } from "../../lib/ui";

const ENGINES: Record<string, string> = {
  google_maps: "Google Maps", google_maps_reviews: "Maps Reviews", google: "Google Search",
  google_ai_overview: "AI Overview", google_ai_mode: "AI Mode", bing_maps: "Bing Maps",
};

type Tile = { kind: "office"; o: OfficeSummary } | { kind: "engine"; name: string; count: number };


function TileCard({ t }: { t: Tile }) {
  if (t.kind === "engine") return (
    <div className="flex h-full flex-col justify-between rounded-2xl bg-gradient-to-br from-brand to-brand-2 p-3.5 text-white">
      <span className="serif text-[19px] leading-tight">{t.name}</span>
      <span className="tnum text-[12px] font-medium opacity-90">{t.count} searches</span>
    </div>
  );
  const m = MAPS[t.o.maps];
  return (
    <div className="flex h-full flex-col rounded-2xl border border-rule bg-card p-3.5 text-left">
      <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
        <span className={cn("size-1.5 rounded-full", toneBg[m.tone])} />{t.o.type_label}
      </span>
      <span className="serif mt-1 line-clamp-2 text-[15px] leading-[1.15] text-ink">{t.o.label}</span>
      <span className="mt-auto flex items-end justify-between gap-2">
        <span className="font-mono text-[11px] tracking-tight text-ink-2">{t.o.official || "No number"}</span>
        <span className="tnum text-[10px] text-muted">{t.o.reviews} reviews</span>
      </span>
    </div>
  );
}

export function Sphere({ overview, onAsk }: { overview: Overview | null; onAsk: (t: string) => void }) {
  const reduce = !!useReducedMotion();
  const section = useRef<HTMLElement>(null);
  const inView = useInView(section, { margin: "200px 0px" });
  const { scrollYProgress: p } = useScroll({ target: section, offset: ["start start", "end end"] });
  const [vw, setVw] = useState(() => innerWidth);
  useEffect(() => {
    const onResize = () => setVw(innerWidth);
    addEventListener("resize", onResize);
    return () => removeEventListener("resize", onResize);
  }, []);

  const tiles = useMemo<Tile[]>(() => {
    if (!overview) return [];
    const counts: Record<string, number> = {};
    for (const t of Object.values(overview.types)) for (const [e, n] of Object.entries(t.searches_by_engine)) counts[e] = (counts[e] ?? 0) + n;
    const engines: Tile[] = Object.entries(ENGINES).filter(([e]) => counts[e]).map(([e, name]) => ({ kind: "engine", name, count: counts[e] }));
    const offices: Tile[] = overview.offices.map((o) => ({ kind: "office", o }));
    // Spread the engines through the offices so they dot the globe instead of clustering at one pole.
    const step = Math.floor(offices.length / engines.length);
    return offices.flatMap((t, i) => i % step === 2 && engines[Math.floor(i / step)] ? [engines[Math.floor(i / step)], t] : [t]);
  }, [overview]);

  const scale = Math.min(1, Math.max(0.46, vw / 1250));
  const R = 470;
  const tilt = useTransform(p, [0, 1], reduce ? [-12, -12] : [-24, 18]);
  const turn = useTransform(p, [0, 1], reduce ? [0, 0] : [0, -140]);
  const globeScale = useTransform(p, [0, 0.12, 0.55, 0.78], reduce ? [1, 1, 1, 1] : [0.72, 1, 1, 0.16]);
  const globeOpacity = useTransform(p, [0.6, 0.8], reduce ? [1, 1] : [1, 0]);
  const titleY = useTransform(p, [0.5, 0.78], reduce ? [0, 0] : [0, -40]);
  const titleOpacity = useTransform(p, [0.55, 0.75], reduce ? [1, 1] : [1, 0]);
  const cardOpacity = useTransform(p, [0.7, 0.86], reduce ? [1, 1] : [0, 1]);
  const cardScale = useTransform(p, [0.7, 0.9], reduce ? [1, 1] : [0.86, 1]);
  const cardEvents = useTransform(p, (v: number) => reduce || v > 0.78 ? "auto" : "none");
  const cardBlur = useTransform(p, (v: number) => reduce || v >= 0.86 ? "none" : `blur(${Math.min(10, 10 * (1 - (v - 0.7) / 0.16))}px)`);

  const t = overview?.totals;
  const engines = tiles.filter((tile) => tile.kind === "engine").length;
  const office = overview ? featured(overview.offices) : null;
  const profile = office ? overview?.types[office.type]?.profile : null;

  const card = office && (
    <div className="surface-float w-[min(520px,100%)] rounded-[28px] p-6 text-left sm:p-8">
      <h3 className="serif text-[1.7rem] leading-tight sm:text-[2rem]">{office.label}</h3>
      <dl className="mt-5 divide-y divide-rule text-[15px]">
        <div className="flex flex-wrap items-center justify-between gap-2 py-3">
          <dt className="text-muted">Own number{profile ? `, from the ${profile.department} directory` : ""}</dt>
          <dd className="font-mono text-ink">{office.official}</dd>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 py-3">
          <dt className="text-muted">Google Maps</dt><dd><Chip tone={MAPS[office.maps].tone}>{MAPS[office.maps].label}</Chip></dd>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 py-3">
          <dt className="text-muted">Google's AI Overview</dt><dd><Chip tone={AI[office.ai].tone}>{AI[office.ai].label}</Chip></dd>
        </div>
      </dl>
      <button onClick={() => onAsk(`How do I reach ${office.label}, and what does Google show for it?`)}
        className="group mt-6 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-2">
        Ask about this office<ArrowRight className="size-4 transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:translate-x-1" />
      </button>
    </div>
  );

  return (
    <section ref={section} className={cn("relative", reduce ? "py-24" : "h-[320vh]")} aria-labelledby="sphere-title">
      <div className={cn("flex flex-col items-center justify-center overflow-hidden", reduce ? "gap-10" : "sticky top-0 h-dvh")}>
        {/* The globe. Tiles on the far side are hidden, so it reads as a lit dome turning toward you. */}
        <motion.div aria-hidden style={{ scale: globeScale, opacity: globeOpacity }}
          className={cn("pointer-events-none grid place-items-center [perspective:1600px]", reduce ? "relative h-[min(80vw,640px)] w-full" : "absolute inset-0")}>
          <div style={{ transform: `scale(${scale})` }} className="[transform-style:preserve-3d]">
            <motion.div style={{ rotateX: tilt, rotateY: turn }} className="[transform-style:preserve-3d]">
              <div className={cn("kh-spin-y relative size-0", (!inView || reduce) && "kh-paused")}>
                {tiles.map((tile, i) => {
                  const y = 1 - (2 * (i + 0.5)) / tiles.length;
                  const lon = i * 137.508;
                  const lat = Math.asin(y) * (180 / Math.PI);
                  return (
                    <div key={i} className="absolute -left-[88px] -top-[56px] h-[112px] w-[176px] [backface-visibility:hidden]"
                      style={{ transform: `rotateY(${lon}deg) rotateX(${lat}deg) translateZ(${R}px)` }}>
                      <TileCard t={tile} />
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </div>
        </motion.div>

        <motion.div style={{ y: titleY, opacity: titleOpacity }} className="relative z-10 px-5 text-center">
          <div className="absolute inset-[-20%] -z-10 rounded-full bg-[radial-gradient(closest-side,var(--color-paper)_45%,transparent)]" />
          <h2 id="sphere-title" className="display text-[clamp(3rem,9vw,8rem)] leading-[0.92] tracking-[-0.04em]">
            <span className="tnum text-brand">{t ? t.searches : " "}</span> searches<br />into <span className="relative">one<span className="text-pop">.</span></span>
          </h2>
          <p className="mx-auto mt-6 max-w-md text-base leading-relaxed text-ink-2 sm:text-lg">
            {engines ? `From ${engines} search engines, all through SerpApi.` : " "}
          </p>
        </motion.div>

        {card && (reduce ? <div className="px-5">{card}</div> : (
          <motion.div style={{ opacity: cardOpacity, scale: cardScale, filter: cardBlur, pointerEvents: cardEvents }} className="absolute inset-x-5 z-20 flex justify-center">{card}</motion.div>
        ))}
      </div>
    </section>
  );
}
