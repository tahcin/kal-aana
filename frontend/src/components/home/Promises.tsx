// Three promises, each with a small picture of itself: a receipt built from a real office's evidence, a browser tab
// that keeps the conversation, and the MCP server's real tool names.
import { LockKeyhole } from "lucide-react";
import type { ReactNode } from "react";
import { Reveal } from "../bits";
import { useJSON, type OfficeDetail, type OfficeSummary } from "../../lib/api";
import { MAPS, cn, toneText } from "../../lib/ui";

// The MCP server's tools, as kalaana/mcp_server.py registers them (the last two run live searches).
const TOOLS = ["how_to_reach", "office_report", "compare_offices", "statutory_timeline", "read_a_complaint", "check_wait",
  "google_ai_answers", "office_reviews", "draft_complaint", "best_time_to_visit", "search_official_sites", "search_news"];

function Card({ visual, title, children, delay }: { visual: ReactNode; title: string; children: ReactNode; delay: number }) {
  return (
    <Reveal delay={delay} className="group flex flex-col">
      <div className="relative aspect-[5/4] overflow-hidden rounded-[28px] bg-gradient-to-br from-wash to-paper-2">{visual}</div>
      <h3 className="serif mt-6 text-[1.75rem] leading-[1.1] tracking-[-0.02em]">{title}</h3>
      <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{children}</p>
    </Reveal>
  );
}

function Receipt({ office }: { office: OfficeSummary | null }) {
  const { data } = useJSON<OfficeDetail>(office ? `/api/office/${office.id}` : null);
  const searchId = data?.card.maps?.search_id;
  const row = "flex items-baseline justify-between gap-3 border-b border-dashed border-rule py-2";
  return (
    <div className="absolute inset-x-[12%] top-[14%] bottom-0 rotate-[-2.5deg] rounded-t-xl bg-card px-5 pt-5 shadow-[var(--shadow-float)] transition-transform duration-700 ease-[var(--ease-out-expo)] group-hover:rotate-0">
      {office && data ? (
        <>
          <p className="serif line-clamp-1 text-[17px] text-ink">{office.label}</p>
          <div className="mt-2 text-[12px]">
            <p className={row}><span className="text-muted">Directory</span><span className="font-mono text-ink">{office.official}</span></p>
            <p className={row}><span className="text-muted">Google Maps</span><span className={cn("font-medium", toneText[MAPS[office.maps].tone])}>{MAPS[office.maps].short}</span></p>
            {searchId && <p className={row}><span className="text-muted">Search ID</span><span className="truncate font-mono text-ink-2">{searchId}</span></p>}
          </div>
        </>
      ) : <div className="space-y-2.5">{[70, 100, 100, 90].map((w, i) => <div key={i} className="h-3 rounded bg-paper-2" style={{ width: `${w}%` }} />)}</div>}
    </div>
  );
}

function Tab() {
  return (
    <div className="absolute inset-x-[10%] top-[16%] bottom-[-6%] overflow-hidden rounded-2xl bg-card shadow-[var(--shadow-float)]">
      <div className="flex items-center gap-1.5 border-b border-rule bg-paper-2 px-3 py-2.5">
        {[0, 1, 2].map((i) => <span key={i} className="size-2 rounded-full bg-rule" />)}
        <span className="ml-3 flex items-center gap-1.5 rounded-md bg-card px-2.5 py-1 text-[11px] font-medium text-ink-2"><LockKeyhole className="size-3 text-brand" />This tab</span>
      </div>
      <div className="space-y-2.5 p-4">
        <div className="ml-auto h-7 w-[62%] rounded-2xl rounded-br-md bg-brand/85" />
        <div className="h-3 w-[86%] rounded bg-paper-2" /><div className="h-3 w-[70%] rounded bg-paper-2" />
        <div className="ml-auto h-7 w-[44%] rounded-2xl rounded-br-md bg-brand/85" />
        <div className="h-3 w-[78%] rounded bg-paper-2" />
      </div>
    </div>
  );
}

function Tools() {
  return (
    <div className="absolute inset-0 flex flex-wrap content-center justify-center gap-1.5 p-6">
      {TOOLS.map((t, i) => (
        <span key={t} className={cn("rounded-full px-2.5 py-1 font-mono text-[11px] shadow-[var(--shadow-soft)]",
          i >= 10 ? "bg-pop-soft text-[#7a4a00]" : "bg-card text-ink-2")}>{t}</span>
      ))}
    </div>
  );
}

export function Promises({ office }: { office: OfficeSummary | null }) {
  return (
    <section className="mx-auto max-w-[1280px] px-5 pb-24 pt-4 sm:px-8 sm:pb-32" aria-label="What Kal Aana promises">
      <div className="grid gap-12 md:grid-cols-3 md:gap-8">
        <Card delay={0} visual={<Receipt office={office} />} title="Every number has a receipt.">
          Phones come from the departments' own directories, deadlines from the Sakala Act or the Passport Seva Citizen's Charter.
          Everything Google showed keeps the SerpApi search ID that fetched it.
        </Card>
        <Card delay={0.1} visual={<Tab />} title="Your conversation stays in your tab.">
          Kal Aana keeps no record of it. Your messages go to the model that writes the answer (here, Claude); a live search sends a short query to SerpApi.
        </Card>
        <Card delay={0.2} visual={<Tools />} title="Ask from your AI assistant too.">
          The same tools run as a hosted MCP server: add kalaana-mcp.gradestone.in/mcp to Claude or any assistant. Ten of the twelve answer from the saved data.
        </Card>
      </div>
    </section>
  );
}
