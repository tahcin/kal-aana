// "The unanswered call": the hero as the familiar experience of phoning a public office. Office landline numbers,
// as their departments publish them, float at different depths round the headline. One at a time comes into focus,
// is dialled, rings and goes quiet; then a marigold light carries the question to the ask box. The numbers are shown
// only as published numbers: nothing here says whether any of them is answered.
import { useEffect, useMemo, useRef } from "react";
import { useJSON, type Overview } from "../../../lib/api";
import type { SceneProps } from "./signals";
import { Director, type Depth } from "./director";
import "./scene.css";

type Slot = { x: number; y: number; side: "l" | "r"; depth: Depth; calls: boolean };

// Where the numbers sit, as fractions of the panel: the left margin and the top band on a wide screen (the dial
// takes the right), the bands above the headline and below the examples on a phone. Only the numbers beside the box make calls, so the answer's
// path into the box never crosses the headline.
const SLOTS: Record<"wide" | "narrow", Slot[]> = {
  wide: [
    { x: 0.045, y: 0.15, side: "l", depth: "mid", calls: true },
    { x: 0.09, y: 0.4, side: "l", depth: "near", calls: true },
    { x: 0.04, y: 0.63, side: "l", depth: "far", calls: true },
    { x: 0.075, y: 0.83, side: "l", depth: "mid", calls: true },
    { x: 0.27, y: 0.05, side: "l", depth: "far", calls: false },
    { x: 0.72, y: 0.055, side: "r", depth: "far", calls: false },
  ],
  narrow: [
    { x: 0.07, y: 0.05, side: "l", depth: "far", calls: false },
    { x: 0.93, y: 0.12, side: "r", depth: "mid", calls: false },
    { x: 0.07, y: 0.79, side: "l", depth: "mid", calls: true },
    { x: 0.12, y: 0.89, side: "l", depth: "far", calls: true },
  ],
};

/** "KA-01 RTO Bengaluru Central (HSR Layout)" to "HSR Layout RTO"; passport offices keep their own short names. */
function shortName(label: string): string {
  const m = label.match(/\b(A?RTO) (.+?)(?: \((.+)\))?$/);
  if (!m) return label.replace(/, Bengaluru$/, "");
  const [, kind, name, area] = m;
  return `${area && !/ and /.test(area) ? area : name} ${kind}`;
}

export default function Scene({ signals, still, running, dense, onReady }: SceneProps) {
  const { data } = useJSON<Overview>("/api/overview");
  const root = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const layer = useRef<HTMLDivElement>(null);
  const director = useRef<Director | null>(null);
  const slots = SLOTS[dense ? "wide" : "narrow"];

  // Office landlines (the 080 numbers of the RTOs and passport offices), one per number, alternating kinds.
  const lines = useMemo(() => {
    if (!data) return [];
    const seen = new Set<string>();
    const pool = data.offices.filter((o) => /^080 /.test(o.official) && !seen.has(o.official) && seen.add(o.official));
    const rto = pool.filter((o) => o.type === "rto"), other = pool.filter((o) => o.type !== "rto");
    const mixed = rto.flatMap((o, i) => (i % 3 === 1 && other.length ? [other.shift()!, o] : [o]));
    return mixed.slice(0, slots.length).map((o) => ({ id: o.id, name: shortName(o.label), number: o.official }));
  }, [data, slots.length]);

  useEffect(() => {
    if (!canvas.current || !root.current || !layer.current) return;
    let d: Director;
    try {
      d = new Director(canvas.current, root.current, layer.current, signals, dense, onReady);
    } catch {
      return; // No WebGL2 after all: the poster stays.
    }
    director.current = d;
    d.measure();
    const ro = new ResizeObserver(() => { d.measure(); if (still) d.still(); });
    ro.observe(root.current);
    const move = (e: PointerEvent) => d.setPointer(e.clientX, e.clientY);
    if (!still) addEventListener("pointermove", move, { passive: true });
    return () => { ro.disconnect(); removeEventListener("pointermove", move); d.dispose(); director.current = null; };
  }, [signals, dense, still, onReady]);

  // Hand the numbers to the timeline once they are on the page.
  useEffect(() => {
    const d = director.current;
    if (!d || !layer.current) return;
    d.setFragments([...layer.current.querySelectorAll<HTMLElement>("[data-frag]")]);
    if (still) d.still();
  }, [lines, still, dense]);

  // Run the clock only while the panel is visible; in reduced motion draw once.
  useEffect(() => {
    const d = director.current;
    if (!d) return;
    if (still) { d.still(); return; }
    if (!running) return;
    // Adaptive resolution: a frame time averaged over a few seconds above ~22 ms (under about 45 fps) steps the
    // shader's resolution down, to 60% at most; a long fast run steps it back up. The change is applied before the
    // frame is drawn (a resize wipes the canvas), and at most every few seconds, so a scroll's brief hitch never
    // triggers it. Capable devices never leave full resolution.
    let raf = 0, last = performance.now(), avg = 16, quality = 1, since = 0, scrolled = -1e9, odd = false, owed = 0;
    // While the page is scrolling, draw every other frame: the scene is sliding past anyway, and the GPU time goes to
    // the scroll itself. Full rate resumes the moment scrolling stops.
    const onScroll = () => { scrolled = performance.now(); };
    addEventListener("scroll", onScroll, { passive: true });
    const loop = (now: number) => {
      const dt = now - last;
      last = now;
      raf = requestAnimationFrame(loop);
      if (now - scrolled < 160 && (odd = !odd)) { owed += dt; return; }
      const step = dt + owed;
      owed = 0;
      if (dt < 250) {  // ignore the gap after a tab switch or a scroll back into view
        avg += (dt - avg) * 0.01;
        since += dt;
        const down = avg > 22 && quality > 0.6 && since > 3000, up = avg < 18 && quality < 1 && since > 8000;
        if (down || up) {
          quality = Math.round((quality + (down ? -0.1 : 0.1)) * 10) / 10;
          d.setQuality(quality);
          since = 0;
        }
      }
      d.tick(step / 1000);
    };
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); removeEventListener("scroll", onScroll); };
  }, [still, running, dense, lines]);

  return (
    <div ref={root} className="kc-scene absolute inset-0">
      <canvas ref={canvas} className="absolute inset-0 size-full" />
      <div ref={layer} className="kc-layer absolute inset-0">
        {lines.map((l, i) => {
          const s = slots[i];
          let n = 0;
          return (
            <div key={l.id} data-frag data-depth={s.depth} data-side={s.side} data-calls={s.calls ? "1" : "0"} className="kc-frag"
              style={{ top: `${s.y * 100}%`, ...(s.side === "l" ? { left: `${s.x * 100}%` } : { right: `${(1 - s.x) * 100}%` }), transitionDelay: `${i * 90}ms` }}>
              <span data-dot className="kc-dot" />
              <span className="kc-text">
                <span className="kc-num">
                  {[...l.number].map((ch, j) => (ch === " " ? <span key={j} className="kc-gap" /> : <span key={j} data-digit={n++}>{ch}</span>))}
                </span>
                <span className="kc-name">{l.name}</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
