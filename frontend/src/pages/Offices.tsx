import { LayoutGroup, motion, useReducedMotion } from "motion/react";
import { ArrowDown, ArrowUp, ChevronsUpDown, Info } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { Chip, CountUp, Mono, Reveal } from "../components/bits";
import { Footer } from "../components/Shell";
import { useJSON, type MapsStatus, type OfficeSummary, type Overview } from "../lib/api";
import { TabList } from "../components/tabs";
import { panelProps } from "../lib/tabs";
import { AI, MAPS, cn, toneBg } from "../lib/ui";
import { useTitle } from "../lib/useTitle";

type Sort = "score" | "problems" | "name";
const SORTS: { id: Sort; label: string; short: string }[] = [
  { id: "score", label: "Listing score", short: "Score" }, { id: "problems", label: "Reported problems", short: "Problems" }, { id: "name", label: "Name", short: "Name" },
];
// Which way each sort runs: worst listing score first, most problem reviews first, names A to Z.
const DESCENDING: Record<Sort, boolean> = { score: false, problems: true, name: false };
const EASE = [0.16, 1, 0.3, 1] as const;
// The order dots are grouped in, worst first.
const STATUS_ORDER: MapsStatus[] = ["no_phone", "no_listing", "other", "helpline", "official"];

const capital = (s: string) => s[0].toUpperCase() + s.slice(1);

function share(o: OfficeSummary) {
  return o.enough_evidence && o.window_reviews ? o.problem_reviews / o.window_reviews : -1;
}

function Bar({ value, max, tone, className }: { value: number; max: number; tone: string; className?: string }) {
  const reduce = useReducedMotion();
  const width = `${(100 * value) / max}%`;
  return (
    <span className={cn("block h-1 w-16 shrink-0 overflow-hidden rounded-full bg-rule", className)} aria-hidden>
      <motion.span className={cn("block h-full rounded-full", tone)} initial={reduce ? false : { width: 0 }}
        style={reduce ? { width } : undefined} whileInView={{ width }} viewport={{ once: true }} transition={{ duration: 0.9, ease: EASE }} />
    </span>
  );
}

/** A dot coloured by what Google Maps shows; offices with no listing at all get a hollow ring. */
function StatusDot({ status, className }: { status: MapsStatus; className?: string }) {
  return <span aria-hidden className={cn("inline-block shrink-0 rounded-full", status === "no_listing" ? "border-2 border-broken" : toneBg[MAPS[status].tone], className)} />;
}

