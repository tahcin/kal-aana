import { motion, useReducedMotion } from "motion/react";
import { Bot, EyeOff, FileSearch, Globe, Landmark, MapPinned, MessageSquareText, Search, Sparkles, type LucideIcon } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router";
import { CountUp, Mono, Reveal } from "../components/bits";
import { Footer } from "../components/Shell";
import { apiUrl, useJSON, type Method as MethodData, type OfficeDetail, type Overview, type Score } from "../lib/api";
import { cn } from "../lib/ui";
import { useTitle } from "../lib/useTitle";

const pct = (v: number | null) => (v === null ? "n/a" : `${Math.round(v * 100)}%`);
const EASE = [0.16, 1, 0.3, 1] as const;

const ENGINES: Record<string, { label: string; icon: LucideIcon; what: string }> = {
  google_maps: { label: "Google Maps", icon: MapPinned, what: "Every office's listing: phone, hours, website, and whether anyone has claimed it" },
  google_maps_reviews: { label: "Maps Reviews", icon: MessageSquareText, what: "Newest reviews for unbiased counts, plus keyword pages for evidence" },
  google: { label: "Google Search", icon: Search, what: '"<office> phone number", searched from Bengaluru, as a citizen would' },
  google_ai_overview: { label: "AI Overview", icon: Sparkles, what: "What Google's AI tells that citizen, every number and PIN checked" },
  google_ai_mode: { label: "AI Mode", icon: Bot, what: "The same question in Google's AI Mode, checked the same way, to compare the two AI answers" },
  bing_maps: { label: "Bing Maps", icon: Globe, what: "Each office looked up outside Google, matched to its Google listing by location" },
};

const SECTIONS = [
  ["promise", "The promise"], ["reality", "The reality"], ["score", "The listing score"], ["reviews", "Reading the reviews"],
  ["breaches", "Possible breaches"], ["privacy", "Privacy"], ["build", "Use it from code"], ["chat", "The chat"], ["scale", "All of India"], ["limits", "Limits"],
] as const;

const MCP_TOOLS = ["how_to_reach", "office_report", "compare_offices", "statutory_timeline", "read_a_complaint", "check_wait",
  "google_ai_answers", "office_reviews", "draft_complaint", "best_time_to_visit", "search_official_sites", "search_news"];

/* ---------- The pipeline diagram ---------- */

type Box = { x: number; y: number; w: number; h: number };
const mid = (b: Box, side: "l" | "r" | "t" | "b"): [number, number] =>
  side === "l" ? [b.x, b.y + b.h / 2] : side === "r" ? [b.x + b.w, b.y + b.h / 2] : side === "t" ? [b.x + b.w / 2, b.y] : [b.x + b.w / 2, b.y + b.h];
/** A soft S-curve between two points, horizontal or vertical. */
function curve([x1, y1]: [number, number], [x2, y2]: [number, number], vertical = false) {
  if (vertical) { const m = (y1 + y2) / 2; return `M${x1} ${y1} C${x1} ${m} ${x2} ${m} ${x2} ${y2}`; }
  const m = (x1 + x2) / 2;
  return `M${x1} ${y1} C${m} ${y1} ${m} ${y2} ${x2} ${y2}`;
}

function Wire({ d, i, flow }: { d: string; i: number; flow: boolean }) {
  const reduce = useReducedMotion();
  return (
    <g>
      <motion.path d={d} fill="none" className="stroke-brand/45" strokeWidth={1.5} strokeLinecap="round"
        initial={reduce ? false : { pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 1.1, delay: 0.1 + i * 0.05, ease: EASE }} />
      {/* A marigold bead travels each wire: the data moving through. Decorative, and off for reduced motion. */}
      {flow && !reduce && (
        <circle r={3.2} className="fill-pop">
          <animateMotion dur={`${2.6 + (i % 4) * 0.35}s`} begin={`${(i * 0.37) % 2.4}s`} repeatCount="indefinite" path={d} />
        </circle>
      )}
    </g>
  );
}

