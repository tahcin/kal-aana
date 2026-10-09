// The SerpApi engines this app uses, in plain words, and a media-query hook.
import { useSyncExternalStore } from "react";
import type { Engine } from "./api";

export const ENGINE: Record<Engine, { name: string; does: string }> = {
  google_maps: { name: "Google Maps", does: "Finds each office's listing: its phone, whether anyone manages it, its rating" },
  google_maps_reviews: { name: "Google Maps Reviews", does: "Reads what citizens report about waits, phones and agents" },
  google: { name: "Google Search", does: "Searches the way a citizen would, and records what shows first" },
  google_ai_overview: { name: "Google AI Overview", does: "Fetches Google's AI answer in full, with the sources it cites" },
  google_ai_mode: { name: "Google AI Mode", does: "Asks Google's AI Mode the same question, to compare its answer" },
  bing_maps: { name: "Bing Maps", does: "Looks the office up outside Google, to see if the gap is Google's alone" },
  google_news: { name: "Google News", does: "Finds recent reports, such as a portal outage, when a citizen asks in the chat" },
};

/** True when the media query matches; follows changes (for example a rotated phone). */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (notify) => { const m = matchMedia(query); m.addEventListener("change", notify); return () => m.removeEventListener("change", notify); },
    () => matchMedia(query).matches,
    () => false,
  );
}
