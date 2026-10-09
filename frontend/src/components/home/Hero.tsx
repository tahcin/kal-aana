// The first screen: one giant panel where office landlines are dialled and ring out around a greeting, and the ask box
// where the answer actually is. The headline and box paint at once over a static poster; the WebGL scene loads behind
// them and crossfades in when it's ready.
import { motion, useReducedMotion } from "motion/react";
import { lazy, Suspense, useCallback, useEffect, useRef, useState, type Ref } from "react";
import { Composer } from "./Composer";
import { EXAMPLES } from "./shared";
import { createSignals } from "./hero/signals";
import { SceneBoundary } from "./hero/SceneBoundary";
import "./hero/poster.css";
import { cn } from "../../lib/ui";


const Scene = lazy(() => import("./hero/Scene"));

const ease = [0.16, 1, 0.3, 1] as const;
const LINES = ["Namaskara,", "Bengaluru"];
const SWIRL_MS = 620;

/** WebGL2 is what three needs; checked once, before any of its code is fetched. */
const webgl = (() => {
  try { return !!document.createElement("canvas").getContext("webgl2"); } catch { return false; }
})();

/** Time until the next example: a stroke that draws once round the lit pill, on its own border, anticlockwise from the top. */
function TurnRing() {
  const ref = useRef<SVGSVGElement>(null);
  const [size, setSize] = useState<[number, number] | null>(null);
  useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize([el.offsetWidth, el.offsetHeight]));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  // The path runs along the centre of a 1.5px stroke laid just inside the pill's edge.
  const i = 0.75;
  const d = size && (() => {
    const [w, h] = size, r = h / 2 - i;
    return `M${w / 2} ${i}H${h / 2}A${r} ${r} 0 0 0 ${h / 2} ${h - i}H${w - h / 2}A${r} ${r} 0 0 0 ${w - h / 2} ${i}Z`;
  })();
  return (
    <svg ref={ref} aria-hidden className="pointer-events-none absolute inset-0 size-full overflow-visible">
      {d && <path d={d} pathLength={1} fill="none" strokeWidth={1.5} className="kh-turn stroke-brand/60" />}
    </svg>
  );
}

