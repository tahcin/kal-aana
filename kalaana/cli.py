"""Command line (also: python -m kalaana ...).

    kalaana official                                # the official ground truth we compare against
    kalaana collect rto --city Bengaluru            # sweep Maps and reviews, save data/collected/
    kalaana collect rto --plan                      # how many fresh searches a run would cost
    kalaana report rto                              # the city report card, from the saved collection
    kalaana evaluate                                # lexicon precision and recall on labelled reviews
    kalaana citizen rto                             # what Google Search and its AI Overview tell a citizen
    kalaana snapshot rto                            # build data/snapshot/, which the web app and MCP server read
    kalaana serve                                   # the web app on http://127.0.0.1:8000 (no key needed)
    kalaana refine --model gemma3:4b                # a second reading of labelled reviews by a local LLM (Ollama)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from . import ask, citizen, crosscheck, reader, evaluate, official, refine, snapshot
from .client import SearchClient
from .collect import COLLECTED_DIR, NEWEST, OTHER_LISTING, Collection, PartialCollection, collect
from .offices import CITIES, OFFICE_TYPES
from .score import ISSUE_WINDOW_DAYS, MIN_SAMPLE, RECENT_DAYS, OfficeScore, score_collection


def positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {n}")
    return n


def print_official(data: official.OfficialData) -> None:
    for office_type in sorted({o.office_type for o in data.offices.values()}):
        offices = data.offices_of(office_type)
        print(f"\n{office_type}: {len(offices)} offices, {len(data.timelines_for(office_type))} statutory timelines")
        for o in offices:
            numbers = ", ".join(p.phone.display for p in o.phones) or "no phone published"
            print(f"  {o.code or o.id:<22} {o.name[:44]:<44} {numbers}")
        for t in data.timelines_for(office_type):
            print(f"  timeline  {t.name[:56]:<56} {t.days} {t.unit}")


def print_collection(c: Collection, data: official.OfficialData) -> None:
    print(f"\n{c.office_type} in {c.city}: {len(c.offices)} official offices")
    for oid, ev in c.offices.items():
        office = data.offices[oid]
        print(f"\n  {office.code or oid}  {office.name}")
        if not ev.primary_id:
            how = "sweep plus one targeted search" if ev.searched else "sweep only; no targeted search"
            print(f"    no listing of its own found on Google Maps ({how})")
        elif not ev.sampled:
            print("    reviews not sampled in this run")
        for listing, m in ev.listings:
            phone = listing.phone.display if listing.phone else "no phone"
            claim = "unclaimed" if listing.unclaimed else "not marked unclaimed"
            tags = [m.role] if m.role != "office" else []
            if listing.data_id == ev.primary_id:
                tags.append("primary")
            if not m.strong:
                tags.append("location match only")
            print(f"    {listing.title[:52]:<52} {phone:<16} {listing.reviews:>5} reviews  {claim}"
                  f"{'  [' + ', '.join(tags) + ']' if tags else ''}")
            print(f"      matched on: {'; '.join(m.reasons)}")
        if ev.reviews:
            first, last = ev.span()
            counts = Counter(s for r in ev.reviews.values() for s in r.samples if s not in (NEWEST, OTHER_LISTING))
            evidence = ", ".join(f"{k} {n}" for k, n in sorted(counts.items()))
            print(f"    newest-first sample: {len(ev.sample())} reviews, {first} to {last}"
                  f"{'; other listings ' + str(len(ev.sample(OTHER_LISTING))) if ev.sample(OTHER_LISTING) else ''}")
            if evidence:
                capped = [s for s in ev.more_available if s.startswith("query:")]
                print(f"    keyword evidence: {evidence}{' (first page only: ' + ', '.join(capped) + ')' if capped else ''}")
    if c.unmatched:
        print("\n  Listings not matched to an official office:")
        for listing, why in c.unmatched:
            print(f"    {listing.title[:52]:<52} {why}")
    for note in c.notes:
        print(f"  note: {note}")


def _pct(share: float | None) -> str:
    return "  n/a" if share is None else f"{share:5.0%}"


def _count(n: int, of: int, enough: bool) -> str:
    return f"{n}/{of}" if enough else "-"


def print_report(scores: list[OfficeScore], city: str, office_type: str, as_of: date) -> None:
    scored = sorted((s for s in scores if s.reachability.score is not None), key=lambda s: s.reachability.score or 0)
    unscored = [s for s in scores if s.reachability.score is None]
    print(f"\n{OFFICE_TYPES[office_type].label}s in {city}: promise vs reality, as of {as_of}")
    print(f"reach: 0-100 from six checks of what Google Maps shows (checks that can't be decided are left out; basis shown).")
    print(f"problems / positive: reviews with text from the last {ISSUE_WINDOW_DAYS // 365} year reporting at least one "
          f"problem / praise, newest first; shown only with {MIN_SAMPLE}+ such reviews.\n")
    print(f"  {'office':<44} {'reach':>5} {'basis':<13} {'problems':>8} {'positive':>8}  {'sample covers':<23}  most reported problem")
    for s in scored:
        problems = sorted((i for i in s.issues if i.polarity == "problem" and i.count), key=lambda i: -i.count)
        top = f"{problems[0].label.lower()} ({problems[0].count}/{problems[0].of})" if problems and s.enough_evidence else ""
        span = f"{s.span[0]} to {s.span[1]}" if s.span else ""
        note = top or ("reviews not sampled" if not s.sampled else
                       f"insufficient evidence ({s.window_reviews} reviews with text in the window)" if not s.enough_evidence else "")
        print(f"  {s.office.code + ' ' + s.office.name:<44} {s.reachability.score:>5} {s.reachability.basis:<13}"
              f" {_count(s.problem_reviews, s.window_reviews, s.enough_evidence):>8} {_count(s.positive_reviews, s.window_reviews, s.enough_evidence):>8}"
              f"  {span:<23}  {note}")
    for s in unscored:
        print(f"  {s.office.code + ' ' + s.office.name:<44}  not scored: {s.reachability.checks[0].detail}")

    print(f"\nPossible statutory breaches, last {RECENT_DAYS // 365} years (a reviewer reports a wait at least 25% past the "
          f"Sakala timeline). Found among the collected reviews: not a rate, and not comparable between offices.")
    for s in scored:
        for b in s.breaches:
            print(f"  {s.office.code} {b.quote.date}: {b.explanation}")
            print(f"      {b.quote.link}")
    waits = [(s, b) for s in scored for b in s.agent_waits]
    if waits:
        print("\nSet aside: long waits where the reviewer went through an agent (the delay may be the agent's):")
        for s, b in waits:
            print(f"  {s.office.code} {b.quote.date}: {b.explanation}")
    older = sum(s.older_breaches for s in scores)
    if older:
        print(f"\n{older} more possible breaches are older than {RECENT_DAYS // 365} years and not shown.")


def busiest(offices: list[official.Office], collection: Path) -> list[official.Office]:
    """Offices ordered by their primary Maps listing's review count, from a saved collection."""
    if not collection.exists():
        raise SystemExit(f"--offices needs a saved collection at {collection}. Run: kalaana collect first.")
    saved = json.loads(collection.read_text(encoding="utf-8"))["offices"]

    def reviews(office: official.Office) -> int:
        ev = saved.get(office.id, {})
        return next((l["reviews"] for l in ev.get("listings", []) if l["data_id"] == ev.get("primary_id")), -1)

    return sorted(offices, key=reviews, reverse=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kalaana", description="Public offices: what they promise vs what citizens report.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("official", help="list the official directories and statutory timelines")
    c = sub.add_parser("collect", help="sweep Google Maps listings and reviews for one office type")
    c.add_argument("office_type", choices=list(OFFICE_TYPES))
    c.add_argument("--city", default="Bengaluru", choices=list(CITIES))
    c.add_argument("--budget", type=int, help="max fresh searches for this run (default: KALAANA_SEARCH_BUDGET in .env)")
    c.add_argument("--pages", type=positive_int, default=2, help="Maps result pages per query")
    c.add_argument("--newest-pages", type=positive_int, default=4, help="most newest-first review pages per office")
    c.add_argument("--target-text", type=positive_int, default=15,
                   help="stop reading an office's newest reviews once this many have text")
    c.add_argument("--no-reviews", action="store_true", help="listings only")
    c.add_argument("--targeted", type=int, help="most targeted Maps searches for unconfirmed offices (default: one each)")
    c.add_argument("--sample-offices", type=positive_int,
                   help="read reviews for only the N most-reviewed offices (the rest are marked 'not sampled')")
    c.add_argument("--plan", action="store_true", help="spend nothing; count the fresh searches a run would make")
    c.add_argument("--allow-partial", action="store_true", help="save even if some searches didn't run")
    v = sub.add_parser("citizen", help="what Google Search and its AI Overview show for each office's phone number")
    v.add_argument("office_type", choices=list(OFFICE_TYPES))
    v.add_argument("--city", default="Bengaluru", choices=list(CITIES))
    v.add_argument("--budget", type=int, help="max fresh searches for this run (default: KALAANA_SEARCH_BUDGET in .env)")
    v.add_argument("--offices", type=positive_int, help="only the N offices whose Maps listings have the most reviews")
    v.add_argument("--plan", action="store_true", help="spend nothing; count the fresh searches a run would make")
    v.add_argument("--allow-partial", action="store_true",
                   help="save the offices whose Google search ran; the rest stay 'not checked'")
    k = sub.add_parser("ask", help="read a citizen's problem in their own words and answer it (uses KALAANA_READER)")
    k.add_argument("text", help='for example: "applied for my learner\'s licence at RTO South 3 weeks ago"')
    x = sub.add_parser("crosscheck", help="look each office up on Bing Maps: is the missing number only Google's problem?")
    x.add_argument("office_type", choices=list(OFFICE_TYPES))
    x.add_argument("--city", default="Bengaluru", choices=list(CITIES))
    x.add_argument("--budget", type=int, help="max fresh searches for this run (default: KALAANA_SEARCH_BUDGET in .env)")
    x.add_argument("--plan", action="store_true", help="spend nothing; count the fresh searches a run would make")
    b = sub.add_parser("snapshot", help="join the official data, collection, scores and citizen view into data/snapshot/")
    b.add_argument("office_type", choices=list(OFFICE_TYPES))
    b.add_argument("--city", default="Bengaluru", choices=list(CITIES))
    w = sub.add_parser("serve", help="run the web app from the committed snapshot")
    w.add_argument("--port", type=positive_int, default=8000)
    f = sub.add_parser("refine", help="read the labelled reviews with a local LLM via Ollama, then score it")
    f.add_argument("--model", default="gemma3:4b")
    f.add_argument("--labels", default="rto-reviews.jsonl", help="file in data/labels (tune on the development set)")
    f.add_argument("--limit", type=positive_int, help="only the first N reviews (for timing a model)")
    e = sub.add_parser("evaluate", help="measure the issue lexicon against hand-labelled reviews")
    e.add_argument("labels", nargs="?", default="rto-reviews-heldout.jsonl", help="file in data/labels")
    e.add_argument("--model", help="also score this model's cached reading, alone and combined with the lexicon")
    q = sub.add_parser("chat-eval", help="run the chat's honesty scenarios through the configured reader (Claude costs money)")
    q.add_argument("--only", nargs="*", help="scenario ids to run (default: all)")
    r = sub.add_parser("report", help="print the city report card from a saved collection (no searches)")
    r.add_argument("office_type", choices=list(OFFICE_TYPES))
    r.add_argument("--city", default="Bengaluru", choices=list(CITIES))
    a = p.parse_args(argv)

    data = official.load()
    if a.cmd == "official":
        print_official(data)
        return 0
    if a.cmd == "ask":
        out = ask.answer(a.text)
        got = out["understood"]
        print(f"read by: {out['by']}" + (f"  ({got['note']})" if got["note"] else ""))
        if reader.configured() == "anthropic":
            print(f"Claude reader spend so far: ${reader.spent()['usd']:.4f} of ${reader.budget_usd():g} "
                  f"({reader.spent()['calls']} calls)")
        print(f"office:  {(got['office'] or {}).get('label', '-')}   service: {got['service'] or '-'}   applied: {got['applied'] or '-'}"
              f"   intent: {got['intent']}")
        if got["candidates"]:
            print("could be: " + "; ".join(c["label"] for c in got["candidates"]))
        if out["answer"]:
            print(f"\n{out['answer']['headline']}")
            for line in out["answer"]["lines"]:
                print(f"  {line}")
        return 0
    if a.cmd == "crosscheck":
        collection_path = COLLECTED_DIR / f"{a.city.lower()}-{a.office_type}.json"
        collection = json.loads(collection_path.read_text(encoding="utf-8")) if collection_path.exists() else {}
        client = SearchClient(budget=a.budget, dry_run=a.plan)
        looks = [crosscheck.look(client, o, data, CITIES[a.city], crosscheck.google_location(collection, o.id))
                 for o in data.offices_of(a.office_type)]
        if a.plan:
            fresh = sum(not s.cached for s in client.log)
            print(f"Plan: {len(client.log) - fresh} searches cached, {fresh} fresh bing_maps searches.")
            return 0
        for b in looks:
            shown = f"{b.phone.display} ({b.verdict})" if b.phone else "no phone"
            print(f"  {b.office_id:<28} {(b.title or 'not found')[:44]:<44} {shown:<40} {b.how or b.note}")
        print(f"\n{client.usage()}")
        if any(b.note for b in looks):
            print("Some searches didn't run; not saving.", file=sys.stderr)
            return 1
        print(f"saved {crosscheck.save(looks, COLLECTED_DIR / f'{a.city.lower()}-{a.office_type}-bing.json')}")
        return 0
    if a.cmd == "citizen":
        offices = data.offices_of(a.office_type)
        if a.offices:
            offices = busiest(offices, COLLECTED_DIR / f"{a.city.lower()}-{a.office_type}.json")[:a.offices]
        client = SearchClient(budget=a.budget, dry_run=a.plan)
        views = [(citizen.citizen_view(client, o, data, CITIES[a.city]), o) for o in offices]
        if a.plan:
            fresh = sum(not s.cached for s in client.log)
            by_engine: dict[str, int] = {}
            for s in client.log:
                if not s.cached:
                    by_engine[s.engine] = by_engine.get(s.engine, 0) + 1
            google = by_engine.get("google", 0)
            print(f"Plan: {len(client.log) - fresh} searches cached, {fresh} fresh "
                  f"({', '.join(f'{n} {e}' for e, n in sorted(by_engine.items()))}), plus up to {google} AI Overview "
                  "follow-ups (only where Google defers the AI Overview).")
            return 0
        for view, office in views:
            match = {True: "matches", False: "DOES NOT match", None: "gives no PIN"}[view.ai_address_matches(office)]
            mode_match = {True: "matches", False: "DOES NOT match", None: "gives no PIN"}[view.mode_address_matches(office)]
            print(f"\n{office.code} {view.query!r}: AI Overview address {match}, AI Mode {mode_match} the official PIN {office.pincode}")
            for n in view.numbers:
                print(f"  {n.surface:<15} {n.source[:34]:<34} {n.phone.display:<16} {n.verdict}")
            for note in view.notes:
                print(f"  note: {note}")
        print(f"\n{client.usage()}")
        if any(v.notes for v, _ in views):
            if not a.allow_partial:
                print("Some searches didn't run; not saving (use --allow-partial to save the rest).", file=sys.stderr)
                return 1
            skipped = [o.id for v, o in views if not v.search_id]
            views = [(v, o) for v, o in views if v.search_id]
            print(f"Saving without {', '.join(skipped)}: their Google search didn't run, so they stay 'not checked'.")
        print(f"saved {citizen.save(views, COLLECTED_DIR / f'{a.city.lower()}-{a.office_type}-citizen.json')}")
        return 0
    if a.cmd == "chat-eval":
        from . import chat_eval
        report = chat_eval.run(only=a.only)
        for x in report["results"]:
            print(f"{'pass' if not x['problems'] else 'FAIL'}  {x['id']:<20} {'; '.join(x['problems'])}")
        print(f"\n{report['passed']} of {report['total']} passed, read by {report['reader']}")
        if not a.only:
            print(f"saved {chat_eval.write(report)}")
        return 0 if report["passed"] == report["total"] else 1
    if a.cmd == "snapshot":
        if not (COLLECTED_DIR / f"{a.city.lower()}-{a.office_type}.json").exists():
            print(f"No saved collection for {a.office_type} in {a.city}. Run: kalaana collect {a.office_type} --city {a.city} "
                  f"(the committed snapshot in data/snapshot/ already serves the demo)", file=sys.stderr)
            return 1
        print(f"saved {snapshot.save(snapshot.build(data, a.city, a.office_type))}")
        return 0
    if a.cmd == "serve":
        import uvicorn

        uvicorn.run("kalaana.web:app", host="127.0.0.1", port=a.port)
        return 0
    if a.cmd == "refine":
        rows = evaluate.load(evaluate.LABELS_DIR / a.labels)[: a.limit]
        try:
            readings = refine.run(rows, a.model)
        except refine.OllamaUnavailable as err:
            print(err, file=sys.stderr)
            return 1
        seconds = [r.seconds for r in readings.values()]
        rejected = sum(len(r.rejected) for r in readings.values())
        print(f"{len(readings)} reviews read by {a.model}, median {sorted(seconds)[len(seconds) // 2]:.1f}s each; "
              f"{rejected} labels rejected because their quote wasn't in the review")
        return 0
    if a.cmd == "evaluate":
        rows = evaluate.load(evaluate.LABELS_DIR / a.labels)
        runs = [("lexicon", evaluate.lexicon)]
        if a.model:
            runs += [(a.model, refine.predictor(a.model)), (f"lexicon + {a.model}", refine.predictor(a.model, combine=True))]
        for name, predict in runs:
            results = evaluate.evaluate(rows, predict)
            print(f"\n{name}\n{'category':<13}{'reviews':>8}{'precision':>11}{'recall':>8}  (ambiguous labels excluded)")
            for result in results.values():
                print(f"{result.category:<13}{result.support:>8}{_pct(result.precision):>11}{_pct(result.recall):>8}")
            precision, recall = evaluate.micro_average(results)
            print(f"{'all':<13}{'':>8}{precision:>11.0%}{recall:>8.0%}")
        return 0
    if a.cmd == "report":
        path = COLLECTED_DIR / f"{a.city.lower()}-{a.office_type}.json"
        if not path.exists():
            print(f"No saved collection at {path}. Run: kalaana collect {a.office_type} --city {a.city}", file=sys.stderr)
            return 1
        collection = json.loads(path.read_text(encoding="utf-8"))
        print_report(score_collection(collection, data), a.city, a.office_type, date.fromisoformat(collection["collected_at"][:10]))
        return 0

    client = SearchClient(budget=a.budget, dry_run=a.plan)
    result = collect(client, data, a.office_type, a.city, pages=a.pages, newest_pages=a.newest_pages,
                     target_text=a.target_text, reviews=not a.no_reviews, targeted=a.targeted,
                     sample_offices=a.sample_offices)
    if a.plan:
        fresh = [s for s in result.searches if not s.cached]
        print(f"Plan: {len(result.searches) - len(fresh)} searches cached, at least {len(fresh)} fresh.")
        print("Searches that depend on uncached results (next pages, offices found later) aren't counted yet.")
        for engine, n in sorted(Counter(s.engine for s in fresh).items()):
            print(f"  {engine:<22} {n}")
        return 0
    print_collection(result, data)
    print(f"\n{client.usage()}")
    for failure in result.failures:
        print(f"NOT RUN: {failure}", file=sys.stderr)
    try:
        print(f"saved {result.save(allow_partial=a.allow_partial)}")
    except PartialCollection as e:
        print(f"{e}. Re-run with a larger --budget, or --allow-partial to save it separately.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
