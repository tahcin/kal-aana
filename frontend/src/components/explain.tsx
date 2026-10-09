// Plain-language helpers for a first-time reader: a glossary term that opens a one-line definition
// (tap, hover or focus, so it works on phones; Escape, scrolling or tapping elsewhere closes it), and the
// chip that names the SerpApi search behind a finding.
import { Check, Copy } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { Engine } from "../lib/api";
import { cn } from "../lib/ui";

export const GLOSSARY = {
  rto: "Regional Transport Office: the government office that issues driving licences and registers vehicles.",
  subregistrar: "Sub-registrar office: the government office that registers property sales, marriages and other documents.",
  charter: "Passport offices are run by the central government, so the Sakala law doesn't cover them. The Ministry of External Affairs' Citizen's Charter sets their time limits, counted from the day complete documents are received.",
  sakala: "Karnataka's Sakala Services Act (2011) sets a legal deadline for many public services, most of them in working days.",
  working: "Days the office is open: not Sundays, the 2nd and 4th Saturdays or public holidays. Kal Aana's counts skip the first two but not holidays, so they can run a little high.",
  listing: "An office's page on Google Maps: its address, hours, phone number and reviews.",
  overview: "The AI-written answer Google shows above the search results.",
  mode: "Google's chat-style AI search, on its own tab. The AI Overview is the one on the normal results page.",
  unclaimed: "Google shows that no verified owner manages this listing.",
  cug: "Closed User Group: a mobile number the government issues to an officer's post, listed in the official directory.",
  directory: "The list of each office's phone numbers that the department publishes on its own website.",
  searchid: "SerpApi saves every search response under an ID, so each finding traces back to the exact search it came from.",
  pin: "The six-digit postal code. A different PIN means a different part of the city.",
} as const;

export type TermKey = keyof typeof GLOSSARY;

/** A word with a dotted underline that explains itself on tap, hover or focus. */
export function Term({ k, children }: { k: TermKey; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const ref = useRef<HTMLButtonElement>(null);
  const id = useId();
  useLayoutEffect(() => {
    if (!open || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const width = Math.min(288, innerWidth - 32);
    setPos({ left: Math.max(16, Math.min(r.left, innerWidth - width - 16)), top: r.bottom + 8 });
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    // Mobile Safari doesn't focus a tapped button, so blur alone wouldn't close it.
    const onDown = (e: PointerEvent) => { if (!ref.current?.contains(e.target as Node)) close(); };
    addEventListener("scroll", close, { passive: true });
    addEventListener("keydown", onKey);
    addEventListener("pointerdown", onDown);
    return () => { removeEventListener("scroll", close); removeEventListener("keydown", onKey); removeEventListener("pointerdown", onDown); };
  }, [open]);
  return (
    <>
      <button ref={ref} type="button" aria-describedby={open ? id : undefined} aria-expanded={open}
        onClick={() => setOpen(true)} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)} onBlur={() => setOpen(false)}
        className="cursor-help font-[inherit] text-inherit [letter-spacing:inherit] [text-transform:inherit] underline decoration-current/40 decoration-dotted decoration-2 underline-offset-[0.2em] transition-colors hover:decoration-pop">
        {children}
      </button>
      {open && pos && (
        <span id={id} role="tooltip" style={{ left: pos.left, top: pos.top }}
          className="fixed z-50 w-[min(18rem,calc(100vw-2rem))] rounded-2xl bg-ink px-4 py-3 text-left font-sans text-sm font-normal leading-snug tracking-normal text-paper shadow-[var(--shadow-float)] normal-case">
          {GLOSSARY[k]}
        </span>
      )}
    </>
  );
}

/** The SerpApi engine and search ID behind one piece of evidence, with a copy button. */
export function SearchId({ engine, id, className }: { engine: Engine; id: string; className?: string }) {
  const [copied, setCopied] = useState<"yes" | "no" | null>(null);
  const copy = () => {
    const done = (ok: boolean) => { setCopied(ok ? "yes" : "no"); setTimeout(() => setCopied(null), 1600); };
    try { navigator.clipboard.writeText(id).then(() => done(true), () => done(false)); } catch { done(false); }  // no clipboard on plain http
  };
  return (
    <span className={cn("inline-flex max-w-full items-center gap-2 rounded-full border border-rule/80 bg-paper/70 py-0.5 pl-3 pr-0.5 text-[11px] font-medium text-muted", className)}>
      <span className="font-semibold text-brand">SerpApi</span>
      <span className="whitespace-nowrap font-mono">engine=<span className="text-ink-2">{engine}</span></span>
      <span className="h-3 w-px shrink-0 bg-rule" aria-hidden />
      <span className="truncate font-mono" title={`Search ID ${id}`}><span className="sr-only">search ID </span>{id}</span>
      <button type="button" onClick={copy} aria-label={`Copy search ID ${id}`}
        className="grid size-6 shrink-0 place-items-center rounded-full transition hover:bg-wash hover:text-brand">
        {copied === "yes" ? <Check className="size-3.5 text-kept" aria-hidden /> : <Copy className="size-3.5" aria-hidden />}
      </button>
      <span className="sr-only" aria-live="polite">{copied === "yes" ? "Copied" : copied === "no" ? "Couldn't copy; select the ID instead" : ""}</span>
    </span>
  );
}
