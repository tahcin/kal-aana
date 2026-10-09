// The chat's cards. Each is drawn from data a tool returned (kalaana/chat.py), never from model text.
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, ArrowUpRight, Check, Copy, Mail, Newspaper, Search as SearchIcon } from "lucide-react";
import { createContext, useContext, useState, type ReactNode } from "react";
import { Link } from "react-router";
import type { ChatCard, ReviewIssue } from "../lib/chat";
import { cn, safeUrl } from "../lib/ui";
import { Mono } from "./bits";
import { SearchId } from "./explain";
import { IssueChart, MapsCard, NumberChecks, PromiseClock, PullQuote, SearchReplay, panel } from "./story";

const ease = [0.16, 1, 0.3, 1] as const;

/** Every card's frame: what it shows and for which office, a link to the office's full evidence, then the evidence. */
function Frame({ label, title, to, children, className }: { label: string; title?: string; to?: string; children: ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  const named = useContext(Named);
  return (
    <motion.section initial={reduce ? false : { opacity: 0, y: 14, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ duration: 0.6, ease }}
      className={cn("my-8 sm:my-10", className)}>
      <header className="mb-3.5 flex items-end justify-between gap-4 px-1">
        <div className="min-w-0">
          <h3 className="text-[15px] font-semibold leading-snug text-ink">{label}</h3>
          {title && named && <p className="mt-0.5 text-sm leading-snug text-muted">{title}</p>}
        </div>
        {to && (
          <Link to={to} className="group inline-flex shrink-0 items-center gap-1 pb-px text-[13px] font-medium text-brand transition-colors hover:text-ink">
            The full evidence <ArrowRight className="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5" aria-hidden />
          </Link>
        )}
      </header>
      {children}
    </motion.section>
  );
}

/** A note set apart in the amber of "check this": a caveat that must stay visible. */
const Caveat = ({ children, className }: { children: ReactNode; className?: string }) =>
  <p className={cn("rounded-2xl bg-amber-soft/80 px-5 py-3.5 text-sm leading-relaxed text-amber", className)}>{children}</p>;

const Empty = ({ children }: { children: ReactNode }) =>
  <p className="rounded-[1.5rem] bg-paper-2/70 px-5 py-4 text-sm leading-relaxed text-muted sm:px-6">{children}</p>;

/** One card of a reply. `named` is false when the card before it in the same reply already named its office. */
export function Card({ card, onAsk, named = true }: { card: ChatCard; onAsk: (text: string) => void; named?: boolean }) {
  return <Named.Provider value={named}><CardBody card={card} onAsk={onAsk} /></Named.Provider>;
}

const Named = createContext(true);

function CardBody({ card, onAsk }: { card: ChatCard; onAsk: (text: string) => void }) {
  switch (card.kind) {
    case "numbers":
      return (
        <Frame label="Its numbers" title={card.card.label} to={`/office/${encodeURIComponent(card.card.id)}`}>
          <div className="grid gap-3 [&>*]:min-w-0">
            <NumberChecks card={card.card} active />
            <MapsCard card={card.card} />
          </div>
        </Frame>
      );
    case "ai":
      return <Frame label="What Google's AI told citizens" title={card.card.label} to={`/office/${encodeURIComponent(card.card.id)}`}><SearchReplay card={card.card} active /></Frame>;
    case "unchecked":
      return (
        <Frame label="What Google's AI told citizens" title={card.card.label}>
          <Empty>This office's Google search didn't complete when we ran it (it failed three times), so there's no AI answer to show.</Empty>
        </Frame>
      );
    case "wait":
      return (
        <Frame label="The time limit" title={card.card.label} to={`/office/${encodeURIComponent(card.card.id)}`}>
          <PromiseClock card={card.card} active />
          {card.caveats.map((c) => <Caveat key={c} className="mt-3">{c}</Caveat>)}
        </Frame>
      );
    case "reviews":
      return <Reviews card={card} />;
    case "letter":
      return <Letter card={card} />;
    case "report":
      return <Report card={card} />;
    case "search":
      return <Search card={card} />;
    case "busy":
      return <Busy card={card} />;
    case "portals":
      return (
        <Frame label="Official portals">
          <ul className={cn(panel, "divide-y divide-rule/70 overflow-hidden")}>
            {card.links.map((l) => (
              <li key={l.url}><a href={safeUrl(l.url)} target="_blank" rel="noopener noreferrer"
                className="group flex items-center justify-between gap-4 px-5 py-4 transition-colors hover:bg-wash/40 sm:px-6">
                <span className="min-w-0">
                  <span className="block font-medium text-ink">{l.label}</span>
                  <span className="mt-0.5 block truncate font-mono text-xs text-muted">{l.url.replace(/^https:\/\//, "").replace(/\/.*$/, "")}</span>
                </span>
                <ArrowUpRight className="size-4 shrink-0 text-muted transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-brand" aria-hidden />
              </a></li>
            ))}
          </ul>
        </Frame>
      );
    case "news":
      return <News card={card} />;
    case "choose":
      return (
        <Frame label="Which office?">
          <div className="flex flex-wrap gap-2">
            {card.options.map((o) => (
              <button key={o.id} onClick={() => onAsk(`I mean ${o.label}.`)}
                className="rounded-full border border-rule/80 bg-card px-4 py-2 text-sm font-medium text-ink-2 transition-colors hover:border-brand/50 hover:bg-wash/60 hover:text-brand">{o.label}</button>
            ))}
          </div>
        </Frame>
      );
  }
}

function Reviews({ card }: { card: Extract<ChatCard, { kind: "reviews" }> }) {
  if (!card.sampled) {
    return <Frame label="What reviewers report" title={card.label}><Empty>This office's reviews weren't sampled, so there's nothing to report.</Empty></Frame>;
  }
  const quoted = [...card.issues.filter((i) => i.polarity === "problem"), ...card.issues.filter((i) => i.polarity !== "problem")].filter((i) => i.quotes.length);
  return (
    <Frame label="What reviewers report" title={card.label} to={`/office/${encodeURIComponent(card.office_id)}`}>
      <div className={cn(panel, "p-5 sm:p-8")}>
        <p className="serif text-[1.35rem] leading-snug text-ink">
          <span className="text-broken">{card.problem} of {card.window}</span> recent Google reviews with text report a problem
          {card.span && <span className="text-ink-2"> ({card.span[0]} to {card.span[1]})</span>}.
        </p>
        <p className="mt-2 text-sm text-muted">{!card.enough && "That's too few reviews to read much into. "}Each review is one person's account, and reviewers are self-selected.</p>
        <IssueChart className="mt-6" issues={card.issues} of={card.window ?? card.issues[0]?.of ?? 0} />
        {quoted.length > 0 && (
          <div className="mt-8 grid gap-8 border-t border-rule/70 pt-7 md:grid-cols-2">
            {quoted.map((i) => <IssueQuote key={i.category} issue={i} />)}
          </div>
        )}
      </div>
    </Frame>
  );
}

function IssueQuote({ issue }: { issue: ReviewIssue }) {
  const q = issue.quotes[0];
  const bad = issue.polarity === "problem";
  return (
    <div>
      <p className={cn("mb-2 text-[13px] font-medium", bad ? "text-broken" : "text-kept")}>{issue.label}</p>
      <PullQuote tone={bad ? "broken" : "kept"} text={q.text} evidence={q.evidence} limit={220}
        caption={<>{q.rating ? `${q.rating}★ · ` : ""}Google review, {q.date}</>}
        links={safeUrl(q.link) && <a href={safeUrl(q.link)}>Read it</a>} />
    </div>
  );
}

function Letter({ card }: { card: Extract<ChatCard, { kind: "letter" }> }) {
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);
  if (!card.letter) return null;
  const copy = () => {
    const done = (ok: boolean) => { setCopied(ok ? "yes" : "no"); setTimeout(() => setCopied(null), 1800); };
    try { navigator.clipboard.writeText(card.letter!).then(() => done(true), () => done(false)); } catch { done(false); }  // no clipboard on plain http
  };
  const mail = `mailto:${card.to.email}?subject=${encodeURIComponent(card.subject ?? "")}&body=${encodeURIComponent(card.letter)}`;
  return (
    <Frame label="A complaint letter" title={card.to.label}>
      <div className="relative">
        {/* A second sheet peeking out underneath, so it reads as paper. */}
        <div aria-hidden className="absolute inset-x-4 -bottom-1.5 top-3 rotate-[0.5deg] rounded-[1.5rem] border border-rule/80 bg-card/70" />
        <article className="letter-paper relative overflow-hidden rounded-[1.5rem] border border-rule/80 shadow-[var(--shadow-soft)]">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rule/70 px-5 py-4 sm:pl-16 sm:pr-5">
            <dl className="grid min-w-0 grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
              <dt className="text-muted">To</dt><dd className="min-w-0 truncate"><Mono className="font-semibold">{card.to.email}</Mono></dd>
              {card.subject && <><dt className="text-muted">Subject</dt><dd className="min-w-0 font-medium">{card.subject}</dd></>}
            </dl>
            <div className="flex gap-2">
              <button type="button" onClick={copy} className="inline-flex h-9 items-center gap-1.5 rounded-full border border-rule bg-card px-3.5 text-[13px] font-medium text-ink-2 transition-colors hover:border-brand/50 hover:text-brand">
                {copied === "yes" ? <Check className="size-3.5 text-kept" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}{copied === "yes" ? "Copied" : copied === "no" ? "Select the text to copy" : "Copy letter"}
              </button>
              <a href={mail} className="inline-flex h-9 items-center gap-1.5 rounded-full bg-brand px-4 text-[13px] font-medium text-white transition-colors hover:bg-brand-2"><Mail className="size-3.5" aria-hidden />Open in email</a>
              <span className="sr-only" aria-live="polite">{copied === "yes" ? "Letter copied" : ""}</span>
            </div>
          </header>
          <div className="fade-bottom max-h-[28rem] overflow-y-auto">
            <pre className="serif whitespace-pre-wrap px-5 pb-12 pt-6 text-[1.05rem] leading-[1.7] text-ink sm:pl-16 sm:pr-10">{card.letter}</pre>
          </div>
        </article>
      </div>
      <div className="relative mt-5 space-y-2.5">
        {card.uncertain && <Caveat>The count includes a period the limit leaves out, so it can't show whether the limit was missed. This letter asks for the application's status.</Caveat>}
        {card.caveats.map((c) => <Caveat key={c}>{c} The letter states which applies; change it if yours is different.</Caveat>)}
        <p className="px-1 text-[13px] text-muted">Fill in your name and details, then send it yourself. Kal Aana sends nothing.</p>
      </div>
    </Frame>
  );
}

function Report({ card }: { card: Extract<ChatCard, { kind: "report" }> }) {
  const h = card.headline;
  const stats: [number, number, string][] = [
    [h.listing_no_phone, h.listed, "Google Maps listings show no phone"],
    [h.listing_official_phone, h.listed, "listings show the number the department publishes"],
    [h.ai_first_number_right, h.ai_overviews, "AI Overviews led with the office's own number"],
    [h.ai_mode_first_number_right, h.ai_mode_answers, "AI Mode answers led with it"],
  ];
  return (
    <Frame label="Report card" title={`All ${h.offices} ${card.plural}`}>
      <div className={cn(panel, "grid gap-px overflow-hidden bg-rule/70 sm:grid-cols-2")}>
        {stats.filter(([, of]) => of > 0).map(([n, of, label]) => (
          <div key={label} className="bg-card px-5 py-6 sm:px-7 sm:last:odd:col-span-2">
            <p className="serif text-5xl leading-none tracking-[-0.03em]"><span className="tnum">{n}</span><span className="text-2xl text-muted"> of {of}</span></p>
            <div className="mt-4 h-1 overflow-hidden rounded-full bg-paper-2" aria-hidden><div className="h-full rounded-full bg-brand" style={{ width: `${(n / of) * 100}%` }} /></div>
            <p className="mt-3 text-sm leading-snug text-ink-2">{label}</p>
          </div>
        ))}
      </div>
      <Link to={`/offices?type=${card.office_type}`} className="group mt-4 inline-flex items-center gap-1 px-1 text-[13px] font-medium text-brand transition-colors hover:text-ink">Every office, ranked <ArrowRight className="size-3.5 transition-transform duration-300 group-hover:translate-x-0.5" aria-hidden /></Link>
    </Frame>
  );
}

/** When a live search ran: "just now" for a fresh one, else the time it was cached (within the hour). */
const when = (card: { fresh: boolean; searched_at: string }) => {
  if (card.fresh) return "just now";
  const t = Date.parse(card.searched_at);
  return Number.isNaN(t) ? "in the last hour"
    : `at ${new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" }).format(t)} IST`;
};

/** The receipt strip under a live result list: what was searched, when, and the search ID. */
function LiveFooter({ children, engine, id }: { children: ReactNode; engine: "google" | "google_news"; id: string }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-rule/70 px-5 py-4 text-xs leading-relaxed text-muted sm:px-6">
      <span className="min-w-0 flex-1 basis-64">{children}</span>
      {id && <SearchId engine={engine} id={id} />}
    </div>
  );
}

function Search({ card }: { card: Extract<ChatCard, { kind: "search" }> }) {
  return (
    <Frame label="Live search" title={`"${card.query}"${card.official_only && !card.no_official ? " · government sites only" : ""}`}>
      <div className={cn(panel, "overflow-hidden")}>
        {card.no_official && card.results.length > 0 && <p className="border-b border-amber/20 bg-amber-soft/80 px-5 py-3.5 text-sm leading-relaxed text-amber sm:px-6">No government page came up, so these are other sites. Check the official portal before relying on them.</p>}
        {card.results.length === 0
          ? <p className="flex items-center gap-2 px-5 py-5 text-sm text-muted sm:px-6"><SearchIcon className="size-4" aria-hidden />No results{card.official_only ? " on government sites" : ""}.</p>
          : <ol className="divide-y divide-rule/70">
              {card.results.map((r, i) => (
                <li key={`${i}-${r.link}`} className="px-5 py-4 sm:px-6">
                  <p className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs">
                    <span className={cn("inline-flex items-center gap-1.5 font-medium", r.official ? "text-kept" : "text-muted")}>
                      <span className={cn("size-1.5 rounded-full", r.official ? "bg-kept" : "bg-unknown")} aria-hidden />{r.official ? "Government site" : "Other site"}
                    </span>
                    <span className="text-muted/50" aria-hidden>·</span>
                    <span className="font-mono text-muted">{r.domain}</span>
                  </p>
                  <a href={safeUrl(r.link)} target="_blank" rel="noopener noreferrer" className="mt-1.5 block font-medium text-ink decoration-brand/40 underline-offset-4 hover:text-brand hover:underline">{r.title}</a>
                  {r.snippet && <p className="mt-1 text-sm leading-relaxed text-ink-2">{r.snippet}</p>}
                </li>
              ))}
            </ol>}
        <LiveFooter engine="google" id={card.search_id}>Google results from Bengaluru through SerpApi, searched {when(card)}. Snippets are partial: open the page for the details.</LiveFooter>
      </div>
    </Frame>
  );
}

function News({ card }: { card: Extract<ChatCard, { kind: "news" }> }) {
  return (
    <Frame label="Live news" title={`"${card.query}"`}>
      <div className={cn(panel, "overflow-hidden")}>
        {card.results.length === 0 ? <p className="flex items-center gap-2 px-5 py-5 text-sm text-muted sm:px-6"><Newspaper className="size-4" aria-hidden />No recent reports found.</p> : (
          <ol className="divide-y divide-rule/70">
            {card.results.map((r, i) => (
              <li key={`${i}-${r.link}`} className="grid gap-1 px-5 py-4 sm:grid-cols-[6.5rem_1fr] sm:gap-4 sm:px-6">
                <Mono className="pt-0.5 text-xs text-muted">{/^\d{4}-\d{2}-\d{2}/.test(r.date) ? r.date.slice(0, 10) : r.date}</Mono>
                <span><a href={safeUrl(r.link)} target="_blank" rel="noopener noreferrer" className="serif text-[1.1rem] leading-snug text-ink decoration-brand/40 underline-offset-4 hover:text-brand hover:underline">{r.title}</a>
                  <span className="mt-0.5 block text-xs text-muted">{r.source || r.domain}</span></span>
              </li>
            ))}
          </ol>
        )}
        <LiveFooter engine="google_news" id={card.search_id}>Google News (India) through SerpApi, searched {when(card)}. A headline's date matters: an old report says nothing about today.</LiveFooter>
      </div>
    </Frame>
  );
}

const HOURS = [9, 10, 11, 12, 13, 14, 15, 16, 17];
const hourLabel = (h: number) => `${h % 12 || 12}${h < 12 ? "am" : "pm"}`;
/** Busyness is not a verdict, so it is drawn in the brand violet, not in red. */
const heat = (s: number) => `color-mix(in srgb, var(--color-brand) ${Math.round(12 + s * 0.8)}%, var(--color-paper-2))`;

/** Google's typical busyness by weekday and hour: darker is busier; a blank cell shows no visits (often closed). */
function Busy({ card }: { card: Extract<ChatCard, { kind: "busy" }> }) {
  const days = Object.entries(card.busy.days);
  const at = (day: string, h: number) => card.busy.days[day]?.find(([x]) => x === h)?.[1] ?? 0;
  // The quietest hour a visit makes sense: a weekday, 10 am to 4 pm, with visits shown (a Saturday may be a closed one).
  const open = days.filter(([d]) => d !== "saturday" && d !== "sunday")
    .flatMap(([d, hs]) => hs.filter(([h, s]) => s > 0 && h >= 10 && h <= 16).map(([h, s]) => ({ d, h, s })));
  const low = open.length ? Math.min(...open.map((x) => x.s)) : null;
  const quiet = open.filter((x) => x.s === low).slice(0, 3);
  const isQuiet = (d: string, h: number) => quiet.some((x) => x.d === d && x.h === h);
  return (
    <Frame label="When it's usually less crowded" title={card.label} to={`/office/${encodeURIComponent(card.office_id)}`}>
      <div className={cn(panel, "p-5 sm:p-8")}>
        {quiet.length > 0 && (
          <p className="serif text-[1.35rem] leading-snug text-ink">The quietest time worth going: <span className="pop-underline">{quiet.map((x) => `${x.d[0].toUpperCase()}${x.d.slice(1, 3)} ${hourLabel(x.h)}`).join(", ")}</span>. Only weekdays from 10 am to 4 pm count; later hours look quieter, but the counters are closing.</p>
        )}
        <div className="-mx-1 mt-5 overflow-x-auto px-1">
          <table className="border-separate border-spacing-1 text-xs" aria-label="Typical busyness by weekday and hour">
            <thead><tr><th />{HOURS.map((h) => <th key={h} scope="col" className="px-0.5 font-mono text-[10px] font-normal text-muted">{hourLabel(h)}</th>)}</tr></thead>
            <tbody>
              {days.map(([d]) => (
                <tr key={d}>
                  <th scope="row" className="pr-2 text-left font-medium text-ink-2">{d[0].toUpperCase() + d.slice(1, 3)}</th>
                  {HOURS.map((h) => {
                    const s = at(d, h);
                    return <td key={h} title={s ? `${s} of 100` : "No visits shown"} aria-label={`${d} ${hourLabel(h)}: ${s ? `${s} of 100` : "no visits shown"}`}
                      className={cn("size-7 rounded-md sm:size-9", s ? "" : "border border-dashed border-rule", isQuiet(d, h) && "ring-2 ring-pop ring-offset-1 ring-offset-card")}
                      style={s ? { backgroundColor: heat(s) } : undefined} />;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] text-muted" aria-hidden>
          <span className="inline-flex items-center gap-2">Quieter<span className="h-2 w-24 rounded-full" style={{ background: `linear-gradient(90deg, ${heat(5)}, ${heat(100)})` }} />Busier</span>
          {quiet.length > 0 && <span className="inline-flex items-center gap-1.5"><span className="size-3 rounded-[4px] ring-2 ring-pop" />Quietest, 10 am to 4 pm on a weekday</span>}
        </div>
        <p className="mt-4 text-xs leading-relaxed text-muted">
          Google's typical busyness for "{card.busy.title}", captured {card.as_of}: how busy the place usually is, not today,
          and not the queue at any one counter. Darker is busier; a dashed cell shows no visits (often closed). Offices are
          closed on Sundays and the 2nd and 4th Saturdays.
        </p>
        <SearchId className="mt-3" engine={card.busy.engine === "google_maps" ? "google_maps" : "google"} id={card.busy.search_id} />
      </div>
    </Frame>
  );
}
