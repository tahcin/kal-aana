import { Command } from "cmdk";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowUpRight, Menu as MenuIcon, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from "react-router";
import { apiUrl, useJSON, type Overview } from "../lib/api";
import { WORDMARKS } from "../lib/wordmarks";
import { MAPS, cn, toneBg } from "../lib/ui";

export function OfficeSearch({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const { data } = useJSON<Overview>("/api/overview");
  const navigate = useNavigate();
  const go = (to: string) => { onOpenChange(false); navigate(to); };
  const kbd = "inline-grid h-5 min-w-5 place-items-center rounded-md border border-rule bg-card px-1 font-mono text-[10px] text-ink-2 shadow-[0_1px_0_var(--color-rule)]";
  const heading = "[&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:flex [&_[cmdk-group-heading]]:items-center [&_[cmdk-group-heading]]:gap-2 [&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pb-1.5 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:text-muted";
  const item = "group flex cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-ink-2 transition-colors duration-150 data-[selected=true]:bg-wash data-[selected=true]:text-ink";
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        {/* Enter transitions use @starting-style (Tailwind's starting: variant), so no animation library is needed here. */}
        <Dialog.Overlay className="fixed inset-0 z-50 bg-ink/25 backdrop-blur-[3px] transition-opacity duration-300 starting:opacity-0" />
        <Dialog.Content className="fixed left-1/2 top-[12vh] bg-card/[0.93] backdrop-blur-2xl backdrop-saturate-150 z-50 w-[min(660px,calc(100vw-1.5rem))] -translate-x-1/2 overflow-hidden rounded-[1.6rem] border border-rule/80 shadow-[var(--shadow-float)] outline-none transition-[opacity,transform,scale] duration-300 ease-[var(--ease-out-expo)] starting:scale-[0.97] starting:opacity-0">
          <Dialog.Title className="sr-only">Find an office</Dialog.Title>
          <Dialog.Description className="sr-only">Type an office name or code, then press Enter to open its page.</Dialog.Description>
          <Command label="Find an office" className="flex flex-col" loop>
            <div className="flex items-center gap-3 border-b border-rule/80 px-5">
              <Search className="size-[18px] shrink-0 text-brand" aria-hidden />
              <Command.Input autoFocus placeholder="Find an office: KA-05, Yelahanka, Basavanagudi" className="h-[3.75rem] min-w-0 flex-1 bg-transparent text-[1.05rem] text-ink outline-none placeholder:text-muted" />
              <button type="button" onClick={() => onOpenChange(false)} className={cn(kbd, "cursor-pointer px-1.5 hover:text-ink")} aria-label="Close">esc</button>
            </div>
            <Command.List className="max-h-[min(56vh,480px)] scroll-py-2 overflow-y-auto overscroll-contain px-2 pb-2">
              <Command.Empty className="px-6 py-12 text-center">
                <span className="serif block text-2xl text-ink">No office matches.</span>
                <span className="mt-1 block text-sm text-muted">Try a code like KA-03, or part of a name.</span>
              </Command.Empty>
              {!data && <Command.Loading><p className="px-3 py-6 text-sm text-muted">Loading offices…</p></Command.Loading>}
              {data && Object.entries(data.types).map(([type, t]) => (
                <Command.Group key={type} heading={t.profile.plural[0].toUpperCase() + t.profile.plural.slice(1)} className={heading}>
                  {data.offices.filter((o) => o.type === type).map((o) => (
                    <Command.Item key={o.id} value={`${o.label} ${o.id}`} onSelect={() => go(`/office/${o.id}`)} className={item}>
                      <span className={cn("size-2.5 shrink-0 rounded-full ring-4 ring-transparent transition group-data-[selected=true]:ring-current/10",
                        o.maps === "no_listing" ? "border-2 border-broken" : toneBg[MAPS[o.maps].tone])} aria-hidden />
                      <span className="min-w-0 flex-1 truncate font-medium">{o.label}</span>
                      <span className="hidden text-xs text-muted sm:inline">{MAPS[o.maps].short}</span>
                      {o.score !== null && <span className="tnum w-7 text-right font-mono text-[11px] text-muted" title="Listing score">{o.score}</span>}
                      <span className={cn(kbd, "opacity-0 transition-opacity group-data-[selected=true]:opacity-100")} aria-hidden>↵</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              ))}
              <Command.Group heading="Pages" className={heading}>
                {nav.map((n) => (
                  <Command.Item key={n.to} value={`page ${n.label}`} onSelect={() => go(n.to)} className={item}>
                    <span className="size-2.5 shrink-0 rounded-full bg-brand/30" aria-hidden />
                    <span className="flex-1 font-medium">{n.label}</span>
                    <span className={cn(kbd, "opacity-0 transition-opacity group-data-[selected=true]:opacity-100")} aria-hidden>↵</span>
                  </Command.Item>
                ))}
              </Command.Group>
            </Command.List>
            <div className="flex items-center gap-4 border-t border-rule/80 bg-paper-2/40 px-5 py-2.5 text-[11.5px] text-muted">
              <span className="flex items-center gap-1.5"><kbd className={kbd}>↑</kbd><kbd className={kbd}>↓</kbd> move</span>
              <span className="flex items-center gap-1.5"><kbd className={kbd}>↵</kbd> open</span>
              <span className="hidden items-center gap-1.5 sm:flex"><kbd className={kbd}>esc</kbd> close</span>
              <span className="ml-auto hidden items-center gap-3 sm:flex">
                {(["no_phone", "other", "official"] as const).map((s) => (
                  <span key={s} className="flex items-center gap-1.5"><span className={cn("size-1.5 rounded-full", toneBg[MAPS[s].tone])} aria-hidden />{MAPS[s].short}</span>
                ))}
              </span>
            </div>
          </Command>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const nav = [
  { to: "/", label: "Ask", end: true, note: "Describe your problem, get the evidence" },
  { to: "/map", label: "Map", note: "Every office, and what Google shows for it" },
  { to: "/offices", label: "Offices", note: "Report cards, office by office" },
  { to: "/method", label: "Method", note: "How the data was gathered and checked" },
];

const HOME_TITLE = document.title;  // the title in index.html, restored on the chat
const ease = [0.16, 1, 0.3, 1] as const;

/** The wordmark: "Kal Aana" hand-lettered, as outlines (src/lib/wordmarks.ts). With `cycle` it turns between English
 *  and Kannada, the old word wiped away and the new one written in, left to right, like a pen (index.css); the box keeps the widest one's width, so nothing beside it moves. Size it by height. */
export function Wordmark({ className, cycle }: { className?: string; cycle?: boolean }) {
  const reduce = useReducedMotion();
  // `turn` counts changes, so each new word mounts fresh and plays its writing-in once; the first word just sits there.
  const [turn, setTurn] = useState(0);
  useEffect(() => {
    if (!cycle || reduce) return;
    const t = setInterval(() => { if (!document.hidden) setTurn((n) => n + 1); }, 4200);
    return () => clearInterval(t);
  }, [cycle, reduce]);
  const marks = cycle ? WORDMARKS : WORDMARKS.slice(0, 1);
  const shown = turn % marks.length, leaving = turn ? (turn - 1) % marks.length : -1;
  return (
    <span role="img" aria-label="Kal Aana" className={cn("inline-grid items-center justify-items-start", className)}>
      {marks.map((m, n) => (
        // Every word stays in the box (the idle one invisible), so the box keeps the widest word's width from the first
        // paint and nothing beside it shifts. Kannada sits a little smaller, so its vowel signs match the English size.
        <svg key={`${m.lang}-${n === shown ? turn : n === leaving ? turn - 1 : "idle"}`} viewBox={`0 0 ${m.w} ${m.h}`} aria-hidden
          className={cn("col-start-1 row-start-1 w-auto", m.lang === "en" ? "h-full" : "h-[80%]",
            n !== shown && n !== leaving ? "invisible" : turn > 0 && (n === shown ? "wm-write" : "wm-erase"))}>
          <path fill="currentColor" d={m.d} />
        </svg>
      ))}
    </span>
  );
}

/** The desktop links: the current page sits in a violet pill that slides between links, and a soft one follows the pointer. */
function NavLinks() {
  const [hover, setHover] = useState<string | null>(null);
  return (
    <div className="relative flex items-center" onPointerLeave={() => setHover(null)}>
      {nav.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.end} onPointerEnter={() => setHover(n.to)}
          className={({ isActive }) => cn("relative rounded-full px-4 py-2 text-[14.5px] font-medium transition-colors duration-300",
            isActive ? "text-paper" : "text-ink-2 hover:text-ink")}>
          {({ isActive }) => (
            <>
              {hover === n.to && !isActive && (
                <motion.span layoutId="nav-hover" className="absolute inset-0 rounded-full bg-ink/[0.06]" transition={{ type: "spring", bounce: 0.15, duration: 0.45 }} />
              )}
              {isActive && <motion.span layoutId="nav-active" className="absolute inset-0 rounded-full bg-brand shadow-[0_6px_16px_-8px_var(--color-brand)]" transition={{ type: "spring", bounce: 0.18, duration: 0.55 }} />}
              <span className="relative">{n.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </div>
  );
}

/** Phones: one Menu button opens a full-screen sheet with big links and search. */
function MobileMenu({ open, onOpenChange, onSearch }: { open: boolean; onOpenChange: (v: boolean) => void; onSearch: () => void }) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Trigger className="flex h-10 items-center gap-2 rounded-full bg-brand pl-4 pr-3.5 text-sm font-medium text-paper shadow-[0_6px_16px_-8px_var(--color-brand)] transition active:scale-95">
        Menu<MenuIcon className="size-4" aria-hidden />
      </Dialog.Trigger>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Content forceMount aria-describedby={undefined} className="fixed inset-0 z-50 outline-none">
              {/* One clipped layer holds everything, so the whole sheet grows from the Menu button and shrinks back into it together. */}
              <motion.div className="absolute inset-0 flex flex-col overflow-y-auto bg-paper px-5 pb-8 pt-4"
                initial={{ clipPath: "circle(0% at 84% 6%)" }} animate={{ clipPath: "circle(150% at 84% 6%)" }}
                exit={{ clipPath: "circle(0% at 84% 6%)", transition: { duration: 0.38, ease: [0.7, 0, 0.84, 0] } }}
                transition={{ duration: 0.6, ease }}>
                <div className="flex h-12 items-center justify-between">
                  <Dialog.Title><Wordmark className="h-8 text-ink" /></Dialog.Title>
                  <Dialog.Close className="grid size-10 place-items-center rounded-full border border-rule bg-card text-ink" aria-label="Close menu"><X className="size-4" /></Dialog.Close>
                </div>
                <nav className="mt-10 flex-1" aria-label="Main">
                  {nav.map((n, i) => (
                    <motion.div key={n.to} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.15 } }}
                      transition={{ duration: 0.6, delay: 0.12 + i * 0.06, ease }}>
                      <NavLink to={n.to} end={n.end} onClick={() => onOpenChange(false)}
                        className={({ isActive }) => cn("group flex items-baseline justify-between gap-4 border-b border-rule py-5", isActive ? "text-brand" : "text-ink")}>
                        <span>
                          <span className="display block text-[2.6rem] leading-none tracking-[-0.03em]">{n.label}</span>
                          <span className="mt-2 block text-sm text-muted">{n.note}</span>
                        </span>
                        <ArrowUpRight className="size-5 shrink-0 text-muted transition-transform group-active:translate-x-0.5" aria-hidden />
                      </NavLink>
                    </motion.div>
                  ))}
                </nav>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }} transition={{ duration: 0.5, delay: 0.4 }}>
                  <button onClick={() => { onOpenChange(false); onSearch(); }} className="flex h-12 w-full items-center gap-2.5 rounded-full border border-rule bg-card px-5 text-[15px] text-muted">
                    <Search className="size-4" aria-hidden />Find an office
                  </button>
                </motion.div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

export function Shell() {
  const { pathname } = useLocation();
  useEffect(() => { if (pathname === "/") document.title = HOME_TITLE; }, [pathname]);
  const [searching, setSearching] = useState(false);
  const [menu, setMenu] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(scrollY > 24);
    onScroll();
    addEventListener("scroll", onScroll, { passive: true });
    return () => removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setSearching((s) => !s); } };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);
  return (
    <div className="min-h-dvh bg-paper text-ink">
      {/* A floating bar: open and airy at the top of the page, then it tightens into a frosted pill as you scroll. */}
      <header className="pointer-events-none sticky top-0 z-40 px-3 pt-2 sm:px-5 sm:pt-3">
        <div className={cn("pointer-events-auto mx-auto flex h-14 items-center gap-2 rounded-full border pl-4 pr-2 transition-[max-width,background-color,border-color,box-shadow] duration-700 ease-[var(--ease-out-expo)] sm:pl-5",
          scrolled ? "glass max-w-4xl border-rule/70 shadow-[var(--shadow-soft)]" : "max-w-7xl border-transparent")}>
          <NavLink to="/" className="group flex shrink-0 items-center rounded-lg" aria-label="Kal Aana home">
            <Wordmark cycle className="h-[30px] text-ink transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover:-rotate-2 sm:h-8" />
          </NavLink>
          <nav className="mx-auto hidden md:block" aria-label="Main"><NavLinks /></nav>
          <div className="ml-auto flex items-center gap-1.5 md:ml-0">
            <button onClick={() => setSearching(true)} aria-label="Find an office"
              className="group flex size-10 items-center justify-center gap-2 rounded-full text-sm text-muted transition hover:bg-ink/[0.06] hover:text-ink lg:w-auto lg:border lg:border-rule/80 lg:bg-card/70 lg:pl-3.5 lg:pr-2">
              <Search className="size-4" aria-hidden /><span className="hidden lg:inline">Find an office</span>
              <kbd className="hidden rounded-md border border-rule bg-paper px-1.5 py-0.5 font-sans text-[11px] text-muted lg:inline">⌘K</kbd>
            </button>
            <div className="md:hidden"><MobileMenu open={menu} onOpenChange={setMenu} onSearch={() => setSearching(true)} /></div>
          </div>
        </div>
      </header>
      <Outlet />
      <OfficeSearch open={searching} onOpenChange={setSearching} />
      <ScrollRestoration />
    </div>
  );
}

