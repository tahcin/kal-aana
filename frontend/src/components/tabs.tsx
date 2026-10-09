import { motion } from "motion/react";
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "../lib/ui";

export interface TabItem<T extends string> { id: T; label: string }

/**
 * An accessible tablist: role=tablist/tab, aria-selected, aria-controls, one tab stop (roving tabindex), and
 * Left/Right/Home/End to move between tabs. Selecting follows focus, as in the ARIA tabs pattern.
 * Pass `indicator` (classes for a pill) to get a selection pill that slides between tabs.
 */
export function TabList<T extends string>({ tabs, value, onChange, idBase, label, className, tabClass, renderTab, indicator }: {
  tabs: TabItem<T>[]; value: T; onChange: (id: T) => void; idBase: string; label?: string; className?: string;
  tabClass: (selected: boolean) => string; renderTab?: (tab: TabItem<T>, selected: boolean) => ReactNode; indicator?: string;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const at = tabs.findIndex((t) => t.id === value);
    const next = { ArrowRight: (at + 1) % tabs.length, ArrowLeft: (at - 1 + tabs.length) % tabs.length, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    onChange(tabs[next].id);
    refs.current[tabs[next].id]?.focus();
  };
  return (
    <div role="tablist" aria-label={label} className={className} onKeyDown={onKeyDown}>
      {tabs.map((t) => {
        const selected = t.id === value;
        const content = renderTab ? renderTab(t, selected) : t.label;
        return (
          <button key={t.id} ref={(el) => { refs.current[t.id] = el; }} type="button" role="tab" id={`${idBase}-tab-${t.id}`}
            aria-selected={selected} aria-controls={`${idBase}-panel`} tabIndex={selected ? 0 : -1} onClick={() => onChange(t.id)}
            className={cn(indicator && "relative isolate", tabClass(selected))}>
            {indicator && selected && (
              <motion.span layoutId={`${idBase}-indicator`} aria-hidden className={cn("absolute inset-0 -z-10", indicator)}
                transition={{ type: "spring", stiffness: 420, damping: 38 }} />
            )}
            {content}
          </button>
        );
      })}
    </div>
  );
}
