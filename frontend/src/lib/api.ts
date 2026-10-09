// Types for the JSON the Python app serves (kalaana/views.py builds it, kalaana/web.py routes it). Everything here is computed from
// the committed snapshots; the frontend only presents it.
import { useEffect, useState } from "react";

export type MapsStatus = "no_listing" | "no_phone" | "official" | "helpline" | "other";
export type AIStatus = "own" | "helpline" | "other" | "no_answer" | "unchecked";
export type Verdict = "this office" | "regional office" | "another office" | "not in the directory" | "national helpline" | "department helpline";

export interface Totals {
  offices: number; listed: number; no_phone: number; official: number; unclaimed: number;
  ai: number; ai_right: number; citizen_checked: number; searches: number; as_of: string;
  ai_mode: number; ai_mode_right: number; bing_found: number; bing_no_phone: number; bing_official: number;
}
export interface Profile { label: string; short: string; plural: string; department: string; officer: string; review_queries: string[]; directory_url: string;
  promise?: string; promise_name?: string }
export interface Headline {
  offices: number; official_phone: number; official_landline: number; listed: number; not_found: string[]; listing_no_phone: number; listing_official_phone: number;
  listing_phone_shown: number; listing_phone_not_in_directory: number; listing_unclaimed: number; ai_overviews: number;
  ai_first_number_right: number; ai_address_wrong: string[]; citizen_checked: number; sampled: number; recent_breaches: number;
  shared_listing_numbers: { display: string; offices: string[]; names: string[] }[];
  ai_mode_answers: number; ai_mode_first_number_right: number; ai_mode_address_wrong: string[];
  bing_checked: number; bing_found: number; bing_no_phone: number; bing_official_phone: number;
}
export interface OfficeSummary {
  id: string; label: string; code: string; type: string; type_label: string; maps: MapsStatus; ai: AIStatus;
  score: number | null; official: string; phone: string; unclaimed: boolean; reviews: number; sampled: boolean; checked: boolean;
  enough_evidence: boolean; problem_reviews: number; window_reviews: number; breaches: number;
}
export interface MapPoint {
  id: string; label: string; type: string; type_label: string; lat: number | null; lng: number | null; status: MapsStatus;
  ai: AIStatus; phone: string; score: number | null; unclaimed: boolean; reviews: number;
  mode: AIStatus; bing: "own" | "other" | "no_phone" | "not_found" | null;
}
export interface Overview {
  totals: Totals;
  types: Record<string, { profile: Profile; headline: Headline; searches: number; searches_by_engine: Record<string, number>; as_of: string;
    lookalikes: { title: string; category: string; pincode: string; reviews: number; lat: number | null; lng: number | null }[];
    rules: { issue_window_days: number; min_sample: number; recent_days: number; breach_margin_pct: number } }>;
  offices: OfficeSummary[];
  points: MapPoint[];
  links: { display: string; ids: string[]; names: string[] }[];
}
export interface Found { display: string; where: string; verdict: Verdict; detail: string; also?: string }
export interface Clock {
  service: string; limit_days: number; limit: string; reported_days: number | null; said?: string; date?: string;
  link?: string; citation: string; quote?: string; evidence?: string; rating?: number | null; conversion?: string;
  search_id?: string | null; note?: string; terms?: string;
}
export type Engine = "google" | "google_ai_overview" | "google_ai_mode" | "google_maps" | "google_maps_reviews" | "bing_maps" | "google_news";
export interface Search { engine: Engine; purpose: string; search_id: string }
export interface StoryCard {
  id: string; label: string; type: string; department: string;
  official: { display: string; label: string; tel: string }[]; email: string; source_url: string;
  maps: { title: string; rating: number | null; reviews: number; phone: string | null; unclaimed: boolean; url: string; search_id: string } | null;
  ai: { query: string; text: string; marks: string[]; good_marks: string[]; searched_on: string; search_id: string;
        address_matches: boolean | null; pincodes: string[]; official_pin: string; overview_search_id: string | null;
        sources: { title: string; domain: string }[] } | null;
  query: string | null; found: Found[]; clock: Clock; verdict: string[]; checked: boolean; sampled: boolean; listed: boolean;
  takeaways: { search: string; maps: string; check: string; clock: string }; searches: Search[];
  promise: { allows: string; name: string; kind: "law" | "charter" };
  further: { numbers: number; own: string[]; sites: string[] } | null;
  mode: { text: string; marks: string[]; good_marks: string[]; first_verdict: Verdict | null; first_display: string | null;
          address_matches: boolean | null; pincodes: string[]; search_id: string; sources: { title: string; domain: string }[] } | null;
  yours?: { service: string; service_id: string; limit: string; limit_days: number; applied: string | null; elapsed: number | null; overdue: boolean;
           status: "within" | "near" | "past" | "uncertain"; condition: string; allows: string };
  bing: { found: boolean; title: string; how: string; search_id: string; query: string; phone_display: string; phone_verdict: Verdict | null } | null;
}
export interface Quote { text: string; evidence: string; date: string; rating: number | null; sample: string; link: string }
export interface Step { engine: string; purpose: string; search_id: string; searched_at: string }
export interface OfficeDetail {
  office: {
    id: string; code: string; name: string; display_name: string; address: string; pincode: string; email: string; source_url: string;
    official_phones: { display: string; label: string; tel: string }[];
    listing: null | { title: string; maps_url: string; rating: number | null; reviews: number; unclaimed: boolean; phone_display?: string;
                      phone_verdict?: Verdict; match: { reasons: string[] } };
    reach: { score: number | null; basis: string; checks: { id: string; label: string; passed: boolean | null; detail: string; points: number; max_points: number }[] };
    issues: { category: string; label: string; polarity: string; count: number; of: number; quotes: Quote[] }[];
    window_reviews: number; problem_reviews: number; positive_reviews: number; enough_evidence: boolean; sampled: boolean;
    citizen_checked: boolean; span: [string, string] | null; sample_size: number; trail: Step[]; notes: string[];
  };
  card: StoryCard; maps: MapsStatus; ai: AIStatus; profile: Profile;
  timelines: { id: string; name: string; limit: string; citation: string }[];
  appeals: { first_appeal: string; second_appeal: string; first_appeal_days: number } | null;
  helpline: string; sweep: Step[]; as_of: string; type_searches: number;
  mode: AIStatus; bing: "own" | "other" | "no_phone" | "not_found" | null;
  grievance: { portals: string[]; phones: string[]; email: string } | null;
  lookalikes: { title: string; category: string; pincode: string; reviews: number; km: number | null }[]; lookalikes_total: number;
  rules: { issue_window_days: number; min_sample: number; recent_days: number; breach_margin_pct: number };
}

