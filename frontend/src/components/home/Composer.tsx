// The ask box, in three dresses: the large one on the hero (a rotating example as its placeholder), the floating bar
// that follows you down the home page, and the follow-up box under a conversation. One line until the visitor writes
// more; the send button stays one compact circle and only changes how sure of itself it looks.
import { AnimatePresence, motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useEffect, useId, useLayoutEffect, useRef, useState, type ReactNode, type Ref } from "react";
import { cn } from "../../lib/ui";

const ease = [0.16, 1, 0.3, 1] as const;
const MAX = 400;

/** A thin arc that turns while a reply is on its way. */
function Spinner() {
  return (
    <svg viewBox="0 0 20 20" className="size-4 animate-spin [animation-duration:1.1s]" aria-hidden>
      <circle cx="10" cy="10" r="8" fill="none" stroke="currentColor" strokeOpacity="0.18" strokeWidth="1.5" />
      <path d="M10 2a8 8 0 0 1 8 8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function Composer({ onSend, busy, variant, initial = "", example, inputRef, onTyping, placeholder, leading }: {
  onSend: (t: string) => void; busy: boolean; variant: "hero" | "bar" | "chat"; initial?: string;
  /** Hero only: the example shown as the placeholder, sent if the box is empty. */
  example?: string; inputRef?: Ref<HTMLTextAreaElement>; onTyping?: (typing: boolean) => void; placeholder?: string;
  /** A quiet icon button inside the box, before the text (the conversation's "Start over"). */
  leading?: ReactNode;
}) {
  const [text, setText] = useState(initial);
  const own = useRef<HTMLTextAreaElement>(null);
  const mirror = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number | null>(null);
  const id = useId();
  const hero = variant === "hero";

  // The height comes from a hidden copy of the text, so the box can ease between sizes instead of snapping to "auto".
  useLayoutEffect(() => {
    const m = mirror.current;
    if (!m) return;
    const measure = () => setHeight(Math.min(m.offsetHeight, 176));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(m);
    return () => ro.disconnect();
  }, [text]);
  useEffect(() => { onTyping?.(text.trim() !== ""); }, [text, onTyping]);

  const value = text.trim() || example || "";
  const send = () => { if (value && !busy) { onSend(value); setText(""); } };
  const setRefs = (el: HTMLTextAreaElement | null) => {
    own.current = el;
    if (typeof inputRef === "function") inputRef(el);
    else if (inputRef) inputRef.current = el;
  };
  const showExample = hero && !text && !!example;
  const ready = !!value && !busy;
  const tall = (height ?? 0) > (hero ? 34 : 30);
  const type = hero ? "text-[16px] leading-[1.6] sm:text-[17.5px]" : "text-[16px] leading-[1.6]";

  return (
    <form data-ask-box onSubmit={(e) => { e.preventDefault(); send(); }} onClick={(e) => { if (e.target === e.currentTarget) own.current?.focus(); }}
      className={cn("group relative flex cursor-text items-end gap-2 border bg-card transition-[border-color,box-shadow,border-radius] duration-500 ease-[var(--ease-out-expo)]",
        "focus-within:border-brand/45 focus-within:shadow-[var(--shadow-float),0_0_0_4px_color-mix(in_srgb,var(--color-brand)_12%,transparent)]",
        hero ? "border-white/70 p-2 pl-5 shadow-[var(--shadow-float)] sm:p-2.5 sm:pl-6"
          : "border-rule/90 p-1.5 pl-4 shadow-[var(--shadow-float)]",
        !hero && "glass",
        leading && "pl-1.5",
        tall ? "rounded-[26px]" : "rounded-[32px]")}>
      <label htmlFor={id} className="sr-only">Describe your problem with a public office</label>
      {showExample && <span id={`${id}-hint`} className="sr-only">Or press Enter to ask the example: {example}</span>}
      {leading && <div className="flex shrink-0 self-end">{leading}</div>}

      <div className={cn("relative min-w-0 flex-1 self-center", hero ? "py-[7px] sm:py-[9px]" : "py-[5px]", leading && "pl-1")}>
        <div ref={mirror} aria-hidden className={cn("pointer-events-none invisible absolute inset-x-0 top-0 whitespace-pre-wrap break-words", type)}>{text + "​"}</div>
        <textarea id={id} ref={setRefs} rows={1} value={text} maxLength={MAX} onChange={(e) => setText(e.target.value)}
          aria-describedby={showExample ? `${id}-hint` : undefined}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } }}
          placeholder={hero ? "" : placeholder ?? "Ask a follow-up"}
          style={height ? { height } : undefined}
          className={cn("block w-full resize-none overflow-y-auto bg-transparent text-ink outline-none transition-[height] duration-300 ease-[var(--ease-out-expo)] [scrollbar-width:thin]",
            "placeholder:overflow-hidden placeholder:text-ellipsis placeholder:whitespace-nowrap placeholder:text-muted", type)} />
        {/* The rotating example, drawn over the empty box on one line. It crossfades through a blur, like a thought forming. */}
        <AnimatePresence initial={false}>
          {showExample && (
            <motion.span key={example} aria-hidden
              initial={{ opacity: 0, filter: "blur(6px)", y: 8 }} animate={{ opacity: 1, filter: "blur(0px)", y: 0 }} exit={{ opacity: 0, filter: "blur(6px)", y: -8 }}
              transition={{ duration: 0.7, ease }}
              className={cn("pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 truncate text-muted", type)}>
              {example}
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Enter asks the example: said only where there is a keyboard, and only while the box has focus. */}
      {showExample && (
        <kbd aria-hidden title="Press Enter to ask this example"
          className="hidden h-6 min-w-6 shrink-0 place-items-center self-center rounded-md border border-rule bg-paper px-1.5 font-sans text-xs text-muted opacity-0 transition-opacity duration-300 group-focus-within:opacity-100 [@media(hover:hover)_and_(pointer:fine)]:grid">↵</kbd>
      )}

      <button type="submit" disabled={!ready} aria-label={busy ? "Answering" : showExample ? "Ask this example" : "Send"}
        className={cn("grid shrink-0 place-items-center rounded-full transition-[background-color,color,transform,box-shadow] duration-300 ease-[var(--ease-out-expo)]",
          hero ? "size-10 sm:size-11" : "size-10",
          ready ? "bg-brand text-white shadow-[0_6px_16px_-6px_rgb(90_63_192/0.6)] hover:scale-[1.05] hover:bg-brand-2 active:scale-95"
            : busy ? "bg-paper-2 text-brand" : "bg-paper-2 text-muted/70")}>
        {busy ? <Spinner /> : <ArrowRight className="size-[18px]" strokeWidth={2.25} aria-hidden />}
      </button>
    </form>
  );
}
