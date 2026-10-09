// What the home page's pieces share: the example questions, a quiet focus, and the office the story features.
import { Bike, MapPin, MessageSquareWarning, Plane } from "lucide-react";
import type { OfficeSummary } from "../../lib/api";

export const EXAMPLES = [
  { q: "Applied for my learner's licence at RTO South 3 weeks ago, still waiting", topic: "Learner's licence", icon: Bike },
  { q: "How do I reach the Jayanagar sub-registrar office?", topic: "Reach an office", icon: MapPin },
  { q: "Are agents or bribes reported at the Varthur sub-registrar office?", topic: "Agents and bribes", icon: MessageSquareWarning },
  { q: "Passport re-issue at PSK Lalbagh, applied on 10 September", topic: "Passport re-issue", icon: Plane },
];

/** Focus without scrolling, and only where there's a real keyboard: on a phone it would pop the keyboard over the page. */
export function focusQuietly(el: HTMLElement | null) {
  if (el && matchMedia("(hover: hover) and (pointer: fine)").matches) el.focus({ preventScroll: true });
}

/** The office whose answer the globe folds into: one Maps shows no phone for, where Google's AI got it right. */
export const featured = (offices: OfficeSummary[]) =>
  offices.find((o) => o.maps === "no_phone" && o.ai === "own" && o.official) ?? offices.find((o) => o.official) ?? offices[0];
