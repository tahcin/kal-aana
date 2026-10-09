// What Kal Aana is, in one paragraph that sharpens word by word as it scrolls past. The counts come from the API.
import { motion, useReducedMotion, useScroll, useTransform, type MotionValue } from "motion/react";
import { Landmark, LockKeyhole, ReceiptText, Search, UsersRound, type LucideIcon } from "lucide-react";
import { Fragment, useRef, type ReactNode } from "react";
import type { Totals } from "../../lib/api";

type Piece = string | { icon: LucideIcon; tone: string } | { n: keyof Totals };

const TEXT: Piece[] = [
  "Kal Aana checks what", { icon: Landmark, tone: "bg-wash text-brand" }, { n: "offices" }, "public offices promise against what",
  { icon: Search, tone: "bg-pop-soft text-[#9a5b00]" }, "Google shows you and what", { icon: UsersRound, tone: "bg-kept-soft text-kept" },
  "citizens report. The evidence comes from", { icon: ReceiptText, tone: "bg-wash text-brand" }, { n: "searches" },
  "saved searches and the departments' own directories. It's free, needs no login, and keeps no record of your conversation.",
  { icon: LockKeyhole, tone: "bg-pop-soft text-[#9a5b00]" },
];

function Word({ children, progress, at, reduce }: { children: ReactNode; progress: MotionValue<number>; at: [number, number]; reduce: boolean }) {
  const opacity = useTransform(progress, at, [0.14, 1]);
  const blur = useTransform(progress, at, [6, 0], { clamp: true });
  const filter = useTransform(blur, (b) => b < 0.2 ? "none" : `blur(${b}px)`);
  if (reduce) return <span className="inline-block">{children}</span>;
  return <motion.span style={{ opacity, filter }} className="inline-block">{children}</motion.span>;
}

export function Manifesto({ totals }: { totals: Totals | undefined }) {
  const reduce = !!useReducedMotion();
  const ref = useRef<HTMLParagraphElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 0.85", "end 0.5"] });
  // One token per word or pill; each sharpens over its own slice of the scroll.
  const tokens = TEXT.flatMap<Piece>((p) => typeof p === "string" ? p.split(" ") : [p]);
  const n = tokens.length;
  return (
    <section className="mx-auto max-w-[1180px] px-5 pb-24 pt-24 sm:px-8 sm:pb-36 sm:pt-40">
      <p ref={ref} className="display text-[clamp(2rem,4.6vw,4.1rem)] leading-[1.12] tracking-[-0.03em]">
        <span className="sr-only">
          {TEXT.map((p) => typeof p === "string" ? p : "n" in p ? (totals ? totals[p.n] : "") : "").join(" ").replace(/\s+/g, " ")}
        </span>
        <span aria-hidden>
          {tokens.map((t, i) => {
            const at: [number, number] = [i / n, Math.min(1, (i + 2) / n)];
            const body = typeof t === "string" ? t
              : "icon" in t ? (
                <span className={`relative top-[-0.08em] inline-grid size-[0.92em] place-items-center rounded-full align-middle ${t.tone}`}>
                  <t.icon className="size-[0.48em]" strokeWidth={2.2} />
                </span>
              ) : (
                <span className="tnum inline-block min-w-[1.2ch] text-brand">{totals ? String(totals[t.n]) : " "}</span>
              );
            return <Fragment key={i}><Word progress={scrollYProgress} at={at} reduce={reduce}>{body}</Word>{" "}</Fragment>;
          })}
        </span>
      </p>
    </section>
  );
}