export function Footer({ asOf, searches }: { asOf?: string; searches?: number }) {
  const { data } = useJSON<Overview>("/api/overview");  // cached: every page already fetches it
  asOf ??= data?.totals.as_of;
  searches ??= data?.totals.searches;
  const link = "underline-offset-4 transition hover:text-ink hover:underline";
  return (
    <footer className="mt-32 border-t border-rule">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-12 text-sm text-muted sm:px-6 md:flex-row md:items-start md:justify-between">
        <div>
          <NavLink to="/" className="inline-flex items-center gap-2.5 text-ink">
            <Wordmark className="h-10 text-ink" />
          </NavLink>
          <p className="mt-5 flex flex-wrap gap-x-5 gap-y-2">
            <NavLink className={link} to="/">Ask</NavLink>
            <NavLink className={link} to="/map">Map</NavLink>
            <NavLink className={link} to="/offices">Every office</NavLink>
            <NavLink className={link} to="/method">Method</NavLink>
            <a className={link} href={apiUrl("/api/docs")}>JSON API</a>
            <a className={link} href="https://github.com/tahcin/kal-aana">GitHub</a>
          </p>
        </div>
        <p className="max-w-3xl leading-relaxed md:text-right">
          Data as of {asOf ?? "…"}: the Karnataka Transport Department, Department of Stamps and Registration and Passport Seva
          (Ministry of External Affairs) directories, the Sakala Service Compendium and the Passport Seva Citizen's Charter, and Google
          Maps, Maps Reviews, Search, AI Overview, AI Mode and Bing Maps results collected through{" "}
          <a className="underline underline-offset-2 hover:text-ink" href="https://serpapi.com">SerpApi</a>
          {searches ? ` (${searches} searches, each traceable by its search ID)` : ""}. Reviews are self-selected; names and unverified mobile numbers are masked.
          This reports on offices, not individuals. Kal Aana is an independent project and is not affiliated with any government department.
        </p>
      </div>
    </footer>
  );
}
