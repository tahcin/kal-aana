// The chat's client side: sends the conversation to /api/chat and reads the reply as server-sent events.
// The conversation lives only in this browser tab (sessionStorage); the server keeps no record of it.
import { apiUrl, type Headline, type StoryCard } from "./api";

export interface ReviewIssue {
  category: string; label: string; polarity: "problem" | "positive"; count: number; of: number;
  quotes: { text: string; date: string; rating: number | null; link: string; evidence: string }[];
}
export type ChatCard =
  | { kind: "numbers"; card: StoryCard }
  | { kind: "ai"; card: StoryCard }
  | { kind: "unchecked"; card: StoryCard }
  | { kind: "wait"; card: StoryCard; sentence: string; caveats: string[] }
  | { kind: "reviews"; label: string; office_id: string; sampled: boolean; window?: number; span?: [string, string] | null;
      enough?: boolean; problem?: number; issues: ReviewIssue[] }
  | { kind: "letter"; office_id: string; to: { label: string; email: string; address: string }; subject: string | null; letter: string | null;
      problem: string | null; overdue: boolean | null; uncertain: boolean | null; caveats: string[] }
  | { kind: "report"; office_type: string; plural: string; headline: Headline; searches: number }
  | { kind: "choose"; query: string; options: { id: string; label: string; type: string }[] }
  | { kind: "portals"; office_type: string; links: { label: string; url: string }[] }
  | { kind: "busy"; office_id: string; label: string; as_of: string;
      busy: { title: string; engine: string; search_id: string; days: Record<string, [number, number][]> } }
  | { kind: "search"; query: string; official_only: boolean; no_official: boolean; search_id: string; searched_at: string; fresh: boolean;
      results: { title: string; link: string; domain: string; official: boolean; snippet: string; date: string }[] }
  | { kind: "news"; query: string; search_id: string; searched_at: string; fresh: boolean;
      results: { title: string; link: string; domain: string; source: string; date: string; official: boolean }[] };

export type Part = { type: "text"; text: string } | { type: "card"; card: ChatCard };
export interface Reply { parts: Part[]; status: string | null; by: string | null; note: string; error: string | null; memory: string; done: boolean }
export type Message = { role: "user"; text: string } | ({ role: "assistant" } & Reply);
export type ChatEvent =
  | { type: "status"; text: string } | { type: "text"; text: string } | { type: "card"; card: ChatCard }
  | { type: "error"; text: string } | { type: "done"; by: string; note?: string; memory: string; withheld?: number };

export const emptyReply = (): Reply => ({ parts: [], status: "Reading your question", by: null, note: "", error: null, memory: "", done: false });

/** One reply to `messages`, applying each event to the reply through `onEvent` as it arrives. */
export async function streamReply(messages: Message[], onEvent: (e: ChatEvent) => void, signal: AbortSignal): Promise<void> {
  // Only the last few turns are read; an earlier reply is sent as its card note first, then its words.
  const body = {
    messages: messages.slice(-12).map((m) => m.role === "user" ? { role: "user", content: m.text }
      : { role: "assistant", content: [m.memory, m.parts.filter((p) => p.type === "text").map((p) => (p as { text: string }).text).join("")].join("\n").trim() || "(cards only)" }),
  };
  const post = () => fetch(apiUrl("/api/chat"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal });
  let r: Response;
  try {
    r = await post();
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    // A blip (the server restarting, a dropped connection): wait a moment and try once more before giving up.
    await new Promise((ok) => setTimeout(ok, 1500));
    if (signal.aborted) throw new DOMException("Aborted", "AbortError");
    try { r = await post(); } catch (again) {
      if ((again as Error).name === "AbortError") throw again;
      throw new Error("Couldn't reach Kal Aana just now. Check your connection and try again.");
    }
  }
  if (r.status === 429) throw new Error("Too many questions for now. Try again in a few minutes.");
  if (!r.ok || !r.body) throw new Error("Kal Aana couldn't answer just now. Try again.");
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try { chunk = await reader.read(); } catch (e) {
      if ((e as Error).name === "AbortError") throw e;
      throw new Error("The connection dropped while Kal Aana was answering. Try again.");
    }
    const { value, done } = chunk;
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      if (chunk.startsWith("data: ")) onEvent(JSON.parse(chunk.slice(6)) as ChatEvent);
    }
  }
}

export function applyEvent(reply: Reply, e: ChatEvent): Reply {
  switch (e.type) {
    case "status": return { ...reply, status: e.text };
    case "text": {
      const last = reply.parts[reply.parts.length - 1];
      const parts = last?.type === "text" ? [...reply.parts.slice(0, -1), { type: "text" as const, text: last.text + e.text }] : [...reply.parts, { type: "text" as const, text: e.text }];
      return { ...reply, parts };
    }
    case "card": return { ...reply, parts: [...reply.parts, { type: "card", card: e.card }], status: null };
    case "error": return { ...reply, error: e.text };
    case "done": return { ...reply, by: e.by, note: e.note ?? "", memory: e.memory, status: null, done: true };
  }
}

const KEY = "kalaana-chat-v1";  // bump when the shape changes, so an old tab's conversation is dropped, not misread
const valid = (m: unknown): m is Message => {
  const x = m as Message;
  return !!x && (x.role === "user" ? typeof x.text === "string" : x.role === "assistant" && Array.isArray(x.parts) && x.done === true);
};
export function loadConversation(): Message[] {
  try {
    const saved: unknown = JSON.parse(sessionStorage.getItem(KEY) ?? "[]");
    return Array.isArray(saved) && saved.every(valid) ? saved : [];
  } catch { return []; }
}
export function saveConversation(messages: Message[]): void {
  try { sessionStorage.setItem(KEY, JSON.stringify(messages.filter((m) => m.role === "user" || m.done))); } catch { /* storage blocked */ }
}

/** Who answered: Claude wrote the words between cards; another model only read the message; or no model at all. */
export const readerLabel = (by: string | null) => !by || by === "none" ? "" : by === "rules" ? "Answered from Kal Aana's saved data (no AI model)"
  : by.includes("Claude API") ? `Written by ${by}` : `Read by ${by}; the cards were chosen by Kal Aana's rules`;

/** The office a card is about, if it is about one. */
export function cardOffice(card: ChatCard): string | null {
  switch (card.kind) {
    case "numbers": case "ai": case "unchecked": case "wait": return card.card.label;
    case "reviews": case "busy": return card.label;
    case "letter": return card.to.label;
    default: return null;
  }
}