function Node({ b, title, sub, tone = "card", children }: { b: Box; title: string; sub?: string; tone?: "card" | "brand" | "wash"; children?: ReactNode }) {
  return (
    <g>
      <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={18}
        className={cn(tone === "brand" ? "fill-brand" : tone === "wash" ? "fill-wash stroke-brand/25" : "fill-card stroke-rule")} strokeWidth={1} />
      <text x={b.x + 18} y={b.y + 28} className={cn("text-[13px] font-semibold", tone === "brand" ? "fill-paper/80" : "fill-brand")}>{title}</text>
      {sub && <text x={b.x + 18} y={b.y + 48} className={cn("text-[13.5px]", tone === "brand" ? "fill-paper" : "fill-ink-2")}>{sub}</text>}
      {children}
    </g>
  );
}

function EnginePill({ b, id, count, compact }: { b: Box; id: string; count: number; compact?: boolean }) {
  const E = ENGINES[id];
  return (
    <g>
      <rect x={b.x} y={b.y} width={b.w} height={b.h} rx={b.h / 2} className="fill-card stroke-rule" strokeWidth={1} />
      <circle cx={b.x + b.h / 2} cy={b.y + b.h / 2} r={b.h / 2 - 6} className="fill-wash" />
      <E.icon x={b.x + b.h / 2 - 8} y={b.y + b.h / 2 - 8} width={16} height={16} className="text-brand" aria-hidden />
      <text x={b.x + b.h + 4} y={b.y + b.h / 2 + 4.5} className={cn("fill-ink font-semibold", compact ? "text-[12px]" : "text-[14px]")}>{E.label}</text>
      <text x={b.x + b.w - (compact ? 11 : 16)} y={b.y + b.h / 2 + 4.5} textAnchor="end" className={cn("fill-muted font-mono", compact ? "text-[10.5px]" : "text-[12px]")}>{count}</text>
    </g>
  );
}

