// Visuals for one office: what Google's AI said, the Maps listing, the number checks, the promise clock, the issue mix and
// review quotes. The office page and the chat's cards both use them. They animate as they appear; with reduced motion
// everything appears at once. Text from reviews and from Google is always rendered as text.
import { AnimatePresence, motion, useInView, useReducedMotion } from "motion/react";
import { Check, CircleHelp, MapPin, Phone, Search, ShieldOff, Sparkles, Star, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Found, StoryCard } from "../lib/api";
import { VERDICT, cn, possessive, excerpt, safeUrl, splitMarks, toneBg, toneText, type Tone } from "../lib/ui";
import { Chip, Mono, Provenance } from "./bits";
import { SearchId, Term } from "./explain";
import "../styles/evidence.css";

const ease = [0.16, 1, 0.3, 1] as const;

/** The shared surface every evidence panel sits on: the card colour, one hairline, the same radius everywhere. */
export const panel = "rounded-[1.5rem] border border-rule/80 bg-card shadow-[0_1px_2px_rgb(40_22_80/0.04)]";
/** The small heading inside a panel that names what it shows. */
export const label = "flex items-center gap-2 text-[13px] font-medium text-muted";
/** A section inside a panel, set off by a hairline instead of another box. */
export const section = "mt-6 border-t border-rule/70 pt-5";

function useTyped(text: string, active: boolean, speed = 26): string {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? text.length : 0);
  useEffect(() => {
    if (reduce) { setN(text.length); return; }
    setN(0);
    if (!active) return;
    let i = 0;
    const id = setInterval(() => { i += 1; setN(i); if (i >= text.length) clearInterval(id); }, speed);
    return () => clearInterval(id);
  }, [text, active, speed, reduce]);
  return text.slice(0, n);
}

/** Text with its numbers and PINs highlighted: green when they are the office's own, red otherwise. */
function Marked({ text, marks, good }: { text: string; marks: string[]; good: Set<string> }) {
  return <>{splitMarks(text, marks).map((part, j) => part.mark ? (
    <mark key={j} className={cn("rounded-md px-1 py-px font-semibold ring-1 ring-inset", good.has(part.text.toLowerCase()) ? "bg-kept-soft text-kept ring-kept/20" : "bg-broken-soft text-broken ring-broken/20")}>{part.text}</mark>
  ) : <span key={j}>{part.text}</span>)}</>;
}

