// The home page: a chat. The citizen describes their problem; the reply streams in as short text and cards built
// from the snapshot (kalaana/chat.py). The conversation stays in this browser tab. Before the first question, the
// page is the scroll story in components/home/.
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { CircleAlert, RotateCcw } from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { Card } from "../components/cards";
import { Composer } from "../components/home/Composer";
import { Welcome } from "../components/home/Welcome";
import "../components/home/home.css";
import { useJSON, type Overview } from "../lib/api";
import { cn } from "../lib/ui";
import { applyEvent, cardOffice, emptyReply, loadConversation, readerLabel, saveConversation, streamReply, type Message, type Reply } from "../lib/chat";

const ease = [0.16, 1, 0.3, 1] as const;

type Block = { kind: "p"; lines: string[] } | { kind: "ul" | "ol"; items: string[] };
const BULLET = /^\s*[-*•]\s+/;
const NUMBERED = /^\s*\d+[.)]\s+/;

/** Splits the model's text into paragraphs and runs of "- " or "1. " list items; a blank line closes a paragraph. */
function blocksOf(text: string): Block[] {
  const out: Block[] = [];
  for (const para of text.replace(/^#{1,6}\s+/gm, "").trim().split(/\n{2,}/)) {
    let open = null as Block | null;  // the block this paragraph is adding to
    for (const line of para.split("\n")) {
      const kind = BULLET.test(line) ? "ul" : NUMBERED.test(line) ? "ol" : "p";
      if (open?.kind !== kind) { open = kind === "p" ? { kind, lines: [] } : { kind, items: [] }; out.push(open); }
      if (open.kind === "p") open.lines.push(line);
      else open.items.push(line.replace(open.kind === "ul" ? BULLET : NUMBERED, ""));
    }
  }
  return out;
}

/** The model's words: paragraphs, lists and **bold**, rendered as text (never as HTML), set for reading. */
function Prose({ text }: { text: string }) {
  const inline = (s: string) => s.split(/(\*\*[^*]+\*\*)/).map((p, i) => p.startsWith("**") && p.endsWith("**") ? <b key={i} className="font-semibold">{p.slice(2, -2)}</b> : <Fragment key={i}>{p}</Fragment>);
  return (
    <div className="serif my-5 max-w-[40rem] space-y-4 text-[1.16rem] leading-[1.65] text-ink first:mt-0 sm:text-[1.21rem]">
      {blocksOf(text).map((b, i) => b.kind === "p"
        ? <p key={i}>{b.lines.map((l, j) => <Fragment key={j}>{j > 0 && <br />}{inline(l)}</Fragment>)}</p>
        : b.kind === "ul"
          ? <ul key={i} className="space-y-2">{b.items.map((t, j) => (
              <li key={j} className="flex gap-3.5"><span className="mt-[0.68em] size-[5px] shrink-0 rounded-full bg-brand/70" aria-hidden /><span>{inline(t)}</span></li>
            ))}</ul>
          : <ol key={i} className="space-y-2.5">{b.items.map((t, j) => (
              <li key={j} className="flex gap-3"><span className="tnum mt-[0.3em] w-4 shrink-0 font-sans text-[0.8em] font-semibold text-brand" aria-hidden>{j + 1}.</span><span>{inline(t)}</span></li>
            ))}</ol>)}
    </div>
  );
}

/** The question, set as the heading of its turn: the reply below answers it. */
function Question({ text, first }: { text: string; first: boolean }) {
  return (
    <h2 className={cn("display break-words text-ink [overflow-wrap:anywhere]",
      text.length > 140 ? "text-[1.4rem] leading-[1.25] tracking-[-0.015em] sm:text-[1.65rem]" : "text-[1.75rem] leading-[1.12] tracking-[-0.02em] sm:text-[2.35rem]",
      !first && "mt-14 border-t border-rule pt-12 sm:mt-16 sm:pt-14")}>
      <span className="block max-w-[40rem]">{text}</span>
    </h2>
  );
}

function Assistant({ reply, onAsk }: { reply: Reply; onAsk: (t: string) => void }) {
  return (
    <div className="mt-6 sm:mt-8">
      {reply.parts.map((p, i) => {
        if (p.type === "text") return <Prose key={i} text={p.text} />;
        // Name the office once: a card about the same office as the card before it doesn't repeat the name.
        const before = reply.parts.slice(0, i).filter((q) => q.type === "card").pop();
        const office = cardOffice(p.card);
        return <Card key={i} card={p.card} onAsk={onAsk} named={!office || before?.type !== "card" || cardOffice(before.card) !== office} />;
      })}
      <AnimatePresence>
        {reply.status && !reply.done && (
          <motion.p initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, transition: { duration: 0.2 } }} transition={{ duration: 0.4, ease }}
            className="my-5 flex items-center gap-2.5 text-[15px]" role="status">
            <span className="size-1.5 animate-pulse rounded-full bg-brand/60" aria-hidden />
            <span className="kh-shimmer font-medium">{reply.status}…</span>
          </motion.p>
        )}
      </AnimatePresence>
      {reply.error && (
        <p className="my-5 flex max-w-[40rem] items-start gap-3 border-l-2 border-broken py-0.5 pl-4 text-[15px] leading-relaxed text-broken" role="alert">
          <CircleAlert className="mt-[3px] size-4 shrink-0" aria-hidden />{reply.error}
        </p>
      )}
    </div>
  );
}