export interface Complaint {
  office: { id: string; label: string; email: string; address: string };
  timelines: { id: string; name: string; limit: string }[];
  officer: string; department: string; helpline: string; first_appeal: string; problem: string | null;
  promise_name: string; grievance: { portals: string[]; phones: string[]; email: string } | null;
  draft: null | { service: string; limit: string; limit_days: number; applied: string | null; elapsed: number | null;
                  uncertain?: boolean; excludes?: string;
                  overdue: boolean; subject: string; letter: string };
}
export interface Score {
  precision: number | null; recall: number | null; flags_right: number; flags: number; reports_found: number; reports: number;
  categories: { category: string; reviews: number; precision: number | null; recall: number | null }[];
}
export interface Method { heldout_reviews: number; office_type: string; lexicon: Score; model_name: string; model: Score; union: Score }

const cache = new Map<string, Promise<unknown>>();

/** Where the chat API lives: the same origin by default (`kalaana serve`), or VITE_API_BASE when the pages are hosted
 *  apart from it. Read-only data (fetchJSON) always comes from the page's own origin: locally the same server, and on
 *  Cloudflare an edge worker that caches it near the visitor. */
export const API_BASE: string = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
export const apiUrl = (path: string) => API_BASE + path;

export function fetchJSON<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(path).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${path}`);
      return r.json();
    }).catch((e) => { cache.delete(path); throw e; }));
  }
  return cache.get(path) as Promise<T>;
}

export function useJSON<T>(path: string | null): { data: T | null; error: string | null } {
  const [state, setState] = useState<{ path: string | null; data: T | null; error: string | null }>({ path: null, data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    fetchJSON<T>(path).then((data) => live && setState({ path, data, error: null }))
      .catch((e: Error) => live && setState({ path, data: null, error: e.message }));
    return () => { live = false; };
  }, [path]);
  return state.path === path ? { data: state.data, error: state.error } : { data: null, error: null };
}