export function SearchReplay({ card, active }: { card: StoryCard; active: boolean }) {
  const reduce = useReducedMotion();
  const query = card.query ?? "";
  const typed = useTyped(query, active && card.checked);
  const done = typed.length === query.length;
  const lines = card.ai ? card.ai.text.split("\n").filter(Boolean) : [];
  const good = new Set(card.ai?.good_marks.map((m) => m.toLowerCase()));
  const said = card.found.filter((f) => f.where === "Google's AI Overview");
  return (
    <div className={cn(panel, "overflow-hidden")}>
      <div className="px-4 pt-4 sm:px-5 sm:pt-5">
        {card.checked ? (
          <p className="flex items-center gap-3 rounded-[1.4rem] bg-paper-2/45 px-4 py-2.5 text-[15px] font-medium ring-1 ring-inset ring-rule/70">
            <Search className="size-4 shrink-0 text-brand" aria-hidden />
            <span className="min-w-0"><span className="sr-only">The search a citizen types: </span>{typed}
              {!done && <span className="ml-0.5 inline-block h-4 w-0.5 translate-y-0.5 animate-pulse bg-brand" aria-hidden />}</span>
          </p>
        ) : (
          <p className="flex items-center gap-3 rounded-full border border-dashed border-rule px-4 py-2.5 text-[15px] text-muted">
            <Search className="size-4 shrink-0" aria-hidden />Not searched for this office
          </p>
        )}
      </div>
      <div className="min-h-[18rem] p-5 pt-6 sm:p-7 sm:pt-7">
        {!card.checked ? (
          <p className="text-muted">This office's Google search didn't complete when we ran it (it failed three times), so there's no AI answer to show. Its Maps listing is below.</p>
        ) : !card.ai ? (
          done && <motion.p initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="serif text-xl text-muted">Google showed no AI Overview for this search.</motion.p>
        ) : (
          <AnimatePresence>
            {done && (
              <motion.div initial={reduce ? false : { opacity: 0 }} animate={{ opacity: 1 }}>
                <p className={cn(label, "mb-3")}><Sparkles className="size-3.5 text-pop" aria-hidden />Google's <Term k="overview">AI Overview</Term> said</p>
                <div className="space-y-1.5 text-[15px] leading-relaxed text-ink-2">
                  {lines.map((line, i) => (
                    <motion.p key={i} initial={reduce ? false : { opacity: 0, y: 6, filter: "blur(4px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ delay: 0.1 * i, duration: 0.5, ease }}>
                      <Marked text={line} marks={card.ai!.marks} good={good} />
                    </motion.p>
                  ))}
                </div>
                <motion.ul className={cn(section, "grid gap-2 text-sm")} initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: reduce ? 0 : 0.1 * lines.length + 0.3, duration: 0.5, ease }} aria-label="What the highlights mean">
                  {said.map((f) => (
                    <li key={f.display} className="flex flex-wrap items-baseline gap-x-2">
                      <Mono className="font-semibold">{f.display}</Mono>
                      <span className={toneText[VERDICT[f.verdict].tone]}>{VERDICT[f.verdict].label.replace(/^The /, "the ").replace(/^A /, "a ").replace(/^In /, "in ").replace(/^Another /, "another ")}</span>
                    </li>
                  ))}
                  {card.ai.address_matches !== null && card.ai.pincodes.length > 0 && (
                    <li className="flex flex-wrap items-baseline gap-x-2">
                      <Mono className="font-semibold"><Term k="pin">PIN</Term> {card.ai.pincodes.join(", ")}</Mono>
                      <span className={card.ai.address_matches ? "text-kept" : "text-broken"}>
                        {card.ai.address_matches ? "the office's own PIN" : `a different area: the office's PIN is ${card.ai.official_pin}`}
                      </span>
                    </li>
                  )}
                  {card.ai.sources.length > 0 && (
                    <li className="text-muted">The AI cites {card.ai.sources.map((src) => src.domain).filter((d, i, all) => all.indexOf(d) === i).join(", ")}.</li>
                  )}
                </motion.ul>
                {card.mode && <ModeCompare card={card} />}
                <Provenance>
                  <span>Captured {card.ai.searched_on} from Bengaluru, redrawn in our own style; unverified mobile numbers masked</span>
                </Provenance>
                <div className="mt-2 flex flex-wrap gap-2">
                  <SearchId engine="google" id={card.ai.search_id} />
                  {card.ai.overview_search_id && <SearchId engine="google_ai_overview" id={card.ai.overview_search_id} />}
                  {card.mode && <SearchId engine="google_ai_mode" id={card.mode.search_id} />}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        )}
        {card.checked && !card.ai && card.query && done && (
          <>
            {card.mode && <ModeCompare card={card} />}
            <div className="mt-4 flex flex-wrap gap-2">
              {card.searches.filter((x) => x.engine === "google").map((x) => <SearchId key={x.search_id} engine="google" id={x.search_id} />)}
              {card.mode && <SearchId engine="google_ai_mode" id={card.mode.search_id} />}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/** Google's AI Mode asked the same question: its first lines, highlighted, and whether it led with the office's number. */
function ModeCompare({ card }: { card: StoryCard }) {
  const m = card.mode!;
  const good = new Set(m.good_marks.map((x) => x.toLowerCase()));
  const own = m.first_verdict === "this office";
  const lines = m.text.split("\n").filter(Boolean).slice(0, 4);
  return (
    <div className={section}>
      <p className={label}><Sparkles className="size-3.5 text-brand" aria-hidden />Same question, Google's <Term k="mode">AI Mode</Term></p>
      <div className="mt-2.5 space-y-1 text-sm leading-relaxed text-ink-2">
        {lines.map((line, i) => <p key={i}><Marked text={line} marks={m.marks} good={good} /></p>)}
      </div>
      <p className={cn("mt-3 flex items-start gap-2 text-sm font-semibold", own ? "text-kept" : "text-broken")}>
        {own ? <Check className="mt-0.5 size-4 shrink-0" aria-hidden /> : <X className="mt-0.5 size-4 shrink-0" aria-hidden />}
        <span>
          {own ? `Leads with the office's own number, ${m.first_display}` : m.first_display ? `Leads with ${m.first_display}: ${VERDICT[m.first_verdict!].label.toLowerCase()}` : "Gives no number"}
          {m.address_matches === true ? ", and the right PIN." : m.address_matches === false ? `, but a PIN that isn't the office's.` : "."}
        </span>
      </p>
    </div>
  );
}

/** The same office on Bing Maps: is the missing number only Google's problem? */
function BingRow({ card }: { card: StoryCard }) {
  const b = card.bing!;
  return (
    <div className={section}>
      <p className={label}>And on Bing Maps</p>
      <p className="mt-1.5 text-sm">
        {!b.found ? <span className="text-muted">We couldn't match a Bing Maps place to this office (searched "{b.query}").</span>
          : !b.phone_display ? <><b>{b.title}</b>: <span className="font-semibold text-broken">no phone number{card.maps && !card.maps.phone ? " either" : ""}.</span></>
          : <><b>{b.title}</b>: <Mono className="font-semibold">{b.phone_display}</Mono>, <span className={toneText[VERDICT[b.phone_verdict!].tone]}>{VERDICT[b.phone_verdict!].label.toLowerCase()}</span>.</>}
      </p>
      {b.found && <p className="mt-0.5 text-xs text-muted">Matched: {b.how}.</p>}
      {b.search_id && <SearchId className="mt-2.5" engine="bing_maps" id={b.search_id} />}
    </div>
  );
}

export function MapsCard({ card }: { card: StoryCard }) {
  const m = card.maps;
  if (!m) {
    return (
      <div className={cn(panel, "p-5 sm:p-7")}>
        <p className={cn(label, "mb-3")}><MapPin className="size-3.5 text-brand" aria-hidden />Google Maps</p>
        <p className="serif text-3xl leading-tight text-broken">No listing of its own found.</p>
        <p className="mt-2 text-sm text-muted">Not finding one isn't proof there is none.</p>
        {card.bing && <BingRow card={card} />}
      </div>
    );
  }
  return (
    <div className={cn(panel, "p-5 sm:p-7")}>
      <p className={cn(label, "mb-3")}><MapPin className="size-3.5 text-brand" aria-hidden />The Google Maps <Term k="listing">listing</Term> we matched</p>
      <h3 className="serif text-2xl leading-snug tracking-[-0.01em]">{m.title}</h3>
      <p className="mt-2 flex items-center gap-2 text-sm text-muted">
        {m.rating && <span className="inline-flex items-center gap-1 font-semibold text-ink"><Star className="size-3.5 fill-pop text-pop" aria-hidden />{m.rating}</span>}
        {m.rating && <span aria-hidden>·</span>}
        <span className="tnum">{m.reviews.toLocaleString("en-IN")} reviews</span>
      </p>
      <div className="mt-5 divide-y divide-rule/70 border-t border-rule/70">
        <motion.div className="flex items-center gap-3.5 py-4" initial={{ x: 0 }} whileInView={m.phone ? {} : { x: [0, -6, 6, -4, 4, 0] }} viewport={{ once: true }} transition={{ delay: 0.5, duration: 0.5 }}>
          <span className={cn("grid size-9 shrink-0 place-items-center rounded-full", m.phone ? "bg-wash text-brand" : "bg-broken-soft text-broken")}><Phone className="size-4" aria-hidden /></span>
          {m.phone ? <Mono className="text-xl font-semibold">{m.phone}</Mono> : (
            <span><span className="block text-lg font-semibold text-broken">No phone number</span>
              <span className="block text-sm text-muted">The department publishes {card.official.length === 1 ? "one number" : `${card.official.length} numbers`} for this office.</span></span>
          )}
        </motion.div>
        <div className="flex items-center gap-3.5 py-4">
          <span className={cn("grid size-9 shrink-0 place-items-center rounded-full", m.unclaimed ? "bg-amber-soft text-amber" : "bg-paper-2 text-muted")}><ShieldOff className="size-4" aria-hidden /></span>
          {m.unclaimed ? <span><b className="font-semibold"><Term k="unclaimed">Unclaimed</Term>.</b> <span className="text-muted">No verified owner manages it.</span></span> : <span className="text-muted">Not marked unclaimed</span>}
        </div>
      </div>
      <Provenance>
        <span>Captured through SerpApi from Bengaluru</span>
        {safeUrl(m.url) && <a href={safeUrl(m.url)}>Open the live listing</a>}
      </Provenance>
      {m.search_id && <SearchId className="mt-2" engine="google_maps" id={m.search_id} />}
      {card.bing && <BingRow card={card} />}
    </div>
  );
}

function CheckRow({ item, revealed, icon, title, sub, chip }: { item: Found | null; revealed: boolean; icon: ReactNode; title: string; sub: string;
  chip?: { tone: Tone; label: string } }) {
  const reduce = useReducedMotion();
  const v = chip ?? (item ? VERDICT[item.verdict] : null);
  return (
    <motion.li layout="position" className="flex items-center gap-3.5 px-5 py-4 sm:gap-4 sm:px-6">
      <motion.span className={cn("grid size-8 shrink-0 place-items-center rounded-full transition-colors duration-500", revealed && v ? `${toneBg[v.tone]} text-card` : "bg-paper-2 text-muted")}
        animate={revealed ? { scale: [1, 1.15, 1] } : {}} transition={{ duration: 0.4 }}>
        {revealed && v ? (v.tone === "kept" ? <Check className="size-4" /> : v.tone === "broken" ? <X className="size-4" /> : <CircleHelp className="size-4" />) : icon}
      </motion.span>
      <div className="min-w-0 flex-1">
        <Mono className="block text-[17px] font-semibold">{title}</Mono>
        <span className="mt-0.5 block text-xs leading-snug text-muted">{sub}</span>
        {revealed && v && <span className={cn("mt-1 block text-xs font-semibold sm:hidden", toneText[v.tone])}>{v.label}</span>}
        {item?.also && revealed && <span className="mt-1 block text-xs font-semibold text-broken">{item.also}</span>}
      </div>
      <AnimatePresence>
        {revealed && v && (
          <motion.span initial={reduce ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} className="hidden shrink-0 sm:block"><Chip tone={v.tone}>{v.label}</Chip></motion.span>
        )}
      </AnimatePresence>
    </motion.li>
  );
}

/** Every number Google shows up front, checked one by one against the department's directory, which closes the panel. */
export function NumberChecks({ card, active }: { card: StoryCard; active: boolean }) {
  const reduce = useReducedMotion();
  const rows: { item: Found | null; title: string; sub: string; icon: ReactNode; chip?: { tone: Tone; label: string } }[] = card.found.map((f) => ({ item: f, title: f.display, sub: `From ${f.where}`, icon: <Phone className="size-3.5" /> }));
  if (card.ai && card.ai.address_matches !== null && card.ai.pincodes.length) {
    rows.push({ item: { display: "", where: "", detail: "", verdict: card.ai.address_matches ? "this office" : "another office" },
      title: `PIN ${card.ai.pincodes.join(", ")}`, sub: `The address in Google's AI Overview. The official PIN is ${card.ai.official_pin}.`, icon: <MapPin className="size-3.5" />,
      chip: card.ai.address_matches ? { tone: "kept", label: "The office's address" } : { tone: "broken", label: "A different address" } });
  }
  const [shown, setShown] = useState(reduce ? rows.length : 0);
  useEffect(() => {
    if (reduce) { setShown(rows.length); return; }
    setShown(0);
    if (!active) return;
    let i = 0;
    const id = setInterval(() => { i += 1; setShown(i); if (i >= rows.length) clearInterval(id); }, 700);
    return () => clearInterval(id);
  }, [active, rows.length, card.id, reduce]);
  const right = card.found.some((f) => f.verdict === "this office");
  const extra = (card.further?.own ?? []).filter((n) => card.found.every((f) => f.display !== n));
  return (
    <div className={cn(panel, "overflow-hidden")}>
      {!card.checked && <p className="border-b border-rule/70 bg-unknown-soft/60 px-5 py-3 text-sm text-muted sm:px-6">Google Search wasn't checked for this office.{card.listed ? " These are only what its Maps listing shows." : ""}</p>}
      <ul className="divide-y divide-rule/70">
        {rows.length === 0 ? (
          <CheckRow item={null} revealed icon={<X className="size-3.5" />}
            title={card.checked ? "No number up front" : card.listed ? "No number on the listing" : "Nothing to check"}
            sub={card.checked ? "Google's AI, its panels and the Maps listing gave no phone number" : card.listed ? "The Maps listing shows no phone" : "Our searches found no Maps listing for this office"} />
        ) : rows.map((r, i) => <CheckRow key={card.id + i} item={r.item} revealed={i < shown} title={r.title} sub={r.sub} icon={r.icon} chip={r.chip} />)}
      </ul>
      <AnimatePresence>
        {shown >= rows.length && (
          <motion.div initial={reduce ? false : { opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} transition={{ duration: 0.6, ease }}
            className="border-t border-kept/20 bg-kept-soft/55">
            <div className="px-5 py-5 sm:px-6">
              <p className="text-[13px] font-medium text-kept">What the {possessive(card.department)} <Term k="directory">directory</Term> lists</p>
              <div className="mt-3 grid gap-1.5">
                {card.official.map((p) => (
                  <a key={p.tel} href={`tel:${p.tel}`} className="group flex flex-wrap items-baseline gap-x-3">
                    <Mono className="text-lg font-semibold text-ink underline-offset-4 group-hover:underline">{p.display}</Mono>
                    <span className="text-xs text-kept">{p.label.includes("(CUG)") ? <>{p.label.replace(" (CUG)", "")} (<Term k="cug">CUG</Term>)</> : p.label}</span>
                  </a>
                ))}
              </div>
              <p className="mt-3 text-sm leading-relaxed text-kept">
                {right ? "Google shows one of these up front, among other answers." : card.checked ? "None of these appear in Google's AI answer, its panels or the Maps listing." : card.listed ? "The Maps listing shows none of these." : "We found no Maps listing to compare."}
                {extra.length > 0 && ` Further down the results, ${card.further!.sites.join(", ")} ${card.further!.sites.length === 1 ? "lists" : "list"} ${extra.length === 1 ? "one" : extra.length}${right ? " more" : ""}.`}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * A row of working days as one segmented bar: green within the limit, red past it, with a marker at the limit.
 * Days from `upTo` on are drawn faint (days of the limit not yet used).
 */
function DayBar({ total, limit, upTo, active, label, overflow = 0 }: { total: number; limit: number; upTo: number; active: boolean; label: string; overflow?: number }) {
  const reduce = useReducedMotion();
  const at = Math.min(limit, total) / total;
  const edge = at > 0.82 ? "-translate-x-full" : at < 0.18 ? "" : "-translate-x-1/2";
  return (
    <div className="mt-8" role="img" aria-label={label}>
      <div className="relative" style={{ maxWidth: total * 56 }}>
        <div className="flex h-9 gap-[3px] sm:h-11">
          {Array.from({ length: total }, (_, i) => (
            <motion.span key={i} className={cn("min-w-0 flex-1 origin-bottom rounded-[5px]", i < limit ? "bg-kept" : "bg-broken")}
              initial={reduce ? false : { opacity: 0, scaleY: 0.2 }} animate={active ? { opacity: i >= upTo ? 0.22 : 1, scaleY: 1 } : {}}
              style={reduce ? { opacity: i >= upTo ? 0.22 : 1 } : undefined}
              transition={{ delay: 0.035 * i + (i >= limit ? 0.35 : 0), duration: 0.45, ease }} />
          ))}
        </div>
        {limit <= total && (
          <div className="pointer-events-none absolute -top-7 bottom-[-6px]" style={{ left: `calc(${at} * (100% + 3px) - 2.5px)` }} aria-hidden>
            <span className="absolute inset-y-[22px] left-0 w-[2px] rounded-full bg-ink" />
            <span className={cn("absolute top-0 whitespace-nowrap rounded-full bg-ink px-2 py-0.5 text-[11px] font-medium text-paper", edge)}>Limit: day {limit}</span>
          </div>
        )}
        <div className="mt-2 flex justify-between font-mono text-[11px] text-muted" aria-hidden>
          <span>Day 1</span>
          {total > limit && <span>Day {total}{overflow > 0 && <span className="text-broken"> +{overflow}</span>}</span>}
        </div>
      </div>
    </div>
  );
}

/** The visitor's own application against the legal limit: one segment per working day, red past the limit. */
function YourWait({ card, active }: { card: StoryCard; active: boolean }) {
  const y = card.yours!;
  const cap = 40, shown = Math.min(Math.max(y.limit_days, y.elapsed ?? 0), cap);
  const tone = y.status === "past" ? "broken" : y.status === "near" || y.status === "uncertain" ? "amber" : "ink";
  return (
    <div className={cn(panel, "mb-3 p-5 sm:p-8")}>
      <p className={label}>Your application · {y.service.replace(/\s*\(.*?\)/g, "")}</p>
      <div className="mt-4 grid gap-6 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className="serif text-[2.6rem] leading-none tracking-[-0.03em] text-kept sm:text-[3.4rem]">{y.limit}</p>
          <p className="mt-2 text-sm text-muted">allowed</p>
        </div>
        {y.elapsed !== null && (
          <div className="sm:text-right">
            <p className={cn("serif text-[2.6rem] leading-none tracking-[-0.03em] sm:text-[3.4rem]", tone === "broken" ? "text-broken" : tone === "amber" ? "text-amber" : "text-ink")}><span className="tnum">{y.elapsed}</span></p>
            <p className="mt-2 text-sm text-muted">working days since {y.applied}</p>
          </div>
        )}
      </div>
      {y.elapsed !== null && (
        <DayBar total={shown} limit={y.limit_days} upTo={y.elapsed} active={active} overflow={Math.max(0, y.elapsed - cap)}
          label={`${y.limit} allowed; about ${y.elapsed} working days so far`} />
      )}
      <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-ink-2">
        {y.elapsed === null ? "Add the date you applied to your question at the top, and this counts your working days."
          : y.status === "past" ? `That's past the limit${y.condition ? `, if everything required was submitted when you applied (the limit runs ${y.condition})` : ""}. You can ask the officer in writing; the complaint letter does the counting for you.`
          : y.status === "near" ? "That's at or just past the limit, depending on public holidays in between (the count doesn't subtract them)."
          : y.status === "uncertain" ? `The limit leaves out the ${y.condition.split("excluding the ")[1] ?? "police verification period"}; this count includes it, so it can't show whether the limit was missed.`
          : "You're still within the legal limit."}
      </p>
    </div>
  );
}

export function PromiseClock({ card, active }: { card: StoryCard; active: boolean }) {
  return <>{card.yours && <YourWait card={card} active={active} />}<ReviewClock card={card} active={active} /></>;
}

function ReviewClock({ card, active }: { card: StoryCard; active: boolean }) {
  const k = card.clock;
  const reported = k.reported_days ?? 0;
  const total = Math.max(k.limit_days, reported);
  if (card.yours && !reported) {
    return (
      <div className={cn(panel, "px-5 py-5 sm:px-8")}>
        <p className={label}>What reviewers report at this office</p>
        <p className="mt-1.5 text-sm text-ink-2">{k.note}</p>
      </div>
    );
  }
  return (
    <div className={cn(panel, "p-5 sm:p-8")}>
      {card.yours && <p className={cn(label, "mb-4")}>What reviewers report at this office</p>}
      <div className="grid gap-6 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div>
          <p className={label}>{card.promise.kind === "law" ? <>The <Term k="sakala">law</Term> allows</> : <>The <Term k="charter">Citizen's Charter</Term> promises</>}</p>
          <p className="serif mt-2 text-[2.6rem] leading-none tracking-[-0.03em] text-kept sm:text-[3.4rem]">{k.limit}</p>
          <p className="mt-2 text-sm text-muted">for {k.service.charAt(0).toLowerCase() + k.service.slice(1)}</p>
        </div>
        {reported > 0 && (
          <div className="sm:text-right">
            <p className={cn(label, "sm:justify-end")}>A reviewer wrote</p>
            <p className="serif mt-2 text-[2.6rem] font-medium leading-none tracking-[-0.03em] text-broken sm:text-[3.4rem]">“{k.said}”</p>
            <p className="mt-2 text-sm text-muted">about {reported} working days{k.conversion && ", at five a week"}</p>
          </div>
        )}
      </div>
      <DayBar total={total} limit={k.limit_days} upTo={total} active={active}
        label={`${k.limit_days} working days allowed${reported ? `; about ${reported} working days reported` : ""}`} />
      <p className="mt-4 text-xs leading-relaxed text-muted">One segment per <Term k="working">working day</Term>.{k.terms ? ` Counted ${k.terms}.` : ""}</p>
      {reported > 0 && k.quote && (
        <PullQuote className="mt-7 border-t border-rule/70 pt-6" tone="broken" text={k.quote} evidence={k.evidence} highlight={k.said ?? ""} limit={260}
          caption={<>{k.rating ? `Rated ${k.rating}★ by the reviewer. ` : ""}Google review, {k.date}. One person's account, not a rate.</>}
          links={<>{safeUrl(k.link) && <a href={safeUrl(k.link)}>Read it</a>}<a href={safeUrl(k.citation)}>{card.promise.kind === "law" ? "Sakala timeline" : "Citizen's Charter"}</a></>}>
          {k.search_id && <SearchId className="mt-3" engine="google_maps_reviews" id={k.search_id} />}
        </PullQuote>
      )}
      {!reported && <p className="serif mt-6 text-xl text-ink-2">{k.note}</p>}
    </div>
  );
}

/** A citizen's review as a pull quote: upright serif under a big marigold quotation mark, the phrase that matched highlighted, and where it came from. */
export function PullQuote({ text, evidence = "", highlight, tone, caption, links, limit = 240, size = "md", className, children }: {
  text: string; evidence?: string; highlight?: string; tone: "broken" | "kept"; caption: ReactNode; links?: ReactNode; limit?: number;
  size?: "md" | "lg"; className?: string; children?: ReactNode;
}) {
  const parts = splitMarks(excerpt(text, evidence, limit), [highlight ?? evidence]);
  return (
    <figure className={cn("relative", className)}>
      <span aria-hidden className={cn("serif pointer-events-none block select-none leading-[0.6]", size === "lg" ? "h-7 text-7xl" : "h-6 text-6xl", tone === "broken" ? "text-pop" : "text-kept/70")}>“</span>
      <blockquote className={cn("serif text-ink", size === "lg" ? "text-[1.35rem] leading-[1.45]" : "text-[1.15rem] leading-[1.5]")}>
        {parts.map((p, i) => p.mark
          ? <mark key={i} className={cn("rounded px-0.5 font-sans text-[0.86em] font-semibold", tone === "broken" ? "bg-broken-soft text-broken" : "bg-kept-soft text-kept")}>{p.text}</mark>
          : <span key={i}>{p.text}</span>)}
      </blockquote>
      <figcaption className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted [&_a]:font-medium [&_a]:text-ink-2 [&_a]:underline [&_a]:decoration-current/30 [&_a]:underline-offset-2 [&_a:hover]:text-brand">
        <span>{caption}</span>{links}
      </figcaption>
      {children}
    </figure>
  );
}

export interface IssueRow { category: string; label: string; polarity: string; count: number; of: number }

/** The issue mix: how many recent reviews with text raise each issue, as labelled bars that grow in on scroll. */
export function IssueChart({ issues, of, className }: { issues: IssueRow[]; of: number; className?: string }) {
  const ref = useRef<HTMLUListElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.3 });
  const reduce = useReducedMotion();
  const rows = [...issues].sort((a, b) => (a.polarity === "problem" ? 0 : 1) - (b.polarity === "problem" ? 0 : 1) || b.count - a.count);
  const max = Math.max(of, 1);
  return (
    <ul ref={ref} className={cn("space-y-3.5", className)} aria-label={`Issues raised in ${of} recent reviews with text`}>
      {rows.map((r, i) => {
        const bad = r.polarity === "problem";
        const pct = (r.count / max) * 100;
        return (
          <li key={r.category} className={cn(!bad && rows[i - 1]?.polarity === "problem" && "mt-6 border-t border-dashed border-rule pt-5")}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className={cn("font-medium", r.count ? "text-ink" : "text-muted")}>{r.label}</span>
              <Mono className={cn("shrink-0 text-xs", r.count ? (bad ? "text-broken" : "text-kept") : "text-muted")}>{r.count} of {r.of}</Mono>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-paper-2">
              <motion.div className={cn("h-full rounded-full", bad ? "bg-broken" : "bg-kept")}
                initial={reduce ? false : { width: 0 }} animate={inView || reduce ? { width: `${pct}%` } : {}} style={reduce ? { width: `${pct}%` } : undefined}
                transition={{ delay: 0.06 * i, duration: 0.9, ease }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