function Pipeline({ engines, searches }: { engines: Record<string, number>; searches: number }) {
  const ids = Object.keys(ENGINES);
  // Wide: left to right. Engines feed the saved snapshot; it and the official promise feed the scoring; scoring makes the cards; the cards serve three doors.
  const W = {
    engines: ids.map((_, i) => ({ x: 0, y: 66 + i * 58, w: 232, h: 46 })),
    snap: { x: 310, y: 170, w: 200, h: 140 }, promise: { x: 566, y: 14, w: 256, h: 92 }, score: { x: 566, y: 160, w: 256, h: 160 },
    cards: { x: 880, y: 196, w: 150, h: 88 }, outs: [0, 1, 2].map((i) => ({ x: 1090, y: 118 + i * 88, w: 150, h: 68 })),
  };
  // Narrow: top to bottom.
  // Narrow: top to bottom, with the six engines grouped so one wire leaves the group.
  const N = {
    group: { x: 0, y: 0, w: 360, h: 196 },
    engines: ids.map((_, i) => ({ x: 12 + (i % 2) * 172, y: 40 + Math.floor(i / 2) * 50, w: 164, h: 42 })),
    snap: { x: 0, y: 240, w: 172, h: 120 }, promise: { x: 188, y: 240, w: 172, h: 120 }, score: { x: 30, y: 414, w: 300, h: 132 },
    cards: { x: 90, y: 600, w: 180, h: 70 }, outs: [0, 1, 2].map((i) => ({ x: i * 122, y: 724, w: 116, h: 46 })),
  };
  const outs = [["Chat", "Ask in your words"], ["MCP server", "For AI assistants"], ["JSON API", "Data and docs"]];
  const scoreLines = ["Listing score: six checks", "Reviews read in five languages", "Waits checked against the limit"];

  const wide = [
    ...W.engines.map((e) => curve(mid(e, "r"), mid(W.snap, "l"))), curve(mid(W.snap, "r"), mid(W.score, "l")), curve(mid(W.promise, "b"), mid(W.score, "t"), true),
    curve(mid(W.score, "r"), mid(W.cards, "l")), ...W.outs.map((o) => curve(mid(W.cards, "r"), mid(o, "l"))),
  ];
  const narrow = [
    curve(mid(N.group, "b"), mid(N.snap, "t"), true), curve(mid(N.snap, "b"), [130, N.score.y], true), curve(mid(N.promise, "b"), [230, N.score.y], true),
    curve(mid(N.score, "b"), mid(N.cards, "t"), true), ...N.outs.map((o) => curve(mid(N.cards, "b"), mid(o, "t"), true)),
  ];

  const body = (L: typeof W, wires: string[], narrowLayout: boolean) => (
    <>
      {wires.map((d, i) => <Wire key={i} d={d} i={i} flow />)}
      {narrowLayout && (
        <g>
          <rect x={N.group.x} y={N.group.y} width={N.group.w} height={N.group.h} rx={22} className="fill-wash/60 stroke-brand/25" strokeWidth={1} strokeDasharray="4 5" />
          <text x={14} y={26} className="fill-brand text-[13px] font-semibold">SerpApi engines</text>
        </g>
      )}
      {ids.map((id, i) => <EnginePill key={id} b={L.engines[i]} id={id} count={engines[id] ?? 0} compact={narrowLayout} />)}
      <Node b={L.snap} title="Saved snapshot" tone="wash">
        <text x={L.snap.x + 18} y={L.snap.y + (narrowLayout ? 74 : 84)} className="fill-ink font-serif text-[40px]">{searches}</text>
        <text x={L.snap.x + 18} y={L.snap.y + (narrowLayout ? 94 : 108)} className="fill-ink-2 text-[12px]">{narrowLayout ? "searches, each with" : "searches, each with its"}</text>
        <text x={L.snap.x + 18} y={L.snap.y + (narrowLayout ? 109 : 124)} className="fill-ink-2 text-[12px]">{narrowLayout ? "its search ID" : "SerpApi search ID"}</text>
      </Node>
      <Node b={L.promise} title="The promise" sub={narrowLayout ? "Directories and" : "Official directories, the Sakala"}>
        <text x={L.promise.x + 18} y={L.promise.y + 66} className="fill-ink-2 text-[13.5px]">{narrowLayout ? "time limits" : "compendium, the Citizen's Charter"}</text>
      </Node>
      <Node b={L.score} title="Scoring" tone="brand">
        {scoreLines.map((s, i) => (
          <g key={s}>
            <circle cx={L.score.x + 22} cy={L.score.y + 56 + i * 28} r={3} className="fill-pop" />
            <text x={L.score.x + 34} y={L.score.y + 60 + i * 28} className="fill-paper text-[14px]">{s}</text>
          </g>
        ))}
      </Node>
      <Node b={L.cards} title="Evidence" sub="cards, with sources" />
      {L.outs.map((o, i) => <Node key={i} b={o} title={outs[i][0]} sub={narrowLayout ? undefined : outs[i][1]} />)}
    </>
  );

  return (
    <figure className="surface overflow-hidden rounded-[var(--radius-panel)] bg-[radial-gradient(120%_80%_at_0%_0%,var(--color-wash),transparent_60%)] p-5 sm:p-10">
      <svg viewBox="-4 0 1248 440" className="hidden w-full md:block" role="img" aria-label={`Pipeline: six SerpApi engines feed a saved snapshot of ${searches} searches; it and the official promise feed the scoring, which builds evidence cards for the chat, the MCP server and the JSON API.`}>
        {body(W, wide, false)}
      </svg>
      <svg viewBox="-2 -2 364 776" className="mx-auto w-full max-w-[420px] md:hidden" role="img" aria-label={`Pipeline: six SerpApi engines feed a saved snapshot of ${searches} searches; it and the official promise feed the scoring, which builds evidence cards for the chat, the MCP server and the JSON API.`}>
        {body(N as typeof W, narrow, true)}
      </svg>
      <figcaption className="mt-6 border-t border-rule pt-4 text-[13px] text-muted">
        Numbers on the engines are the searches each one ran.
      </figcaption>
    </figure>
  );
}

/* ---------- Long-form pieces ---------- */

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} data-section className="scroll-mt-24 border-t border-rule py-16 first:border-t-0 first:pt-0 sm:py-20">
      <Reveal>
        <h2 className="headline text-[clamp(2rem,4.2vw,3.25rem)]">{title}</h2>
      </Reveal>
      <Reveal delay={0.06} className="mt-7">{children}</Reveal>
    </section>
  );
}