/** One dot per office of this type, grouped by what its Google Maps listing shows. */
function UnitChart({ offices }: { offices: OfficeSummary[] }) {
  const reduce = useReducedMotion();
  const sorted = [...offices].sort((a, b) => STATUS_ORDER.indexOf(a.maps) - STATUS_ORDER.indexOf(b.maps) || a.label.localeCompare(b.label));
  const present = STATUS_ORDER.filter((s) => offices.some((o) => o.maps === s));
  return (
    <figure className="surface rounded-[1.75rem] p-5 sm:p-6">
      <figcaption className="text-xs font-medium text-muted">Each dot is one office</figcaption>
      <ul className="mt-4 flex flex-wrap gap-[7px]" aria-label="What each office's Google Maps listing shows">
        {sorted.map((o, i) => (
          <motion.li key={o.id} title={`${o.label}: ${MAPS[o.maps].label}`} initial={reduce ? false : { opacity: 0, scale: 0.4 }}
            whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ duration: 0.5, delay: 0.15 + i * 0.012, ease: EASE }}>
            <Link to={`/office/${o.id}`} aria-label={`${o.label}: ${MAPS[o.maps].label}`}
              className="block rounded-full p-0.5 transition-transform duration-300 hover:scale-125">
              <StatusDot status={o.maps} className="size-3.5" />
            </Link>
          </motion.li>
        ))}
      </ul>
      <ul className="mt-5 space-y-1.5 border-t border-rule pt-4 text-[13px] text-ink-2">
        {present.map((s) => (
          <li key={s} className="flex items-center gap-2.5">
            <StatusDot status={s} className="size-2.5" />
            <span className="flex-1">{MAPS[s].label}</span>
            <span className="tnum font-semibold text-ink">{offices.filter((o) => o.maps === s).length}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

/** A pill segmented control whose selection slides between options. Buttons with aria-pressed, as before. */
function SortControl({ sort, onChange, className }: { sort: Sort; onChange: (s: Sort) => void; className?: string }) {
  return (
    <div role="group" aria-label="Sort offices" className={cn("inline-flex rounded-full border border-rule/80 bg-card/70 p-1 shadow-[var(--shadow-soft)]", className)}>
      {SORTS.map((s) => {
        const on = sort === s.id;
        return (
          <button key={s.id} type="button" onClick={() => onChange(s.id)} aria-pressed={on}
            className={cn("relative isolate rounded-full px-3.5 py-1.5 text-[13px] font-medium transition-colors duration-300", on ? "text-paper" : "text-ink-2 hover:text-ink")}>
            {on && <motion.span layoutId="offices-sort" aria-hidden className="absolute inset-0 -z-10 rounded-full bg-brand shadow-sm" transition={{ type: "spring", stiffness: 420, damping: 38 }} />}
            <span className="sm:hidden">{s.short}</span><span className="max-sm:hidden">{s.label}</span>
          </button>
        );
      })}
    </div>
  );
}

/** Problem reviews as a count over the recent reviews read, with a thin bar. Right-aligned so the counts line up. */
function Reviews({ o }: { o: OfficeSummary }) {
  if (!o.sampled) return <span className="text-[13px] text-muted">Not sampled</span>;
  if (!o.enough_evidence) return <span className="text-[13px] text-muted">Too few ({o.window_reviews})</span>;
  return (
    <span className="inline-flex items-center gap-3" aria-label={`${o.problem_reviews} of ${o.window_reviews} recent reviews report a problem`}>
      <Bar value={o.problem_reviews} max={o.window_reviews} tone="bg-broken" className="w-10" />
      <span className="tnum min-w-[3.25rem] text-right text-sm text-ink">{o.problem_reviews}<span className="text-muted"> / {o.window_reviews}</span></span>
    </span>
  );
}

function Score({ score }: { score: number | null }) {
  if (score === null) return <span className="text-[13px] text-muted">Not scored</span>;
  return (
    <span className="inline-flex items-center gap-3">
      <Bar value={score} max={100} tone="bg-brand" className="w-10" />
      <span className="tnum min-w-[1.75rem] text-right text-[15px] font-semibold text-ink">{score}</span>
    </span>
  );
}

const Breach = ({ n }: { n: number }) => (
  <span className="mt-1 flex items-center gap-1.5 text-xs font-medium text-broken"><span className="size-1.5 rounded-full bg-broken" aria-hidden />{n} possible breach{n > 1 ? "es" : ""}</span>
);

/** What the Google Maps listing shows: the verdict, and the number it shows if any. */
const Maps = ({ o }: { o: OfficeSummary }) => (
  <span className="flex flex-col items-start gap-1">
    <Chip tone={MAPS[o.maps].tone}>{MAPS[o.maps].short}</Chip>
    {o.phone && <Mono className="tnum text-xs text-ink-2">{o.phone}</Mono>}
  </span>
);

/** A column header that sorts. aria-sort sits on the <th>; the arrow shows the active column and its direction. */
function SortHead({ id, sort, onChange, align = "left", children }: { id: Sort; sort: Sort; onChange: (s: Sort) => void; align?: "left" | "right"; children: ReactNode }) {
  const on = sort === id;
  const Icon = on ? (DESCENDING[id] ? ArrowDown : ArrowUp) : ChevronsUpDown;
  return (
    <th scope="col" aria-sort={on ? (DESCENDING[id] ? "descending" : "ascending") : "none"} className={cn(TH, align === "right" && "text-right")}>
      <button type="button" onClick={() => onChange(id)}
        className={cn("-mx-1.5 -my-0.5 inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 transition-colors hover:bg-ink/[0.05] hover:text-ink", on && "text-ink", align === "right" && "flex-row-reverse")}>
        {children}<Icon className={cn("size-3.5", on ? "text-brand" : "opacity-50")} aria-hidden />
      </button>
    </th>
  );
}

const TH = "border-b border-rule px-4 py-3 text-left text-xs font-medium text-muted first:pl-6 last:pr-6";
const TD = "border-b border-rule/70 px-4 py-4 align-middle first:pl-6 last:pr-6 group-last:border-b-0";

/** Wide screens (1280px and up, where every column fits): a real table, sortable from its headers. The office name's link covers the whole row. */
function OfficeTable({ rows, sort, onChange }: { rows: OfficeSummary[]; sort: Sort; onChange: (s: Sort) => void }) {
  return (
    <div className="surface mt-8 hidden overflow-clip rounded-[1.5rem] xl:block">
      <table className="w-full border-separate border-spacing-0 text-sm">
        <caption className="sr-only">Every office, with what Google shows for it</caption>
        <colgroup><col /><col className="w-[11rem]" /><col className="w-[12.5rem]" /><col className="w-[12rem]" /><col className="w-[10.5rem]" /><col className="w-[9rem]" /></colgroup>
        <thead>
          <tr>
            <SortHead id="name" sort={sort} onChange={onChange}>Office</SortHead>
            <th scope="col" className={TH}>Official number</th>
            <th scope="col" className={TH}>Google Maps shows</th>
            <th scope="col" className={TH}>Google's AI Overview leads with</th>
            <SortHead id="problems" sort={sort} onChange={onChange} align="right">Reported problems</SortHead>
            <SortHead id="score" sort={sort} onChange={onChange} align="right">Listing score</SortHead>
          </tr>
        </thead>
        <LayoutGroup>
          <tbody>
            {rows.map((o) => (
              <motion.tr key={o.id} layout="position" transition={{ type: "spring", stiffness: 400, damping: 40 }}
                className="group relative transition-colors duration-200 hover:bg-wash/50 has-[a:focus-visible]:bg-wash/50">
                <td className={TD}>
                  <Link to={`/office/${o.id}`} className="font-semibold text-ink outline-none transition-colors after:absolute after:inset-0 group-hover:text-brand focus-visible:text-brand">{o.label}</Link>
                  {o.breaches > 0 && <Breach n={o.breaches} />}
                </td>
                <td className={TD}><Mono className="tnum whitespace-nowrap text-[13px] text-ink-2">{o.official || "None published"}</Mono></td>
                <td className={TD}><Maps o={o} /></td>
                <td className={TD}><Chip tone={AI[o.ai].tone}>{AI[o.ai].short}</Chip></td>
                <td className={cn(TD, "text-right")}><Reviews o={o} /></td>
                <td className={cn(TD, "text-right")}><Score score={o.score} /></td>
              </motion.tr>
            ))}
          </tbody>
        </LayoutGroup>
      </table>
    </div>
  );
}

/** Narrow screens: one stacked row per office in a single card, the score kept beside the name. */
function OfficeList({ rows }: { rows: OfficeSummary[] }) {
  return (
    <LayoutGroup>
      <ul className="surface mt-6 overflow-clip rounded-[1.5rem] xl:hidden">
        {rows.map((o) => (
          <motion.li key={o.id} layout="position" transition={{ type: "spring", stiffness: 400, damping: 40 }} className="border-b border-rule/70 last:border-b-0">
            <Link to={`/office/${o.id}`} className="group block px-4 py-4 transition-colors hover:bg-wash/50 focus-visible:bg-wash/50 sm:px-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-semibold leading-snug text-ink transition-colors group-hover:text-brand">{o.label}</p>
                  {o.breaches > 0 && <Breach n={o.breaches} />}
                </div>
                <div className="shrink-0 pt-0.5 text-right">
                  {o.score === null ? <span className="text-[13px] text-muted">Not scored</span>
                    : <p className="tnum text-[15px] font-semibold leading-none text-ink">{o.score}<span className="text-xs font-normal text-muted"> /100</span></p>}
                  <p className="mt-1 text-[11px] text-muted">Listing score</p>
                </div>
              </div>
              <dl className="mt-3.5 grid grid-cols-2 gap-x-4 gap-y-3 text-[13px] sm:grid-cols-4">
                <div className="min-w-0"><dt className="text-xs text-muted">Official number</dt><dd className="mt-1"><Mono className="tnum text-ink-2">{o.official || "None published"}</Mono></dd></div>
                <div className="min-w-0"><dt className="text-xs text-muted">Google Maps shows</dt><dd className="mt-1"><Maps o={o} /></dd></div>
                <div className="min-w-0"><dt className="text-xs text-muted">Google's AI Overview leads with</dt><dd className="mt-1"><Chip tone={AI[o.ai].tone}>{AI[o.ai].short}</Chip></dd></div>
                <div className="min-w-0"><dt className="text-xs text-muted">Reported problems</dt><dd className="mt-1"><Reviews o={o} /></dd></div>
              </dl>
            </Link>
          </motion.li>
        ))}
      </ul>
    </LayoutGroup>
  );
}

function Loading({ error }: { error: string | null }) {
  return (
    <main className="mx-auto max-w-7xl px-4 pt-14 sm:px-6" aria-busy={!error}>
      {error ? (
        <div className="max-w-xl">
          <p className="headline text-4xl">The report cards didn't load.</p>
          <p className="mt-4 text-ink-2">Reloading the page usually fixes this. The data itself is saved and unchanged.</p>
        </div>
      ) : (
        <div className="animate-pulse space-y-6" aria-label="Loading the report cards">
          <div className="h-11 w-full max-w-md rounded-full bg-paper-2" />
          <div className="h-24 w-full max-w-4xl rounded-3xl bg-paper-2" />
          <div className="h-24 w-full max-w-2xl rounded-3xl bg-paper-2" />
        </div>
      )}
    </main>
  );
}

export default function Offices() {
  const { data, error } = useJSON<Overview>("/api/overview");
  const reduce = useReducedMotion();
  const [params, setParams] = useSearchParams();
  const asked = params.get("type") ?? "";
  // An unknown ?type= falls back to the first office type rather than a blank page.
  const type = data ? (asked in data.types ? asked : Object.keys(data.types)[0] ?? "") : "";
  const [sort, setSort] = useState<Sort>("score");
  // Stuck once the line just above the switcher has scrolled up under the nav.
  const sentinel = useRef<HTMLDivElement>(null);
  const [stuck, setStuck] = useState(false);
  useEffect(() => {
    const check = () => { const el = sentinel.current; if (el) setStuck(el.getBoundingClientRect().bottom <= 77); };
    check();
    addEventListener("scroll", check, { passive: true });
    addEventListener("resize", check);
    return () => { removeEventListener("scroll", check); removeEventListener("resize", check); };
  }, [data]);
  const t = data?.types[type];
  useTitle("Offices");
  const all = useMemo(() => (data?.offices ?? []).filter((o) => o.type === type), [data, type]);
  const rows = useMemo(() => {
    const by: Record<Sort, (a: OfficeSummary, b: OfficeSummary) => number> = {
      score: (a, b) => (a.score ?? 999) - (b.score ?? 999),
      problems: (a, b) => share(b) - share(a),
      name: (a, b) => a.label.localeCompare(b.label),
    };
    return [...all].sort(by[sort]);
  }, [all, sort]);
  if (!data || !t) return <Loading error={error} />;
  const h = t.headline;
  const stats: [number, number | null, string][] = [
    [h.listing_unclaimed, h.listed, "listings no verified owner manages"],
    [h.ai_overviews - h.ai_first_number_right, h.ai_overviews, "AI Overviews not leading with the office's own number"],
    [h.listing_phone_not_in_directory, h.listing_phone_shown, "numbers on listings that aren't in the department's directory"],
    [h.recent_breaches, null, "possible statutory breaches reported in the last two years"],
  ];

  return (
    <main>
      {/* The type switcher sticks just under the floating nav as you scroll, and glides to the centre beneath it. */}
      <div ref={sentinel} aria-hidden className="h-10 sm:h-14" />
      <section className="sticky top-[4.75rem] z-30 mx-auto max-w-7xl px-4 sm:px-6">
        <div className={cn("flex", stuck ? "justify-center" : "justify-start")}>
          <motion.div layout={!reduce} transition={{ type: "spring", stiffness: 260, damping: 32 }}
            className={cn("w-full rounded-full transition-shadow duration-500 sm:w-auto", stuck && "shadow-[var(--shadow-float)]")}>
          <TabList idBase="offices" label="Office type" value={type} onChange={(id) => setParams({ type: id })}
            className={cn("grid w-full grid-cols-[auto_1fr_auto] rounded-full border border-rule/80 p-1 sm:inline-flex sm:w-auto", stuck ? "glass" : "bg-card/70 shadow-[var(--shadow-soft)]")}
            indicator="rounded-full bg-brand shadow-sm"
            tabs={Object.entries(data.types).map(([id, info]) => ({ id, label: capital(info.profile.plural) }))}
            renderTab={(tab, on) => (
              <span className="flex items-center justify-center gap-2">
                <span className="sm:hidden">{tab.label.split(" ")[0]}</span><span className="max-sm:hidden">{tab.label}</span>
                <span className={cn("tnum rounded-full px-1.5 text-[11px] font-semibold transition-colors", on ? "bg-paper/20 text-paper" : "bg-paper-2 text-muted")}>
                  {data.types[tab.id].headline.offices}
                </span>
              </span>
            )}
            tabClass={(on) => cn("whitespace-nowrap rounded-full px-3 py-2 text-[13px] font-medium transition-colors duration-300 sm:px-4", on ? "text-paper" : "text-ink-2 hover:text-ink")} />
          </motion.div>
        </div>
      </section>

      <div {...panelProps("offices", type)} className="outline-none">
        <section className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)] lg:items-end lg:gap-14">
            <div>
              <Reveal key={type} y={18}>
                <h1 className="headline mt-12 sm:mt-16 max-w-[15ch] text-[clamp(2.5rem,6vw,5.5rem)] leading-[0.98] tracking-[-0.035em]">
                  <span className="text-broken">{h.listing_no_phone} of {h.listed}</span> {t.profile.short} listings on Google Maps show no phone number.
                </h1>
              </Reveal>
              <Reveal key={type + "p"} delay={0.08}>
                <p className="serif mt-8 max-w-[34ch] text-[1.4rem] leading-snug text-ink-2 sm:text-[1.6rem]">
                  The {t.profile.department} publishes {h.official_landline === h.offices ? "a landline" : "a phone number"} for every one of its {h.offices}.
                </p>
              </Reveal>
            </div>
            <Reveal key={type + "u"} delay={0.14}><UnitChart offices={all} /></Reveal>
          </div>

          <dl className="mt-14 grid grid-cols-2 border-y border-rule md:grid-cols-4">
            {stats.map(([v, of, label], i) => (
              <div key={label} className={cn("py-7 pr-4 md:px-6 md:first:pl-0", i % 2 === 1 && "max-md:border-l max-md:border-rule max-md:pl-4",
                i > 1 && "max-md:border-t max-md:border-rule", i > 0 && "md:border-l md:border-rule")}>
                <dt className="sr-only">{label}</dt>
                <dd>
                  <p className="serif text-[clamp(2.4rem,4.4vw,3.4rem)] leading-none tracking-[-0.03em]">
                    <CountUp value={v} />{of !== null && <span className="text-[0.55em] text-muted"> / {of}</span>}
                  </p>
                  {of !== null && of > 0 && <Bar value={v} max={of} tone="bg-ink" className="mt-4 w-full max-w-36" />}
                  <p className="mt-3 max-w-[24ch] text-[13px] leading-snug text-ink-2" aria-hidden>{label}</p>
                </dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="mx-auto mt-16 max-w-7xl px-4 sm:mt-20 sm:px-6" aria-labelledby="by-office">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 id="by-office" className="headline text-[clamp(2rem,4vw,2.9rem)]">Office by office</h2>
              <p className="mt-2 text-sm text-muted">{rows.length} {t.profile.plural}, sorted by {SORTS.find((s) => s.id === sort)!.label.toLowerCase()}.</p>
            </div>
            <SortControl sort={sort} onChange={setSort} className="xl:hidden" />
          </div>

          <OfficeTable rows={rows} sort={sort} onChange={setSort} />
          <OfficeList rows={rows} />

          <div className="mt-8 flex max-w-3xl gap-3 text-sm leading-relaxed text-muted">
            <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
            <div className="space-y-2">
              {(h.sampled < h.listed || h.citizen_checked < h.offices) && (
                <p>{h.sampled < h.listed && `Reviews were read for the ${h.sampled} most-reviewed of these ${h.listed} listings. `}
                  {h.citizen_checked < h.offices && `Google Search and its AI answers were checked for ${h.citizen_checked} of the ${h.offices} offices; a search that kept failing is marked "not checked". `}
                  The rest say "not sampled" or "not checked".</p>
              )}
              <p>A possible breach is one person's account, not a rate.</p>
              <p>Listing score: six checks of the Google Maps listing, 0 to 100. It measures what citizens find on Google, not the quality of the office.{" "}
                <Link className="font-medium text-ink-2 underline decoration-rule underline-offset-4 transition hover:decoration-ink-2" to="/method">How it's measured</Link></p>
            </div>
          </div>
        </section>
      </div>
      <Footer asOf={data.totals.as_of} searches={data.totals.searches} />
    </main>
  );
}
