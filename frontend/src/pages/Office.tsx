// One office's evidence file: what the department promises against what a citizen finds on Google, then each finding
// in its own chapter with the searches behind it.
import { motion, useInView, useReducedMotion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, MapPin, Minus, RotateCcw, X } from "lucide-react";
import { useRef, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { Chip, Mono, Provenance, Reveal } from "../components/bits";
import { Footer } from "../components/Shell";
import { SearchId } from "../components/explain";
import { IssueChart, MapsCard, NumberChecks, PromiseClock, PullQuote, SearchReplay, panel } from "../components/story";
import { useJSON, type Engine, type OfficeDetail, type Step } from "../lib/api";
import NotFound from "./NotFound";
import { AI, MAPS, VERDICT, cn, safeUrl, type Tone } from "../lib/ui";
import { ENGINE, useMedia } from "../lib/explain";
import { useTitle } from "../lib/useTitle";
import "../styles/evidence.css";

const ease = [0.16, 1, 0.3, 1] as const;

function InView({ children }: { children: (active: boolean) => ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const active = useInView(ref, { once: true, amount: 0.35 });
  return <div ref={ref}>{children(active)}</div>;
}

const ENGINES = [
  { id: "google_maps", label: "Google Maps", what: "finds the office's listing" },
  { id: "google_maps_reviews", label: "Maps Reviews", what: "reads what citizens report" },
  { id: "google", label: "Google Search", what: "sees what a citizen sees" },
  { id: "google_ai_overview", label: "AI Overview", what: "checks what Google's AI says" },
  { id: "google_ai_mode", label: "AI Mode", what: "asks Google's other AI" },
  { id: "bing_maps", label: "Bing Maps", what: "checks outside Google" },
] as const;

/** The SerpApi engines feeding one page, with this office's search count on each line. Phones get a plain list. */
function EngineDiagram({ steps }: { steps: Step[] }) {
  const ref = useRef<SVGSVGElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const reduce = useReducedMotion();
  const wide = useMedia("(min-width: 640px)");
  const count = (id: string) => steps.filter((s) => s.engine === id).length;
  if (!wide) {
    return (
      <ul className="grid grid-cols-2 gap-2">
        {ENGINES.map((e) => (
          <li key={e.id} className={cn(panel, "rounded-2xl px-4 py-3")}>
            <p className={cn("serif text-3xl leading-none", count(e.id) ? "text-brand" : "text-muted")}><span className="tnum">{count(e.id)}</span></p>
            <p className="mt-1.5 text-sm font-semibold">{e.label}</p>
            <p className="text-xs text-muted">{e.what}</p>
          </li>
        ))}
      </ul>
    );
  }
  const gap = 62, W = 760, H = 80 + (ENGINES.length - 1) * gap, cx = 610, cy = H / 2;
  return (
    <svg ref={ref} viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={ENGINES.map((e) => `${e.label}: ${count(e.id)} searches`).join(", ")}>
      <defs>
        <linearGradient id="hub" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="var(--color-brand)" /><stop offset="1" stopColor="var(--color-brand-2)" /></linearGradient>
      </defs>
      {ENGINES.map((e, i) => {
        const y = 40 + i * gap;
        const path = `M 244 ${y} C 410 ${y}, 430 ${cy}, ${cx - 72} ${cy}`;
        const n = count(e.id);
        return (
          <g key={e.id}>
            <motion.path d={path} fill="none" stroke={n ? "var(--color-brand)" : "var(--color-rule)"} strokeOpacity={n ? 0.35 : 1} strokeWidth={n ? 2.5 : 1.5}
              strokeDasharray={n ? undefined : "4 6"} strokeLinecap="round"
              initial={reduce ? false : { pathLength: 0 }} animate={inView ? { pathLength: 1 } : {}} transition={{ duration: 1.1, delay: 0.15 * i, ease }} />
            {n > 0 && !reduce && (
              <motion.circle r="4" fill="var(--color-pop)" initial={{ offsetDistance: "0%" }}
                animate={inView ? { offsetDistance: ["0%", "100%"] } : {}} style={{ offsetPath: `path("${path}")` }}
                transition={{ duration: 2.2, delay: 1 + 0.25 * i, repeat: Infinity, repeatDelay: 1.2, ease: "easeInOut" }} />
            )}
            <rect x="10" y={y - 27} width="234" height="54" rx="14" fill="var(--color-card)" stroke="var(--color-rule)" />
            <text x="28" y={y - 4} className="fill-ink text-[15px] font-semibold">{e.label}</text>
            <text x="28" y={y + 15} className="fill-muted text-[12px]">{e.what}</text>
            <text x="226" y={y + 7} textAnchor="end" className={cn("font-serif text-[24px]", n ? "fill-brand" : "fill-muted")}>{n}</text>
          </g>
        );
      })}
      <rect x={cx - 72} y={cy - 52} width="144" height="104" rx="22" fill="url(#hub)" />
      <text x={cx} y={cy - 6} textAnchor="middle" className="fill-card font-serif text-[20px]">This page</text>
      <text x={cx} y={cy + 18} textAnchor="middle" className="fill-card font-mono text-[12px] opacity-80">{steps.length} searches</text>
    </svg>
  );
}

/** Every search behind the page, printed like a till receipt: engine, purpose, time and search ID. */
function Receipts({ trail, asOf }: { trail: Step[]; asOf: string }) {
  return (
    <div className="receipt px-6 py-9 font-mono text-[12px] text-ink-2">
      <p className="text-center text-[13px] font-semibold text-ink">Search receipts</p>
      <p className="mt-1 text-center text-[11px] text-muted">{trail.length} searches · data as of {asOf}</p>
      <ol className="mt-5 max-h-[460px] space-y-0 overflow-y-auto border-y border-dashed border-rule pr-3">
        {trail.map((s, i) => (
          <li key={s.search_id + i} className="border-b border-dashed border-rule py-3 last:border-b-0">
            <p className="flex flex-wrap justify-between gap-x-3 text-[11px]">
              <span className="font-semibold text-brand">{ENGINE[s.engine as Engine]?.name ?? s.engine}</span>
              <span className="text-muted">{s.searched_at}</span>
            </p>
            <p className="mt-1 font-sans text-[13px] leading-snug text-ink">{s.purpose}</p>
            {s.search_id ? <SearchId className="mt-2" engine={s.engine as Engine} id={s.search_id} /> : <p className="mt-1 text-[11px] text-muted">id not recorded</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}

/** A small receipt beside the title on wide screens: what this page is built from, at a glance. */
function FileStub({ data, trail }: { data: OfficeDetail; trail: Step[] }) {
  const o = data.office;
  const rows: [string, ReactNode][] = [
    ["Searches", trail.length],
    ["Engines", new Set(trail.map((s) => s.engine)).size],
    ["Numbers published", o.official_phones.length],
    ["Listing score", o.reach.score === null ? "n/a" : `${o.reach.score}/100`],
    ["Reviews read", o.sampled ? o.sample_size : "not sampled"],
  ];
  return (
    <Reveal delay={0.2} className="hidden xl:block">
      <div className="receipt rotate-[2deg] px-6 py-8 font-mono text-[11px] text-ink-2 transition-transform duration-700 ease-[var(--ease-out-expo)] hover:rotate-0">
        <p className="text-center text-[13px] font-semibold text-ink">Evidence file</p>
        <p className="mt-1 text-center text-muted">{o.code || data.profile.short}</p>
        <dl className="mt-4 space-y-2 border-y border-dashed border-rule py-4">
          {rows.map(([k, v]) => <div key={k} className="flex justify-between gap-3"><dt className="text-muted">{k}</dt><dd className="font-semibold text-ink">{v}</dd></div>)}
        </dl>
        <p className="mt-3 text-center text-muted">Data as of {data.as_of}</p>
        <a href="#how" className="mt-2 block text-center font-semibold text-brand underline decoration-brand/30 underline-offset-2">See every receipt</a>
      </div>
    </Reveal>
  );
}

/** A chapter of the evidence file: a hairline and a serif heading. The findings are said once, at the top. */
function Chapter({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="mx-auto mt-24 max-w-7xl scroll-mt-24 px-4 sm:mt-36 sm:px-6">
      <Reveal className="border-t border-ink/70 pt-6">
        <h2 id={`${id}-h`} className="display text-[clamp(2.1rem,4.6vw,3.6rem)]">{title}</h2>
      </Reveal>
      <div className="mt-10 sm:mt-12">{children}</div>
    </section>
  );
}

const worst = (tones: Tone[]): Tone => tones.includes("broken") ? "broken" : tones.includes("amber") ? "amber" : tones.every((t) => t === "kept") ? "kept" : "unknown";

/** One line of "what Google shows": where a citizen looks, the number they get (or a gap), and the verdict. */
function RealityRow({ where, value, tone, children }: { where: string; value: string | null | undefined; tone: Tone; children: ReactNode }) {
  return (
    <div className="grid gap-2 border-t border-rule/80 py-4 first:border-t-0 first:pt-0 last:pb-0">
      <dt className="text-sm text-muted">{where}</dt>
      <dd className="flex flex-wrap items-center gap-x-3 gap-y-2">
        {value ? <Mono className={cn("text-2xl font-semibold sm:text-[1.75rem]", { kept: "text-kept", broken: "text-broken", amber: "text-amber", unknown: "text-ink" }[tone])}>{value}</Mono>
          : <span className="rounded-lg border border-dashed border-current/30 px-2.5 py-0.5 font-mono text-lg text-muted" aria-label="No number">· · ·</span>}
        {children}
      </dd>
    </div>
  );
}

function PromiseVsReality({ data }: { data: OfficeDetail }) {
  const { office: o, card } = data;
  const aiSaid = card.found.find((f) => f.where === "Google's AI Overview");
  const bingTone: Tone | null = !card.bing ? null : !card.bing.found ? "unknown" : !card.bing.phone_display ? "broken" : card.bing.phone_verdict === "this office" ? "kept" : "amber";
  const tones = [MAPS[data.maps].tone, AI[data.ai].tone, AI[data.mode].tone, ...(bingTone ? [bingTone] : [])].filter((t) => t !== "unknown");
  const verdict = worst(tones);
  const same = verdict === "kept";
  const [first, ...rest] = o.official_phones;
  return (
    <section className="mx-auto mt-12 max-w-7xl px-4 sm:mt-16 sm:px-6" aria-label="What the department promises, and what Google shows">
      <Reveal className="relative grid lg:grid-cols-2">
        {/* The promise: what the department itself publishes. */}
        <div className="relative overflow-hidden rounded-[var(--radius-panel)] border border-rule bg-gradient-to-br from-wash via-card to-card p-7 pb-12 sm:p-10 sm:pb-14 lg:rounded-r-none lg:pb-10 lg:border-r-0">
          <h2 className="serif text-[1.75rem] leading-tight tracking-[-0.02em] text-brand">The promise</h2>
          <p className="mt-1 text-sm text-muted">Published by the {data.profile.department}</p>
          {first && (
            <a href={`tel:${first.tel}`} className="group mt-8 block">
              <Mono className="block text-[clamp(2rem,4.4vw,3.25rem)] font-semibold leading-none text-ink transition group-hover:text-brand">{first.display}</Mono>
              <span className="mt-2 block text-xs text-muted">{first.label}</span>
            </a>
          )}
          {rest.length > 0 && (
            <ul className="mt-5 grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {rest.map((p) => <li key={p.tel}><a href={`tel:${p.tel}`} className="group flex flex-col"><Mono className="text-lg font-semibold transition group-hover:text-brand">{p.display}</Mono><span className="text-xs text-muted">{p.label}</span></a></li>)}
            </ul>
          )}
          {o.email && <a className="mt-4 inline-block text-sm text-ink-2 underline decoration-current/30 underline-offset-4 hover:text-brand" href={`mailto:${o.email}`}>{o.email}</a>}
          {o.notes.length > 0 && <ul className="mt-3 space-y-1 text-xs text-muted">{o.notes.map((n) => <li key={n}>{n}</li>)}</ul>}

          <div className="mt-9 border-t border-dashed border-rule pt-7">
            <p className="text-sm text-muted">{card.clock.service}</p>
            <p className="serif mt-1 text-[clamp(2.75rem,5.5vw,4.25rem)] leading-none tracking-[-0.03em] text-ink">{card.clock.limit}</p>
            {card.clock.terms && <p className="mt-2 text-sm text-muted">Counted {card.clock.terms}.</p>}
            {data.appeals && <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-2">Late? Appeal to the {data.appeals.first_appeal}, then the {data.appeals.second_appeal}.</p>}
            {!data.appeals && data.grievance && (
              <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-2">
                Late? The charter has no appeal ladder; raise it through the Passport Seva grievance channels
                ({data.grievance.portals.map((u, i) => <span key={u}>{i > 0 && ", "}<a className="underline decoration-current/30 underline-offset-2 hover:text-brand" href={safeUrl(u)}>{u.replace(/^https?:\/\//, "")}</a></span>)})
                {data.grievance.email && <> or email the ministry's central grievance address, {data.grievance.email}</>}.
              </p>
            )}
          </div>
          <Provenance>
            {safeUrl(o.source_url) && <a href={safeUrl(o.source_url)}>The department's directory</a>}
            {safeUrl(card.clock.citation) && <a href={safeUrl(card.clock.citation)}>{card.promise.name}</a>}
          </Provenance>
        </div>

        {/* The meeting point: "=" only when every channel checked shows the office's own number. */}
        <div className="relative z-10 -my-7 flex justify-center lg:absolute lg:inset-y-0 lg:left-1/2 lg:my-0 lg:-translate-x-1/2 lg:items-center" aria-hidden>
          <motion.span initial={{ scale: 0.6, rotate: -20, opacity: 0 }} whileInView={{ scale: 1, rotate: 0, opacity: 1 }} viewport={{ once: true }}
            transition={{ type: "spring", stiffness: 260, damping: 16, delay: 0.4 }}
            className={cn("serif grid size-16 place-items-center rounded-full pb-1 text-[2.6rem] leading-none text-card shadow-[var(--shadow-float)] ring-8 ring-paper sm:size-20 sm:text-5xl",
              same ? "bg-kept" : "bg-gradient-to-br from-ink to-brand")}>
            {same ? "=" : "≠"}
          </motion.span>
        </div>

        {/* The reality: what a citizen finds. */}
        <div className={cn("rounded-[var(--radius-panel)] border p-7 pt-12 sm:p-10 sm:pt-14 lg:rounded-l-none lg:pl-14 lg:pt-10",
          verdict === "broken" ? "border-broken/25 bg-gradient-to-bl from-broken-soft/80 to-card" : verdict === "amber" ? "border-amber/25 bg-gradient-to-bl from-amber-soft/80 to-card" : "border-kept/25 bg-gradient-to-bl from-kept-soft/80 to-card")}>
          <h2 className={cn("serif text-[1.75rem] leading-tight tracking-[-0.02em]", { broken: "text-broken", amber: "text-amber", kept: "text-kept", unknown: "text-ink" }[verdict])}>The reality</h2>
          <p className="mt-1 text-sm text-muted">What a citizen finds on Google and Bing</p>
          <dl className="mt-8">
            <RealityRow where="Its Google Maps listing" value={o.listing?.phone_display} tone={MAPS[data.maps].tone}>
              <Chip tone={MAPS[data.maps].tone}>{MAPS[data.maps].label}</Chip>
              {o.listing?.unclaimed && <Chip tone="amber">Unclaimed</Chip>}
            </RealityRow>
            <RealityRow where="Google's AI Overview, asked for its number" value={aiSaid?.display} tone={AI[data.ai].tone}>
              <Chip tone={AI[data.ai].tone}>{AI[data.ai].label}</Chip>
              {card.ai?.address_matches === false && <Chip tone="broken">Address with a different PIN</Chip>}
            </RealityRow>
            <RealityRow where="Google's AI Mode, asked the same thing" value={card.mode?.first_display} tone={AI[data.mode].tone}>
              <Chip tone={AI[data.mode].tone}>{AI[data.mode].label}</Chip>
            </RealityRow>
            {card.bing && bingTone && (
              <RealityRow where="The same office on Bing Maps" value={card.bing.phone_display || null} tone={bingTone}>
                <Chip tone={bingTone}>{!card.bing.found ? "Couldn't match a place" : !card.bing.phone_display ? "No phone" : VERDICT[card.bing.phone_verdict!].label}</Chip>
              </RealityRow>
            )}
            <div className="grid gap-2 border-t border-rule/80 pt-4">
              <dt className="text-sm text-muted">Its recent Google reviews</dt>
              <dd>
                {!o.sampled ? <Chip tone="unknown">Not sampled</Chip> : o.enough_evidence
                  ? <p className="flex flex-wrap items-baseline gap-x-2"><span className="serif text-4xl leading-none tracking-[-0.02em]"><span className="tnum">{o.problem_reviews}</span><span className="text-muted"> of {o.window_reviews}</span></span><span className="text-ink-2">report a problem</span></p>
                  : <Chip tone="unknown">Too few to count ({o.window_reviews})</Chip>}
              </dd>
            </div>
          </dl>
        </div>
      </Reveal>
    </section>
  );
}

/** The listing score as one bar split by each check's weight: earned, missed, or left out. */
function ListingScore({ reach }: { reach: OfficeDetail["office"]["reach"] }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const reduce = useReducedMotion();
  return (
    <div className={cn(panel, "p-6 sm:p-8")}>
      <p className="text-xs font-medium text-muted">Listing score</p>
      <p className="serif mt-2 text-7xl leading-none tracking-[-0.04em]">{reach.score ?? "n/a"}{reach.score !== null && <span className="text-3xl text-muted">/100</span>}</p>
      <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted">Six checks of the Google Maps listing ({reach.basis}). It measures what citizens find on Google, not the quality of the office.</p>
      <div ref={ref} className="mt-6 flex h-3 gap-1" aria-hidden>
        {reach.checks.map((c, i) => (
          <span key={c.id} className={cn("relative overflow-hidden rounded-full", c.passed === null ? "border border-dashed border-rule" : "bg-paper-2")} style={{ flexGrow: c.max_points }}>
            {c.passed && <motion.span className="absolute inset-0 origin-left rounded-full bg-kept" initial={reduce ? false : { scaleX: 0 }} animate={inView ? { scaleX: 1 } : {}} transition={{ delay: 0.1 * i, duration: 0.8, ease }} />}
            {c.passed === false && <span className="absolute inset-0 rounded-full bg-broken/25" />}
          </span>
        ))}
      </div>
      <table className="mt-6 w-full border-separate border-spacing-0">
        <caption className="sr-only">Each check, and the points it earned</caption>
        <thead>
          <tr className="text-xs text-muted">
            <th scope="col" className="border-b border-rule pb-2.5 text-left font-medium" colSpan={2}>Check</th>
            <th scope="col" className="border-b border-rule pb-2.5 pl-4 text-right font-medium">Points</th>
          </tr>
        </thead>
        <tbody>
          {reach.checks.map((c) => (
            <tr key={c.id} className="align-top [&>td]:border-b [&>td]:border-rule/70 [&>td]:py-3.5 last:[&>td]:border-b-0 last:[&>td]:pb-0">
              <td className="w-9 pr-3">
                <span className={cn("mt-px grid size-6 place-items-center rounded-full", c.passed ? "bg-kept-soft text-kept" : c.passed === null ? "bg-unknown-soft text-muted" : "bg-broken-soft text-broken")}>
                  {c.passed ? <Check className="size-3.5" aria-label="Passed" /> : c.passed === null ? <Minus className="size-3.5" aria-label="Left out" /> : <X className="size-3.5" aria-label="Failed" />}
                </span>
              </td>
              <td><p className="font-semibold leading-snug">{c.label}</p><p className="mt-0.5 text-sm leading-snug text-muted">{c.detail}</p></td>
              <td className="whitespace-nowrap pl-4 text-right">
                {c.passed === null ? <span className="text-sm text-muted">Left out</span>
                  : <span className="tnum font-semibold leading-snug">{c.points}<span className="font-normal text-muted"> / {c.max_points}</span></span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReviewsChapter({ data }: { data: OfficeDetail }) {
  const o = data.office;
  const quoted = [...o.issues.filter((i) => i.polarity === "problem"), ...o.issues.filter((i) => i.polarity !== "problem")].filter((i) => i.quotes.length);
  const problems = quoted.filter((i) => i.polarity === "problem");
  // The counts cover only reviews from the issue window before the data date; quotes from before it are shown but not counted.
  const counted = new Date(Date.parse(data.as_of) - data.rules.issue_window_days * 864e5).toISOString().slice(0, 10);
  return (
    <Chapter id="reviews" title="What reviewers report">
      {!o.sampled ? <p className="serif max-w-2xl text-xl text-muted">Not sampled: within the free plan, reviews were read for the most-reviewed offices only.</p> : (
        <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-14 [&>*]:min-w-0">
          <div>
            <div className={cn(panel, "p-6 sm:p-7 lg:sticky lg:top-24")}>
              {o.span && <p className="text-sm leading-relaxed text-muted">Newest {o.sample_size} reviews, <span className="whitespace-nowrap">{o.span[0]}</span> to <span className="whitespace-nowrap">{o.span[1]}</span>; {o.window_reviews} have text and are from the last year.{!o.enough_evidence && " Too few to count shares: these quotes are evidence, not a measure."}</p>}
              {o.enough_evidence && <IssueChart className="mt-6" issues={o.issues} of={o.window_reviews} />}
              <p className="mt-6 border-t border-dashed border-rule pt-4 text-xs leading-relaxed text-muted">Reviews are self-selected: each is one person's account, not a rate. Names and unverified mobile numbers are masked; this reports on the office, not individuals. Quotes marked "found by searching" or "older" are not in the counts: they come from a review search, or from before the last year.</p>
            </div>
          </div>
          <div>
            {problems.length === 0 && (
              <p className="serif mb-10 max-w-2xl text-xl leading-snug text-ink-2">We have no problem quotes to show for this office. That is not a clean bill of health: reviews are self-selected, and we read only the newest ones.</p>
            )}
            <div className="grid gap-x-10 gap-y-12 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {quoted.map((i, n) => {
                const q = i.quotes[0];
                const bad = i.polarity === "problem";
                return (
                  <Reveal key={i.category} delay={0.05 * (n % 2)}>
                    <p className={cn("mb-3 flex items-baseline justify-between gap-3 text-xs font-medium", bad ? "text-broken" : "text-kept")}>
                      <span>{i.label}</span>{o.enough_evidence && i.count > 0 && <span className="tnum shrink-0 text-xs font-normal text-muted">{i.count} of {i.of}</span>}
                    </p>
                    <PullQuote tone={bad ? "broken" : "kept"} text={q.text} evidence={q.evidence} size="lg"
                      caption={<>{q.rating ? `${q.rating}★ · ` : ""}{q.date}{q.sample !== "newest" && ` · found by searching "${q.sample.slice(6)}"`}{q.date < counted && " · older, not counted"}</>}
                      links={safeUrl(q.link) && <a href={safeUrl(q.link)}>on Google</a>} />
                  </Reveal>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </Chapter>
  );
}

const CHAPTERS = [["search", "Search"], ["listing", "Listing"], ["reviews", "Reviews"], ["how", "How we know"]] as const;

export default function Office() {
  const { id = "rto-ka05" } = useParams();
  return <OfficeView key={id} id={id} />;  // a new office starts at the top, with its own animations
}

function OfficeView({ id }: { id: string }) {
  const reduce = useReducedMotion();
  const { data, error } = useJSON<OfficeDetail>(`/api/office/${encodeURIComponent(id)}`);
  useTitle(data?.card.label ?? "Office");
  if (error) return error.startsWith("404") ? <NotFound /> : <LoadError message={error} />;
  if (!data) return <Skeleton />;
  const { office: o, card } = data;
  const trail = [...data.sweep, ...o.trail];

  return (
    <main>
      <section className="relative overflow-x-clip">
        {/* A soft jacaranda bloom behind the title: decoration only. */}
        <div aria-hidden className="pointer-events-none absolute -right-40 -top-40 size-[38rem] rounded-full bg-[radial-gradient(closest-side,color-mix(in_srgb,var(--color-brand)_16%,transparent),transparent)]" />
        <div aria-hidden className="pointer-events-none absolute right-[18%] top-24 size-40 rounded-full bg-[radial-gradient(closest-side,color-mix(in_srgb,var(--color-pop)_22%,transparent),transparent)]" />
        <div className="relative mx-auto max-w-7xl px-4 pt-8 sm:px-6 sm:pt-12">
          <Link to="/offices" className="group inline-flex items-center gap-1.5 text-sm font-medium text-muted transition hover:text-brand">
            <ArrowLeft className="size-4 transition-transform group-hover:-translate-x-0.5" aria-hidden />Every office
          </Link>
          <div className="mt-10 grid items-start gap-10 sm:mt-14 xl:grid-cols-[minmax(0,1fr)_15rem]">
            <div>
              <Reveal><h1 className="display max-w-[17ch] text-[clamp(2.6rem,7.2vw,6.25rem)] leading-[0.98]">{card.label}</h1></Reveal>
              {o.address && (
                <Reveal delay={0.1}><p className="mt-6 flex max-w-xl items-start gap-2 text-sm leading-relaxed text-muted"><MapPin className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden />{o.address}</p></Reveal>
              )}
            </div>
            <FileStub data={data} trail={trail} />
          </div>
          <ul className="mt-12 grid gap-3 sm:mt-14 md:grid-cols-[repeat(var(--n),minmax(0,1fr))]" style={{ "--n": Math.min(card.verdict.length, 3) } as React.CSSProperties} aria-label="The findings">
            {card.verdict.map((line, i) => (
              <motion.li key={line} initial={reduce ? false : { opacity: 0, y: 18, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ delay: 0.25 + 0.12 * i, duration: 0.8, ease }}
                className={cn(panel, "rounded-3xl p-6 sm:p-7")}>
                <p className="serif text-[1.3rem] leading-snug text-ink sm:text-[1.45rem]">{line}</p>
              </motion.li>
            ))}
          </ul>
        </div>
      </section>

      <PromiseVsReality data={data} />

      <section className="mx-auto mt-4 max-w-7xl px-4 sm:px-6">
        <InView>{(active) => <PromiseClock card={card} active={active} />}</InView>
      </section>

      {data.lookalikes.length > 0 && (
        <section className="mx-auto mt-4 max-w-7xl px-4 sm:px-6">
          <Reveal className="rounded-[var(--radius-panel)] border border-amber/30 bg-gradient-to-br from-amber-soft/70 to-card p-7 sm:p-10">
            <h2 className="serif text-[1.75rem] leading-tight tracking-[-0.02em] text-amber">Named like a {data.profile.short}, but not on the official list</h2>
            <p className="serif mt-3 max-w-3xl text-xl leading-snug text-ink-2">
              {data.lookalikes_total} Google Maps listings in Bengaluru are named like a {data.profile.short} but aren't among the official offices listed above.
              The nearest to this one:
            </p>
            <ul className="mt-6 grid gap-3 sm:grid-cols-2">
              {data.lookalikes.map((l) => (
                <li key={l.title + l.pincode} className="rounded-2xl border border-amber/20 bg-card px-5 py-4 text-sm">
                  <b className="block font-semibold">"{l.title}"</b>
                  <span className="text-muted">Google lists it as {l.category || "no category"} · PIN {l.pincode}{l.km !== null && ` · ${l.km} km away`}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-muted">We don't show their phone numbers.</p>
          </Reveal>
        </section>
      )}

      <nav aria-label="Chapters" className="mx-auto mt-20 max-w-7xl px-4 sm:px-6">
        <ul className="flex flex-wrap gap-2">
          {CHAPTERS.map(([href, label]) => (
            <li key={href}><a href={`#${href}`} className="group inline-flex items-center gap-2 rounded-full border border-rule bg-card px-4 py-2 text-sm font-medium text-ink-2 transition hover:-translate-y-0.5 hover:border-brand hover:text-brand">
              {label}</a></li>
          ))}
        </ul>
      </nav>

      <Chapter id="search" title="What a citizen sees on Google">
        <div className="grid gap-6 lg:grid-cols-2 [&>*]:min-w-0">
          <SearchReplay card={card} active />
          <div className="lg:sticky lg:top-24 lg:self-start">
            <p className="mb-4 text-xs font-medium text-muted">Every number up front, checked</p>
            <InView>{(active) => <NumberChecks card={card} active={active} />}</InView>
          </div>
        </div>
      </Chapter>

      <Chapter id="listing" title="The listing, checked">
        <div className="grid gap-6 lg:grid-cols-2 lg:items-start [&>*]:min-w-0">
          <MapsCard card={card} />
          <ListingScore reach={o.reach} />
        </div>
      </Chapter>

      <ReviewsChapter data={data} />

      <Chapter id="how" title="How we know">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-14 [&>*]:min-w-0">
          <div>
            <EngineDiagram steps={trail} />
            <p className="mt-6 max-w-2xl text-sm leading-relaxed text-muted">Each search ran once through SerpApi and was saved. {data.sweep.length} were city-wide sweeps shared by all {data.profile.plural}.</p>
            <Link to="/method" className="group mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand">The full method <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden /></Link>
          </div>
          <Receipts trail={trail} asOf={data.as_of} />
        </div>
      </Chapter>

      <section className="mx-auto mt-24 max-w-7xl px-4 sm:mt-32 sm:px-6">
        <Reveal className="relative overflow-hidden rounded-[var(--radius-panel)] bg-gradient-to-br from-[#1c1530] via-[#261a47] to-[#5a3fc0] p-8 text-[#fffdf9] ring-1 ring-white/10 sm:p-14">
          <div aria-hidden className="pointer-events-none absolute -bottom-24 -right-16 size-72 rounded-full bg-[radial-gradient(closest-side,color-mix(in_srgb,var(--color-pop)_55%,transparent),transparent)]" />
          <p className="display relative max-w-[20ch] text-[clamp(2rem,4.4vw,3.5rem)]">Application late? Kal Aana counts the working days and drafts the letter.</p>
          <p className="relative mt-4 max-w-xl text-white/75">You fill in your details and send it yourself. Kal Aana sends nothing.</p>
          <div className="relative mt-8 flex flex-wrap gap-3">
            <Link to={`/#ask=${encodeURIComponent(`My application at ${card.label} is late. I applied on `)}`}
              className="group inline-flex items-center gap-2 rounded-full bg-[#ffb31a] px-5 py-3 font-semibold text-[#1c1530] shadow-[var(--shadow-float)] transition hover:-translate-y-0.5">
              Draft a complaint about a late service <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
            </Link>
            <Link to={`/?office=${encodeURIComponent(o.id)}`} className="inline-flex items-center gap-2 rounded-full border border-white/30 px-5 py-3 font-semibold transition hover:border-white hover:bg-white/10">Ask Kal Aana about this office</Link>
          </div>
        </Reveal>
      </section>
      <Footer asOf={data.as_of} />
    </main>
  );
}

/** The page's shape while the office loads, so nothing jumps when it arrives. */
function Skeleton() {
  return (
    <main className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 sm:pt-12" aria-busy="true">
      <p className="sr-only" role="status">Loading this office's evidence</p>
      <div aria-hidden>
        <div className="skeleton h-4 w-28 rounded-full" />
        <div className="skeleton mt-14 h-3 w-72 max-w-full rounded-full" />
        <div className="skeleton mt-6 h-[clamp(2.4rem,6vw,5.5rem)] w-[80%] rounded-2xl" />
        <div className="skeleton mt-3 h-[clamp(2.4rem,6vw,5.5rem)] w-[55%] rounded-2xl" />
        <div className="mt-14 grid gap-3 md:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-40 rounded-3xl" />)}</div>
        <div className="mt-12 grid gap-3 lg:grid-cols-2"><div className="skeleton h-[30rem] rounded-[var(--radius-panel)]" /><div className="skeleton h-[30rem] rounded-[var(--radius-panel)]" /></div>
      </div>
    </main>
  );
}

function LoadError({ message }: { message: string }) {
  return (
    <main className="mx-auto grid min-h-[70vh] max-w-7xl place-items-center px-4 sm:px-6">
      <div className={cn(panel, "max-w-lg p-8 text-center sm:p-10")} role="alert">
        <h1 className="display text-4xl">This office's evidence didn't arrive.</h1>
        <p className="mt-3 text-ink-2">The connection or the server may have hiccupped. Try again in a moment.</p>
        <p className="mt-2 font-mono text-xs text-muted">{message}</p>
        <button type="button" onClick={() => location.reload()} className="mt-6 inline-flex items-center gap-2 rounded-full bg-brand px-5 py-2.5 font-semibold text-card transition hover:bg-brand-2">
          <RotateCcw className="size-4" aria-hidden />Try again
        </button>
      </div>
    </main>
  );
}