const prose = "max-w-[66ch] text-[1.05rem] leading-[1.7] text-ink-2";

function Meter({ label, score, strong }: { label: string; score: Score; strong?: boolean }) {
  const reduce = useReducedMotion();
  return (
    <div className={cn("relative rounded-[1.5rem] p-5", strong ? "surface ring-2 ring-brand/70" : "border border-rule")}>
      {strong && <span className="absolute -top-2.5 right-4 rounded-full bg-pop px-2.5 py-0.5 text-[11px] font-bold text-[#1c1530]">Used</span>}
      <p className="font-semibold">{label}</p>
      {(["precision", "recall"] as const).map((k) => (
        <div key={k} className="mt-4">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[13px] text-muted">{k === "precision" ? "Flags that were right" : "Reports it found"}</span>
            <span className="serif tnum text-[1.75rem] leading-none">{pct(score[k])}</span>
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-paper-2">
            <motion.div className={cn("h-full rounded-full", strong ? "bg-brand" : "bg-muted/60")} initial={reduce ? false : { width: 0 }}
              style={reduce ? { width: pct(score[k]) } : undefined} whileInView={{ width: pct(score[k]) }} viewport={{ once: true }} transition={{ duration: 1.1, ease: EASE }} />
          </div>
        </div>
      ))}
      <p className="mt-4 text-xs text-muted">{score.flags_right} of {score.flags} flags right · {score.reports_found} of {score.reports} reports found</p>
    </div>
  );
}

function Code({ children }: { children: string }) {
  return <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-all rounded-2xl bg-ink p-4 font-mono text-[12px] leading-relaxed text-paper">{children}</pre>;
}

