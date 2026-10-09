import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { AIStatus, MapsStatus, Verdict } from "./api";

export const cn = (...inputs: ClassValue[]) => twMerge(clsx(inputs));

export type Tone = "broken" | "kept" | "amber" | "unknown";

export const VERDICT: Record<Verdict, { tone: Tone; label: string }> = {
  "this office": { tone: "kept", label: "The office's own number" },
  "regional office": { tone: "amber", label: "The regional passport office's number" },
  "another office": { tone: "broken", label: "Another office's number" },
  "not in the directory": { tone: "amber", label: "Not in the department's directory" },
  "national helpline": { tone: "amber", label: "A national helpline queue" },
  "department helpline": { tone: "amber", label: "A department-wide helpline" },
};

export const MAPS: Record<MapsStatus, { tone: Tone; label: string; short: string }> = {
  no_phone: { tone: "broken", label: "No phone on Google Maps", short: "No phone" },
  no_listing: { tone: "broken", label: "No listing found", short: "No listing" },
  other: { tone: "amber", label: "A number not in the department's directory", short: "Not in directory" },
  helpline: { tone: "amber", label: "A helpline, not the office's own number", short: "Helpline" },
  official: { tone: "kept", label: "The office's own number", short: "Own number" },
};

export const AI: Record<AIStatus, { tone: Tone; label: string; short: string }> = {
  own: { tone: "kept", label: "Leads with the office's own number", short: "Own number" },
  helpline: { tone: "amber", label: "Leads with a helpline, not the office's number", short: "A helpline" },
  other: { tone: "broken", label: "Leads with a different number", short: "A different number" },
  no_answer: { tone: "amber", label: "An AI answer with no number in it", short: "No number given" },
  no_ai: { tone: "unknown", label: "No AI answer shown", short: "No AI answer" },
  unchecked: { tone: "unknown", label: "Not checked", short: "Not checked" },
};

/** "Transport Department's", "Ministry of External Affairs'". */
export const possessive = (name: string) => name + (name.endsWith("s") ? "'" : "'s");


export const toneText: Record<Tone, string> = { broken: "text-broken", kept: "text-kept", amber: "text-amber", unknown: "text-unknown" };
export const toneBg: Record<Tone, string> = { broken: "bg-broken", kept: "bg-kept", amber: "bg-amber", unknown: "bg-unknown" };
export const toneSoft: Record<Tone, string> = {
  broken: "bg-broken-soft text-broken", kept: "bg-kept-soft text-kept", amber: "bg-amber-soft text-amber", unknown: "bg-unknown-soft text-muted",
};

/** Only http(s), tel: and mailto: links leave the app. */
export const safeUrl = (url?: string | null) => (url && /^(https?:\/\/|tel:|mailto:)/.test(url) ? url : undefined);

/** Split text around marks (numbers, PINs) so they can be highlighted; never inserts HTML. */
export function splitMarks(text: string, marks: string[]): { text: string; mark: boolean }[] {
  const words = [...new Set(marks.filter(Boolean))].sort((a, b) => b.length - a.length);
  if (!words.length) return [{ text, mark: false }];
  const re = new RegExp("(" + words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "gi");
  return text.split(re).filter((p) => p !== "").map((p) => ({ text: p, mark: words.some((w) => w.toLowerCase() === p.toLowerCase()) }));
}

export function excerpt(text: string, evidence = "", limit = 320): string {
  if (text.length <= limit) return text;
  const at = Math.max(0, text.toLowerCase().indexOf(evidence.toLowerCase()));
  const start = Math.max(0, Math.min(at - limit / 3, text.length - limit));
  return (start ? "…" : "") + text.slice(start, start + limit).trim() + (start + limit < text.length ? "…" : "");
}