export default function Chat() {
  const { data: overview } = useJSON<Overview>("/api/overview");
  const [messages, setMessages] = useState<Message[]>(loadConversation);
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const [params, setParams] = useSearchParams();
  const reduce = useReducedMotion();
  const restored = useRef(messages.length);  // messages from before a reload appear at once; new ones rise in

  const send = useCallback((text: string) => {
    if (busy) return;
    const history: Message[] = [...messages, { role: "user", text }];
    setMessages([...history, { role: "assistant", ...emptyReply() }]);
    setBusy(true);
    const controller = new AbortController();
    abort.current = controller;
    let reply = emptyReply();
    const update = () => setMessages([...history, { role: "assistant", ...reply }]);
    streamReply(history, (e) => { reply = applyEvent(reply, e); update(); }, controller.signal)
      .catch((err: Error) => { if (err.name !== "AbortError") { reply = { ...reply, error: err.message, status: null, done: true }; update(); } })
      .finally(() => {
        if (controller.signal.aborted) return;  // started over: this reply no longer belongs on the page
        if (!reply.done) { reply = { ...reply, done: true, status: null, error: reply.error ?? "The answer was cut off. Try again." }; update(); }
        saveConversation([...history, { role: "assistant", ...reply }]);
        setBusy(false);
      });
  }, [busy, messages]);

  // A shared link: /#ask=<question> puts it in the box for the visitor to send (a fragment never reaches the server, and
  // a link can't make Kal Aana say anything on its own); /?office=<id> asks a fixed question about that office.
  const [draft] = useState(() => {
    const m = location.hash.match(/^#ask=(.*)$/);
    if (!m) return "";
    history.replaceState(null, "", location.pathname + location.search);
    try { return decodeURIComponent(m[1]).slice(0, 400); } catch { return ""; }
  });
  const asked = useRef(false);
  useEffect(() => {
    const office = params.get("office");
    const label = office && overview?.offices.find((o) => o.id === office)?.label;
    if (!label || asked.current) return;
    asked.current = true;
    setParams({}, { replace: true });
    const question = `How do I reach ${label}, and what does Google show for it?`;
    const last = [...messages].reverse().find((m) => m.role === "user");
    if (last?.role === "user" && last.text === question) return;  // a reload: it's already on the page
    send(question);
  }, [params, overview, send, setParams, messages]);

  // Follow the reply as it streams in. The visitor scrolling up (wheel, touch or keys) stops following, so they can
  // read; reaching the end again resumes it. Our own scrolling never switches it off.
  const following = useRef(true);
  useEffect(() => {
    const atEnd = () => innerHeight + scrollY >= document.documentElement.scrollHeight - 80;
    const onScroll = () => { if (atEnd()) following.current = true; };
    const away = () => { if (!atEnd()) following.current = false; };
    const onWheel = (e: WheelEvent) => { if (e.deltaY < 0) following.current = false; };
    const onKey = (e: KeyboardEvent) => { if (["ArrowUp", "PageUp", "Home"].includes(e.key)) following.current = false; };
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("wheel", onWheel, { passive: true });
    addEventListener("touchmove", away, { passive: true });
    addEventListener("keydown", onKey);
    return () => {
      removeEventListener("scroll", onScroll); removeEventListener("wheel", onWheel);
      removeEventListener("touchmove", away); removeEventListener("keydown", onKey);
    };
  }, []);
  // Only new activity scrolls: arriving on the page (fresh, or with a saved conversation) keeps the normal position.
  const count = useRef(messages.length);
  const active = useRef(false);
  useEffect(() => {
    if (messages.length !== count.current) {
      const grew = messages.length > count.current;
      count.current = messages.length;
      active.current = grew;
      if (!grew) return;
      following.current = true;
      end.current?.scrollIntoView({ block: "end", behavior: reduce ? "auto" : "smooth" });
      return;
    }
    if (!active.current || !following.current) return;
    const id = requestAnimationFrame(() => scrollTo({ top: document.documentElement.scrollHeight }));
    return () => cancelAnimationFrame(id);
  }, [messages, reduce]);
  useEffect(() => () => abort.current?.abort(), []);

  const reset = () => { restored.current = 0; abort.current?.abort(); setMessages([]); saveConversation([]); setBusy(false); };

  // Who answered the latest reply, shown once under the ask bar rather than under every reply.
  const last = [...messages].reverse().find((m): m is Extract<Message, { role: "assistant" }> => m.role === "assistant" && m.done);
  const lastReader = last && readerLabel(last.by) ? { label: readerLabel(last.by), note: last.note, model: !!last.by && last.by !== "rules" && last.by !== "none" } : null;

  if (messages.length === 0) return <Welcome onSend={send} busy={busy} overview={overview} draft={draft} />;
  return (
    <div className="mx-auto max-w-[800px] px-4 sm:px-6">
      <h1 className="sr-only">Your conversation with Kal Aana</h1>
      <div className="pb-36 pt-8 sm:pb-40 sm:pt-16">
        {messages.map((m, i) => (
          <motion.div key={i} initial={reduce || i < restored.current ? false : { opacity: 0, y: 16, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={{ duration: 0.7, ease }}>
            {m.role === "user" ? <Question text={m.text} first={i === 0} /> : <Assistant reply={m} onAsk={send} />}
          </motion.div>
        ))}
        <div ref={end} />
      </div>
      {/* The follow-up box floats over a fade of the page, the width of the reading column. */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 bg-gradient-to-t from-paper from-40% to-paper/0 pb-3 pt-10 sm:pb-4">
        <div className="pointer-events-auto mx-auto max-w-[800px] px-3 sm:px-6">
          <Composer variant="chat" onSend={send} busy={busy}
            leading={
              <button type="button" onClick={reset} aria-label="Start over" title="Start over"
                className="group/reset grid size-10 place-items-center rounded-full text-muted transition-colors hover:bg-paper-2 hover:text-ink">
                <RotateCcw className="size-[17px] transition-transform duration-500 ease-[var(--ease-out-expo)] group-hover/reset:-rotate-90" aria-hidden />
              </button>
            } />
          {lastReader && (
            <p className="mt-2 text-center text-[11px] leading-snug text-muted">
              {lastReader.label}{lastReader.note && ` · ${lastReader.note}`}{lastReader.model && " · Every number on the cards comes from the data, not the model."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
