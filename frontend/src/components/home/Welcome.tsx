// The home page before any question: a scroll story from the greeting to the finding, with an ask box never far away.
import { AnimatePresence, motion, useInView } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useRef } from "react";
import { Footer } from "../Shell";
import { Reveal } from "../bits";
import type { Overview } from "../../lib/api";
import { Composer } from "./Composer";
import { Hero } from "./Hero";
import { Finding } from "./Finding";
import { Manifesto } from "./Manifesto";
import { Promises } from "./Promises";
import { Sphere } from "./Sphere";
import { featured, focusQuietly } from "./shared";
import "./home.css";

const ease = [0.16, 1, 0.3, 1] as const;

/** A marigold, the flower of every Bengaluru garland, turning slowly. */
function Marigold({ className }: { className: string }) {
  return (
    <svg viewBox="-50 -50 100 100" aria-hidden className={`kh-rotate absolute ${className}`}>
      {Array.from({ length: 14 }, (_, i) => <ellipse key={i} cx={0} cy={-30} rx={9} ry={17} fill="#ff9a1f" transform={`rotate(${i * (360 / 14)})`} />)}
      {Array.from({ length: 12 }, (_, i) => <ellipse key={i} cx={0} cy={-19} rx={7} ry={12} fill="#ffb31a" transform={`rotate(${i * 30 + 15})`} />)}
      <circle r={12} fill="#ffc94d" /><circle r={5} fill="#e07a00" opacity={0.6} />
    </svg>
  );
}

export function Welcome({ onSend, busy, overview, draft }: { onSend: (t: string) => void; busy: boolean; overview: Overview | null; draft: string }) {
  const ask = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const closing = useRef<HTMLElement>(null);
  const heroAskVisible = useInView(ask, { initial: true });
  const closingVisible = useInView(closing);
  const office = overview ? featured(overview.offices) : null;

  const backToTop = () => {
    scrollTo({ top: 0, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    setTimeout(() => focusQuietly(input.current), 600);
  };

  return (
    <div className="overflow-x-clip">
      <Hero onSend={onSend} busy={busy} draft={draft} inputRef={input} askRef={ask} />
      <Manifesto totals={overview?.totals} />
      <Sphere overview={overview} onAsk={onSend} />
      <Finding overview={overview} />
      <Promises office={office} />

      <section ref={closing} className="px-3 sm:px-5" aria-labelledby="closing-title">
        <div className="clip-corners relative mx-auto max-w-[1400px] overflow-hidden rounded-[28px] bg-gradient-to-br from-brand via-brand-2 to-[#c9a6ff] px-6 py-20 text-center text-white sm:rounded-[var(--radius-panel)] sm:py-28">
          <div aria-hidden className="absolute -bottom-32 -left-20 size-80 rounded-full bg-white/20 blur-[90px]" />
          <Marigold className="-right-6 -top-6 size-28 sm:right-[8%] sm:top-10 sm:size-36" />
          <Marigold className="-bottom-8 left-[6%] size-20 [animation-direction:reverse] sm:size-24" />
          <Marigold className="bottom-12 right-[14%] hidden size-14 sm:block" />
          <Reveal className="relative">
            <h2 id="closing-title" className="display text-[clamp(3.2rem,9vw,7.5rem)] leading-[0.95] tracking-[-0.04em] text-white">Go on, ask<span className="text-pop">.</span></h2>
            <button onClick={backToTop}
              className="group mt-10 inline-flex items-center gap-3 rounded-full bg-white py-2 pl-6 pr-2 text-[15px] font-medium text-[#1c1530] shadow-[var(--shadow-float)] transition hover:scale-[1.02]">
              Ask Kal Aana
              <span className="grid size-10 place-items-center rounded-full bg-pop transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:translate-x-0.5"><ArrowRight className="size-5" /></span>
            </button>
          </Reveal>
        </div>
      </section>

      <Footer />

      {/* Once the hero's box has scrolled away, a smaller one floats at the bottom of the screen. */}
      <AnimatePresence>
        {!heroAskVisible && !closingVisible && (
          <motion.div initial={{ opacity: 0, y: 40, filter: "blur(8px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} exit={{ opacity: 0, y: 40, filter: "blur(8px)" }}
            transition={{ duration: 0.6, ease }} className="fixed inset-x-3 bottom-4 z-30 mx-auto max-w-[640px] sm:bottom-6">
            <Composer variant="bar" onSend={onSend} busy={busy} placeholder="Ask about a public office" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
