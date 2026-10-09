import { animate, motion, useInView, useReducedMotion } from "motion/react";
import { ReceiptText } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn, toneSoft, type Tone } from "../lib/ui";

const dot: Record<Tone, string> = { broken: "bg-broken", kept: "bg-kept", amber: "bg-amber", unknown: "bg-unknown" };

/** A verdict pill: one semantic colour, a dot, and a hairline ring so it holds its shape on any background. */
export function Chip({ tone, children, className }: { tone: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold leading-none ring-1 ring-inset ring-current/15", toneSoft[tone], className)}>
      <span className={cn("size-1.5 shrink-0 rounded-full", dot[tone])} aria-hidden />
      {children}
    </span>
  );
}

/** A number that counts up once it scrolls into view. */
export function CountUp({ value, className, duration = 1.4 }: { value: number; className?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);
  useEffect(() => {
    if (!inView || reduce) { if (reduce) setShown(value); return; }
    const controls = animate(0, value, { duration, ease: [0.16, 1, 0.3, 1], onUpdate: (v) => setShown(Math.round(v)) });
    return () => controls.stop();
  }, [inView, value, duration, reduce]);
  return <span ref={ref} className={cn("tnum", className)} aria-label={String(value)}>{shown}</span>;
}

/** Fades, lifts and un-blurs content as it scrolls into view. */
export function Reveal({ children, delay = 0, className, y = 24 }: { children: ReactNode; delay?: number; className?: string; y?: number }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} initial={{ opacity: 0, y, filter: "blur(6px)" }} whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-8% 0px" }} transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}>
      {children}
    </motion.div>
  );
}

/** Where a piece of evidence came from: a quiet receipt line under it, never hidden. */
export function Provenance({ children }: { children: ReactNode }) {
  return (
    <div className="mt-6 flex items-start gap-2 border-t border-rule/70 pt-3.5 text-[11.5px] font-medium leading-relaxed text-muted [&_a]:underline [&_a]:decoration-current/40 [&_a]:underline-offset-2 [&_a:hover]:text-ink">
      <ReceiptText className="mt-px size-3.5 shrink-0 text-muted" aria-hidden />
      <div className="flex min-w-0 flex-wrap gap-x-4 gap-y-1">{children}</div>
    </div>
  );
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("font-mono tracking-tight", className)}>{children}</span>;
}