/** The section in view, for the contents list. */
function useActiveSection(ready: boolean) {
  const [active, setActive] = useState<string>(SECTIONS[0][0]);
  useEffect(() => {
    if (!ready) return;
    const obs = new IntersectionObserver((entries) => {
      const seen = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (seen) setActive(seen.target.id);
    }, { rootMargin: "-20% 0px -70% 0px" });
    document.querySelectorAll("[data-section]").forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [ready]);
  return active;
}

export default function Method() {
  useTitle("Method");
  const { data: overview } = useJSON<Overview>("/api/overview");
  const { data: method } = useJSON<MethodData>("/api/method");
  const { data: sample } = useJSON<OfficeDetail>("/api/office/rto-ka05");
  const engines: Record<string, number> = {};
  Object.values(overview?.types ?? {}).forEach((t) => Object.entries(t.searches_by_engine).forEach(([k, v]) => (engines[k] = (engines[k] ?? 0) + v)));
  const rules = overview?.types.rto?.rules;
  const checks = sample?.office.reach.checks ?? [];
  const total = checks.reduce((s, c) => s + c.max_points, 0);
  const { hash } = useLocation();
  // Sections fill in as data arrives, so jump to a linked section (such as #build) once it has.
  useEffect(() => { if (hash && method) document.getElementById(hash.slice(1))?.scrollIntoView(); }, [hash, method]);
  const active = useActiveSection(!!overview);

  return (
    <main>
      <header className="mx-auto max-w-7xl px-4 pt-12 sm:px-6 sm:pt-20">
        <Reveal><h1 className="headline max-w-[13ch] text-[clamp(3rem,9vw,7.5rem)] leading-[0.95] tracking-[-0.04em]">How we know what we show.</h1></Reveal>
        <Reveal delay={0.1}>
          <p className="serif mt-8 max-w-[38ch] text-[1.45rem] leading-snug text-ink-2 sm:text-[1.75rem]">
            Every number on this site is computed from saved search results and official documents, and every saved search keeps its SerpApi search ID.
          </p>
        </Reveal>
        {overview && (
          <dl className="mt-12 grid max-w-4xl grid-cols-2 gap-y-6 border-y border-rule py-6 sm:grid-cols-4">
            {[[overview.totals.searches, "SerpApi searches"], [Object.keys(ENGINES).length, "search engines"], [overview.totals.offices, "public offices"], [method?.heldout_reviews ?? 0, "hand-labelled test reviews"]].map(([v, l]) => (
              <div key={String(l)} className="pr-4">
                <dt className="sr-only">{l}</dt>
                <dd><p className="serif text-[2.6rem] leading-none tracking-[-0.03em]"><CountUp value={Number(v)} /></p><p className="mt-2 text-[13px] text-muted" aria-hidden>{l}</p></dd>
              </div>
            ))}
          </dl>
        )}
      </header>

      <section className="mx-auto mt-14 max-w-7xl px-4 sm:mt-20 sm:px-6" aria-label="How the data flows">
        <Reveal><Pipeline engines={engines} searches={overview?.totals.searches ?? 0} /></Reveal>
      </section>

      <div className="mx-auto mt-20 grid max-w-7xl gap-12 px-4 sm:px-6 lg:mt-28 lg:grid-cols-[13rem_minmax(0,1fr)] lg:gap-20">
        <nav aria-label="On this page" className="hidden lg:block">
          <ol className="sticky top-28 space-y-0.5 border-l border-rule text-[13px]">
            {SECTIONS.map(([id, label]) => (
              <li key={id}>
                <a href={`#${id}`} className={cn("relative -ml-px block border-l-2 py-1.5 pl-4 transition-colors",
                  active === id ? "border-brand font-semibold text-ink" : "border-transparent text-muted hover:text-ink")}>
                  {label}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <div className="min-w-0">
          <Section id="promise" title="The promise">
            <p className={prose}>Every office starts from what it officially promises: the phone numbers its own department publishes, and the working days the law gives it for each service. These come from official documents, not from searches, so they are the yardstick everything else is measured against.</p>
            <div className="mt-8 grid gap-3 sm:grid-cols-2 [&>*]:min-w-0">
              {([
                [Landmark, "Official directories", "Phone numbers and addresses from the Karnataka Transport Department, the Department of Stamps and Registration and Passport Seva (Ministry of External Affairs)."],
                [FileSearch, "Time limits", "Karnataka's Sakala Service Compendium, with the PDF page for each service. Passport offices follow the Passport Seva Citizen's Charter, counted from the day complete documents are received."],
              ] as const).map(([Icon, title, text]) => (
                <div key={title} className="surface rounded-[1.5rem] p-6">
                  <span className="grid size-11 place-items-center rounded-full bg-kept-soft text-kept"><Icon className="size-5" aria-hidden /></span>
                  <p className="mt-4 text-lg font-semibold">{title}</p><p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">{text}</p>
                </div>
              ))}
            </div>
          </Section>

          <Section id="reality" title="The reality, through SerpApi">
            <p className={prose}>Then the same office as a citizen finds it: its Google Maps listing, what Google Search and Google's AI answers say when you ask for its number, Bing Maps as a second opinion, and what reviewers report. Each engine below runs through SerpApi, and every response is saved with its search ID, so any finding can be traced back to the search behind it.</p>
            <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-3 [&>*]:min-w-0">
              {Object.entries(ENGINES).map(([id, e]) => (
                <div key={id} className="surface group flex flex-col rounded-[1.5rem] p-6 transition duration-500 ease-[var(--ease-out-expo)] hover:-translate-y-1 hover:shadow-[var(--shadow-float)]">
                  <div className="flex items-start justify-between">
                    <span className="grid size-11 place-items-center rounded-full bg-wash text-brand transition-transform duration-500 group-hover:rotate-[-8deg]"><e.icon className="size-5" aria-hidden /></span>
                    <span className="text-right"><span className="serif tnum block text-[2.4rem] leading-none tracking-[-0.03em]">{engines[id] ?? 0}</span><span className="text-[11px] text-muted">searches</span></span>
                  </div>
                  <p className="mt-5 text-lg font-semibold">{e.label}</p>
                  <Mono className="mt-1 w-fit rounded-md bg-paper-2 px-1.5 py-0.5 text-[11px] text-muted">{id}</Mono>
                  <p className="mt-3 text-[14.5px] leading-relaxed text-ink-2">{e.what}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-[66ch] text-sm text-muted">Re-running a saved search costs nothing. Every office page lists the ones behind it.</p>
          </Section>

          <Section id="score" title="The listing score">
            <p className={prose}>A single number for how reachable an office is from its Google Maps listing: six checks, weighted as below, out of 100. A check that can't be decided (say, the listing shows no number to compare, or the office's reviews weren't read) is left out rather than counted as a fail. It measures what a citizen finds on Google, not how good the office is.</p>
            {checks.length > 0 && (
              <div className="surface mt-7 max-w-3xl overflow-clip rounded-[1.5rem]">
                <table className="w-full border-separate border-spacing-0 text-[15px]">
                  <caption className="sr-only">The six checks and the points each is worth</caption>
                  <thead>
                    <tr className="text-xs font-medium text-muted">
                      <th scope="col" className="border-b border-rule px-5 py-3 text-left font-medium sm:px-6">Check</th>
                      <th scope="col" className="border-b border-rule py-3 pl-4 pr-5 text-right font-medium sm:pr-6">Points</th>
                    </tr>
                  </thead>
                  <tbody>
                    {checks.map((c) => (
                      <tr key={c.id}>
                        <td className="border-b border-rule/70 px-5 py-3 leading-snug text-ink sm:px-6">{c.label}</td>
                        <td className="border-b border-rule/70 py-3 pl-4 pr-5 sm:pr-6">
                          <span className="flex items-center justify-end gap-4">
                            {/* Each bar is the check's share of the 100 points. */}
                            <span className="hidden h-1 w-28 overflow-hidden rounded-full bg-paper-2 sm:block" aria-hidden>
                              <span className="block h-full rounded-full bg-brand/70" style={{ width: `${(100 * c.max_points) / total}%` }} />
                            </span>
                            <span className="tnum w-8 text-right font-semibold">{c.max_points}</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="bg-wash/60">
                      <th scope="row" className="px-5 py-3 text-left text-sm font-semibold sm:px-6">Points if every check passes</th>
                      <td className="tnum py-3 pl-4 pr-5 text-right font-semibold sm:pr-6">{total}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </Section>

          <Section id="reviews" title="Reading the reviews">
            <p className={prose}>
              A phrase list in English, Kannada, Hindi, Tamil and Telugu sorts each review into nine categories, and skips denials like "didn't have to pay any bribe".
              We tested it once on {method?.heldout_reviews ?? "…"} hand-labelled RTO reviews it had never seen. We also tried a small local AI model ({method?.model_name}), and kept the phrase list because its flags are more often right.
            </p>
            {method && (
              <div className="mt-8 grid gap-4 md:grid-cols-3">
                <Meter label="Phrase list" score={method.lexicon} strong />
                <Meter label={`${method.model_name}, run locally`} score={method.model} />
                <Meter label="Either of the two" score={method.union} />
              </div>
            )}
            <p className="mt-5 max-w-[66ch] text-sm leading-relaxed text-muted">Measured on RTO reviews only, so sub-registrar counts are untested. The labels are one labeller's reading. Shares need {rules?.min_sample ?? "…"} or more recent reviews with text; below that, offices say "too few".</p>
          </Section>

          <Section id="breaches" title="Possible breaches">
            <p className={prose}>A review from the last {rules ? rules.recent_days / 365 : "…"} years that reports a wait at least {rules?.breach_margin_pct ?? "…"}% past the legal limit, for a service named in the same sentence. Waits that went through an agent are set aside. It is one person's account, never a rate.</p>
          </Section>

          <Section id="privacy" title="Privacy">
            <div className="flex max-w-3xl gap-5 rounded-[1.5rem] bg-wash p-6">
              <span className="grid size-11 shrink-0 place-items-center rounded-full bg-card text-brand"><EyeOff className="size-5" aria-hidden /></span>
              <div className="space-y-3 text-[1.02rem] leading-relaxed text-ink-2">
                <p>No reviewer names or profiles are stored. Names of staff and agents, vehicle numbers, and any mobile number that isn't in an official directory are masked in every quote, and an automated test fails if one ever reaches a published file. This reports on offices, not individuals.</p>
                <p>Kal Aana keeps no record of your conversation: it stays in your browser tab. When a model writes the answers, your messages go to that model's API (on this site, Claude through Anthropic's API), and a live search sends a short query to SerpApi, whose results are kept on the server for an hour.</p>
              </div>
            </div>
          </Section>

          <Section id="build" title="Use it from code">
            <div className="grid gap-4 xl:grid-cols-2 [&>*]:min-w-0">
              <div className="surface rounded-[1.5rem] p-6">
                <p className="text-lg font-semibold">MCP server for AI assistants</p>
                <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">Connect an assistant such as Claude to the hosted server and it can answer "how do I reach this office?" with the official number and the evidence, instead of a guess. Nothing to install: add <Mono>https://kalaana-mcp.gradestone.in/mcp</Mono> as a custom connector, or run <Mono>kalaana-mcp</Mono> yourself.</p>
                <p className="mt-4 flex flex-wrap gap-1.5">{MCP_TOOLS.map((t) => <Mono key={t} className="rounded-md bg-wash px-2 py-0.5 text-[11.5px] text-brand">{t}</Mono>)}</p>
                <Code>{`# hosted
claude mcp add --transport http kal-aana https://kalaana-mcp.gradestone.in/mcp

# or locally
pip install -e ".[mcp]"
claude mcp add kal-aana -- .venv/bin/kalaana-mcp`}</Code>
                <p className="mt-3 text-xs leading-relaxed text-muted">Read-only. Ten tools answer offline from the saved snapshot and ask which office you mean rather than guess; the two live searches share the chat's rationed allowance (locally they need a SerpApi key).</p>
              </div>
              <div className="surface flex flex-col rounded-[1.5rem] p-6">
                <p className="text-lg font-semibold">JSON API and CLI</p>
                <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">Every page here is drawn from the same JSON: an overview, each office, its complaint letter, and the chat's stream. The <Mono>kalaana</Mono> command collects, scores and rebuilds the data.</p>
                <p className="mt-auto flex flex-wrap gap-2 pt-5 text-sm">
                  <a className="inline-flex items-center rounded-full bg-brand px-4 py-2 font-semibold text-paper transition hover:brightness-110" href={apiUrl("/api/docs")}>API docs</a>
                  <a className="inline-flex items-center rounded-full border border-rule px-4 py-2 font-semibold transition hover:border-ink-2" href={apiUrl("/api/snapshot")}>Download the data</a>
                  <a className="inline-flex items-center rounded-full border border-rule px-4 py-2 font-semibold transition hover:border-ink-2" href="https://github.com/tahcin/kal-aana">GitHub</a>
                </p>
              </div>
            </div>
          </Section>

          <Section id="chat" title="The chat">
            <div className="space-y-4">
              <p className={prose}>
                You describe the problem in your own words, and the answer is built from the saved data, plus a live search when the data
                doesn't cover it. With a model reader (any OpenAI-compatible API; this site runs Claude Sonnet 5.5), the model works as an agent over ten tools: find the office, its numbers,
                Google's AI answers, your wait against the limit, reviews, a complaint letter, a report card, the usual busy hours, and
                rationed live SerpApi searches of government sites and Google News.
              </p>
              <p className={prose}>
                Each tool returns a card drawn from the snapshot, so the numbers, quotes and phones on the cards come from the saved data or
                a cited live result (the model only passes along the date and application number you gave). The model writes only the
                sentences between cards, and a guard withholds any number in them that no tool returned, including a phone number typed
                into the chat. The tools accept only services and offices in the data.
              </p>
              <p className={prose}>
                Without a key, or once its spending cap is reached, tested rules choose the same cards. A local model can read the message
                instead, with every field it returns checked against the data. Every reply says which reader answered.
              </p>
            </div>
            <div className="mt-8 grid gap-3 sm:grid-cols-2">
              {[
                ["Any OpenAI-compatible API (the full agent)", "KALAANA_READER=openai OPENAI_BASE_URL=... OPENAI_API_KEY=... KALAANA_MODEL=... kalaana serve"],
                ["A local model with tools (Ollama)", "KALAANA_READER=openai OPENAI_BASE_URL=http://localhost:11434/v1 KALAANA_MODEL=... kalaana serve"],
                ["Claude with prompt caching", 'pip install -e ".[claude]"\nKALAANA_READER=anthropic ANTHROPIC_API_KEY=... kalaana serve'],
                ["A local field reader only", "KALAANA_READER=ollama KALAANA_MODEL=gemma3:4b kalaana serve"],
              ].map(([title, cmd]) => (
                <div key={title} className="rounded-[1.5rem] border border-rule p-5">
                  <p className="font-semibold">{title}</p>
                  <Code>{cmd}</Code>
                </div>
              ))}
            </div>
          </Section>

          <Section id="scale" title="From one city to all of India">
            <p className={prose}>
              Nothing here is tied to Bengaluru: a new city is a <Mono>CITIES</Mono> entry and the department's directory, Karnataka's other
              cities reuse the Sakala time limits, and the passport Citizen's Charter is national. At the pilot's 10.5 searches per office,
              mostly Maps Reviews, a national sweep is about 80,000 searches. The harder part is collecting each state's directories and Right
              to Services time limits, not the searches.
            </p>
            <div className="surface mt-7 max-w-3xl overflow-x-auto rounded-[1.5rem]">
              <table className="w-full border-separate border-spacing-0 text-[15px]">
                <caption className="sr-only">Estimated searches and cost for a national sweep</caption>
                <thead>
                  <tr className="text-xs font-medium text-muted">
                    <th scope="col" className="border-b border-rule px-5 py-3 text-left font-medium sm:px-6">Scope</th>
                    <th scope="col" className="border-b border-rule px-4 py-3 text-right font-medium">Offices, approx.</th>
                    <th scope="col" className="border-b border-rule px-4 py-3 text-right font-medium">Searches</th>
                    <th scope="col" className="border-b border-rule py-3 pl-4 pr-5 text-right font-medium sm:pr-6">Cost, roughly</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Bengaluru pilot (measured)", "60", "628", "$6 to $9 at those rates (done on free credits)"],
                    ["RTOs and passport offices, all of India", "2,000", "21,000", "$250 to $350"],
                    ["RTOs, sub-registrars and passport offices, all of India", "7,000 to 8,000", "80,000", "$1,000"],
                  ].map(([scope, offices, searches, cost]) => (
                    <tr key={scope}>
                      <th scope="row" className="border-b border-rule/70 px-5 py-3 text-left font-normal leading-snug text-ink sm:px-6">{scope}</th>
                      <td className="tnum border-b border-rule/70 px-4 py-3 text-right">{offices}</td>
                      <td className="tnum border-b border-rule/70 px-4 py-3 text-right">{searches}</td>
                      <td className="tnum border-b border-rule/70 py-3 pl-4 pr-5 text-right sm:pr-6">{cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-5 max-w-[66ch] text-sm leading-relaxed text-muted">Office counts are rough estimates. Costs assume SerpApi's published plans at the time of writing (about one to one and a half US cents a search at volume); check current prices. Reading fewer reviews per office could cut a sweep roughly in half.</p>
          </Section>

          <Section id="limits" title="Limits">
            <ol className="max-w-[66ch] space-y-6">
              {[
                "Reviews are self-selected: people with a bad experience write more of them.",
                `Google's AI answers change from day to day. These are what it said on ${overview?.totals.as_of ?? "…"}, for the exact search shown.`,
                "Not finding a listing isn't proof there is none. Directories go out of date, so \"not in the directory\" means exactly that.",
                "A few offices have gaps, and say so: RTO Chandapura and the BDA office have no Google Maps listing that our searches found, and Halasooru's Google search failed three times, so it says \"not checked\".",
              ].map((text, i) => (
                <li key={i} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-2">
                  <span className="mt-[0.6em] size-1.5 rounded-full bg-pop" aria-hidden />
                  <p className="text-[1.05rem] leading-relaxed text-ink-2">{text}</p>
                </li>
              ))}
            </ol>
            <p className="mt-10 flex flex-wrap gap-2 text-sm">
              <Link className="inline-flex items-center rounded-full bg-brand px-4 py-2 font-semibold text-paper transition hover:brightness-110" to="/offices">See every office</Link>
            </p>
          </Section>
        </div>
      </div>
      <Footer asOf={overview?.totals.as_of} searches={overview?.totals.searches} />
    </main>
  );
}