export function Hero({ onSend, busy, draft, inputRef, askRef }: {
  onSend: (t: string) => void; busy: boolean; draft: string; inputRef: Ref<HTMLTextAreaElement>; askRef: Ref<HTMLDivElement>;
}) {
  const reduce = !!useReducedMotion();
  const panel = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [signals] = useState(createSignals);
  const [example, setExample] = useState(0);
  const [typing, setTyping] = useState(!!draft);
  const [held, setHeld] = useState(false);  // an example chip is hovered or focused
  const [shown, setShown] = useState(false);  // the canvas has drawn, so fade it in
  const [running, setRunning] = useState(true);  // the panel is on screen and the tab is visible
  const [sending, setSending] = useState(false);
  const [dense] = useState(() => matchMedia("(min-width: 768px) and (pointer: fine)").matches);
  const onTyping = useCallback((t: boolean) => setTyping(t), []);
  const onReady = useCallback(() => { signals.ready = true; setShown(true); }, [signals]);

  // Turn to the next example every few seconds, unless the visitor is typing or looking at one. Each turn rings
  // another number in the background.
  useEffect(() => {
    if (typing || held) return;
    const t = setInterval(() => {
      if (document.hidden) return;
      setExample((e) => (e + 1) % EXAMPLES.length);
      signals.gust = 1;
    }, 5200);
    return () => clearInterval(t);
  }, [typing, held, signals]);

  // Render only while the panel is on screen and the tab is visible.
  useEffect(() => {
    const el = panel.current;
    if (!el) return;
    let visible = true;
    const sync = () => setRunning(visible && !document.hidden);
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; sync(); });
    io.observe(el);
    document.addEventListener("visibilitychange", sync);
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", sync); };
  }, []);

  // Sending: the rings close in on the ask box, then the conversation takes over. Without the scene, send at once.
  const timer = useRef(0);
  useEffect(() => () => clearTimeout(timer.current), []);
  const send = (text: string) => {
    if (sending) return;
    const r = box.current?.getBoundingClientRect();
    if (reduce || !signals.ready || !running || !r) { onSend(text); return; }
    signals.swirl = { x: r.left + r.width / 2, y: r.top + r.height / 2, ms: SWIRL_MS };
    setSending(true);
    timer.current = window.setTimeout(() => {
      onSend(text);
      signals.swirl = null;
      setSending(false);
    }, SWIRL_MS - 40);
  };

  const line = (i: number) => reduce ? {} : {
    initial: { y: "105%" }, animate: { y: "0%" }, transition: { duration: 1.5, delay: 0.25 + i * 0.12, ease },
  };
  const rise = (delay: number) => reduce ? {} : {
    initial: { opacity: 0, y: 22, filter: "blur(10px)" }, animate: { opacity: 1, y: 0, filter: "blur(0px)" }, transition: { duration: 1.3, delay, ease },
  };

  return (
    <section className="px-2 pb-6 pt-1 sm:px-4 sm:pt-2" aria-labelledby="hero-title">
      <div ref={panel} className="kh-hero relative isolate mx-auto h-[max(600px,min(calc(100svh-5rem),900px))] max-w-[1480px] overflow-hidden rounded-[28px] sm:rounded-[var(--radius-panel)]">
        {/* The poster: the scene's sky and canopy in CSS, there from the first paint and whenever WebGL isn't. */}
        <motion.div aria-hidden className="kh-poster-call absolute inset-0" initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }}
          transition={{ duration: 1.4, ease }} />
        {webgl && (
          <SceneBoundary>
            <Suspense fallback={null}>
              <div aria-hidden className={cn("absolute inset-0 transition-opacity duration-[1600ms] ease-[var(--ease-out-expo)]", shown ? "opacity-100" : "opacity-0")}>
                <Scene signals={signals} still={reduce} running={running} dense={dense} onReady={onReady} />
              </div>
            </Suspense>
          </SceneBoundary>
        )}
        <div aria-hidden className="kh-hero-veil pointer-events-none absolute inset-0" />
        <div aria-hidden className="kh-grain pointer-events-none absolute inset-0" />

        <div className="relative flex h-full flex-col items-center justify-center px-4 pb-6 text-center sm:px-8 sm:pb-10">
          <h1 id="hero-title" className="display text-[clamp(3.4rem,10.5vw,9.5rem)] leading-[0.9] tracking-[-0.045em] text-ink">
            {LINES.map((w, i) => (
              <span key={w} className="-mb-[0.12em] block overflow-hidden pb-[0.12em]">
                <motion.span {...line(i)} className="block">
                  {w}{i === 1 && <span className="text-pop">.</span>}
                </motion.span>
              </span>
            ))}
          </h1>
          <motion.p {...rise(0.75)} className="mt-5 max-w-md text-[1.05rem] leading-relaxed text-ink-2 sm:mt-7 sm:text-xl">
            Stuck at a government office? Start here.
          </motion.p>

          <motion.div ref={askRef} {...rise(1.05)} className="mt-8 w-full max-w-[760px] sm:mt-11">
            {/* The box keeps one line's room in the layout and grows downward over the examples, so the headline never moves. */}
            <div className="relative z-10 h-14 sm:h-[66px]">
              <div ref={box} className={cn("absolute inset-x-0 top-0 text-left transition-transform duration-500 ease-[var(--ease-out-expo)]", sending && "scale-[1.015]")}>
                <Composer variant="hero" onSend={send} busy={busy || sending} initial={draft} example={EXAMPLES[example].q} inputRef={inputRef} onTyping={onTyping} />
              </div>
            </div>
            {/* The examples by topic. The one in the box is lit, with a hairline that fills until the next turns; once the
                visitor is writing their own question they step back. */}
            <div className={cn("mt-4 flex flex-wrap justify-center gap-1.5 transition-opacity duration-500 sm:mt-5 sm:gap-2", typing && "pointer-events-none opacity-0")}
              role="group" aria-label="Example questions" aria-hidden={typing || undefined}
              onPointerLeave={() => setHeld(false)} onBlur={() => setHeld(false)}>
              {EXAMPLES.map((e, i) => {
                const on = i === example;
                return (
                  <button key={e.q} type="button" disabled={busy || sending} onClick={() => send(e.q)} tabIndex={typing ? -1 : undefined}
                    onPointerEnter={() => { setHeld(true); setExample(i); }} onFocus={() => { setHeld(true); setExample(i); }}
                    aria-label={`Ask: ${e.q}`}
                    className={cn("relative h-8 rounded-full px-3.5 text-[13px] font-medium backdrop-blur-md transition-[background-color,color,box-shadow] duration-500 ease-[var(--ease-out-expo)] sm:h-9 sm:px-4 sm:text-sm",
                      on ? "bg-card/90 text-ink shadow-[0_1px_2px_rgb(40_22_80/0.06),0_6px_16px_-8px_rgb(40_22_80/0.25)]"
                        : "bg-card/40 text-ink-2 ring-1 ring-inset ring-white/50 hover:bg-card/70")}>
                    {e.topic}
                    {on && !held && !reduce && <TurnRing key={example} />}
                  </button>
                );
              })}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
