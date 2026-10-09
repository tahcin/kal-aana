import { ArrowRight } from "lucide-react";
import { Link, useLocation } from "react-router";
import { Reveal } from "../components/bits";
import { TokenTicket } from "../components/ErrorPage";
import { Footer } from "../components/Shell";
import { useTitle } from "../lib/useTitle";

export default function NotFound() {
  useTitle("Page not found");
  const { pathname } = useLocation();
  return (
    <main>
      <section className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-14 sm:px-6 sm:pt-24 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div>
          <Reveal>
            <h1 className="headline text-[clamp(2.75rem,6.4vw,5.25rem)] leading-[0.96] tracking-[-0.04em]">
              This page told us to <span className="bg-[linear-gradient(transparent_62%,color-mix(in_srgb,var(--color-pop)_42%,transparent)_62%)] [box-decoration-break:clone] px-1">come back tomorrow.</span>
            </h1>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-6 max-w-[44ch] text-lg leading-relaxed text-ink-2">
              Nothing lives at <span className="break-all rounded-md bg-paper-2 px-1.5 py-0.5 font-mono text-[0.85em] text-ink">{pathname}</span>.
              The rest of Kal Aana is open today.
            </p>
            <p className="mt-9 flex flex-wrap gap-3">
              <Link to="/" className="group inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 font-semibold text-paper shadow-[var(--shadow-soft)] transition hover:brightness-110">
                Ask Kal Aana <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
              </Link>
              <Link to="/offices" className="inline-flex rounded-full border border-rule bg-card px-5 py-3 font-semibold transition hover:border-ink-2">Every office</Link>
            </p>
          </Reveal>
        </div>
        <div className="flex justify-center px-2 lg:justify-end"><TokenTicket token="404" stamp="Come back tomorrow" /></div>
      </section>
      <Footer />
    </main>
  );
}
