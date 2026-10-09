import type { Layer } from "@deck.gl/core";
import { MapboxOverlay } from "@deck.gl/mapbox";
import { ArcLayer, ScatterplotLayer } from "@deck.gl/layers";
import { AnimatePresence, motion, useDragControls, useReducedMotion, type PanInfo } from "motion/react";
import { ArrowRight, MessageCircleQuestion, WifiOff, X } from "lucide-react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import MapGL, { NavigationControl, useControl, type MapRef } from "react-map-gl/maplibre";
import { setWorkerUrl, type StyleSpecification } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import { Link } from "react-router";
import { Chip, CountUp, Mono } from "../components/bits";
import { useJSON, type MapPoint, type MapsStatus, type Overview } from "../lib/api";
import { AI, MAPS, cn, toneBg, type Tone } from "../lib/ui";
import { useTitle } from "../lib/useTitle";
import "../styles/map.css";

// MapLibre loads its worker from beside its own script by default; Vite bundles that script, so
// point it at the worker file Vite copies into the build.
setWorkerUrl(workerUrl);

const BING: Record<"own" | "other" | "no_phone" | "not_found", { tone: Tone; label: string }> = {
  own: { tone: "kept", label: "Own number" }, other: { tone: "amber", label: "A different number" },
  no_phone: { tone: "broken", label: "No phone" }, not_found: { tone: "unknown", label: "Not matched" },
};

type Filter = string;  // "all", "no_phone", "lookalikes", or an office type
type Arc = { from: MapPoint; to: MapPoint; label: string; km: number };
type Lookalike = Overview["types"][string]["lookalikes"][number] & { of: string };

/* ---------- The street map: OpenFreeMap's free Positron tiles, recoloured to Kal Aana's palette ---------- */

const BASE_STYLE = "https://tiles.openfreemap.org/styles/positron";
let baseStyle: Promise<StyleSpecification> | null = null;
function loadBaseStyle() {
  baseStyle ??= fetch(BASE_STYLE).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
    .catch((e) => { baseStyle = null; throw e; });
  return baseStyle;
}

type Palette = Record<"land" | "residential" | "park" | "water" | "waterway" | "building" | "buildingLine" | "road" | "casing" | "minor"
  | "motorway" | "motorwayCasing" | "rail" | "boundary" | "place" | "label" | "roadLabel" | "waterLabel" | "halo", string>;

// Filter-coffee cream land, lilac water and marigold highways.
const PALETTE: Palette = {
  land: "#f6efe2", residential: "#f1e8d8", park: "#e5e9d2", water: "#d8cdf3", waterway: "#c8b8ee", building: "#ece1ce", buildingLine: "#e0d3bd",
  road: "#fffaf1", casing: "#e4d7c2", minor: "#fbf5ea", motorway: "#ffe7b8", motorwayCasing: "#f3d08f", rail: "#ddd0bd", boundary: "#b7a6d9",
  place: "#1c1530", label: "#3f3555", roadLabel: "#7a6f86", waterLabel: "#5a3fc0", halo: "#f8f3ea",
};

/** The paint colours for one layer of the Positron style, by what the layer draws. */
function paintFor(id: string, type: string, p: Palette): Record<string, string> | null {
  if (type === "background") return { "background-color": p.land };
  if (type === "symbol") {
    const color = /water/.test(id) ? p.waterLabel : /^label_/.test(id) ? (/village|other/.test(id) ? p.label : p.place) : p.roadLabel;
    return { "text-color": color, "text-halo-color": p.halo };
  }
  if (id === "park" || id === "landcover_wood") return { "fill-color": p.park };
  if (id === "landuse_residential") return { "fill-color": p.residential };
  if (id === "water") return { "fill-color": p.water };
  if (id === "waterway") return { "line-color": p.waterway };
  if (id === "building") return { "fill-color": p.building, "fill-outline-color": p.buildingLine };
  if (/motorway.*casing/.test(id)) return { "line-color": p.motorwayCasing };
  if (/motorway_(inner|bridge_inner)/.test(id)) return { "line-color": p.motorway };
  if (/motorway_subtle/.test(id)) return { "line-color": p.motorwayCasing };
  if (/major_casing|major_subtle/.test(id)) return { "line-color": p.casing };
  if (/major_inner/.test(id)) return { "line-color": p.road };
  if (/highway_(minor|path)|aeroway/.test(id)) return { [type === "fill" ? "fill-color" : "line-color"]: p.minor };
  if (/pier/.test(id)) return { [type === "fill" ? "fill-color" : "line-color"]: p.land };
  if (/railway.*dashline/.test(id)) return { "line-color": p.land };
  if (/railway/.test(id)) return { "line-color": p.rail };
  if (/boundary/.test(id)) return { "line-color": p.boundary };
  return null;
}

function themedStyle(base: StyleSpecification, p: Palette): StyleSpecification {
  return {
    ...base,
    layers: base.layers.map((l) => {
      const paint = paintFor(l.id, l.type, p);
      return paint ? ({ ...l, paint: { ...("paint" in l ? l.paint : {}), ...paint } } as typeof l) : l;
    }),
  };
}

/** Until the tiles arrive (or if they never do), a plain ground in the page colour so the offices still read. */
const plainStyle = (p: Palette): StyleSpecification => ({ version: 8, sources: {}, layers: [{ id: "background", type: "background", paint: { "background-color": p.land } }] });

/* ---------- Helpers ---------- */

/** Straight-line distance in km between two offices. */
function km(a: MapPoint, b: MapPoint): number {
  const rad = Math.PI / 180, dLat = (b.lat! - a.lat!) * rad, dLng = (b.lng! - a.lng!) * rad;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat! * rad) * Math.cos(b.lat! * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function cssColor(name: string): [number, number, number] {
  const probe = document.createElement("span");
  probe.style.color = `var(${name})`;
  document.body.append(probe);
  const [r, g, b] = getComputedStyle(probe).color.match(/\d+/g)!.map(Number);
  probe.remove();
  return [r, g, b];
}

type DeckProps = ConstructorParameters<typeof MapboxOverlay>[0];

/** The deck.gl layer stack on the map. `overlayRef` lets the page update layers without re-rendering React. */
function DeckOverlay({ overlayRef, ...props }: DeckProps & { overlayRef: RefObject<MapboxOverlay | null> }) {
  const overlay = useControl(() => new MapboxOverlay(props));
  overlay.setProps(props);
  useEffect(() => { overlayRef.current = overlay; return () => { overlayRef.current = null; }; }, [overlay, overlayRef]);
  return null;
}

function useWide(): boolean {
  const [wide, setWide] = useState(() => matchMedia("(min-width: 768px)").matches);
  useEffect(() => {
    const mq = matchMedia("(min-width: 768px)");
    const on = () => setWide(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return wide;
}

const capital = (s: string) => s[0].toUpperCase() + s.slice(1);
const radius = (p: MapPoint) => (p.type === "subregistrar" ? 6 : 9.5);
const STAT_TONE: Partial<Record<MapsStatus, string>> = { no_phone: "text-broken", other: "text-amber", helpline: "text-amber", official: "text-kept" };

/* ---------- Legend swatches (drawn, not data) ---------- */

function Swatch({ children, label }: { children: ReactNode; label: string }) {
  return (
    <li className="flex items-center gap-2">
      <svg viewBox="0 0 24 16" className="h-4 w-6 shrink-0" aria-hidden>{children}</svg>
      <span>{label}</span>
    </li>
  );
}

/* ---------- The page ---------- */

const PEEK = 212;  // how much of the bottom sheet shows on a phone when it is lowered

export default function MapPage() {
  const reduce = useReducedMotion();
  const { data } = useJSON<Overview>("/api/overview");
  const wide = useWide();
  const mapRef = useRef<MapRef>(null);
  const mainRef = useRef<HTMLElement>(null);
  const [height, setHeight] = useState(0);
  const [filter, setFilter] = useState<Filter>("all");
  const [selected, setSelected] = useState<MapPoint | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [tilesFailed, setTilesFailed] = useState(false);
  const [base, setBase] = useState<StyleSpecification | null>(null);
  const [revealed, setRevealed] = useState(false);  // the map has drawn its first full frame, so it can fade in
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const frame = useRef<{ halo: (pulse: number) => ScatterplotLayer<MapPoint>; rest: Layer[] } | null>(null);
  const drag = useDragControls();
  useTitle("Map");

  const mapStyle = useMemo(() => (base ? themedStyle(base, PALETTE) : plainStyle(PALETTE)), [base]);
  useEffect(() => { loadBaseStyle().then(setBase).catch(() => setTilesFailed(true)); }, []);

  // The map fills the window below the header, whatever the header's height.
  useLayoutEffect(() => {
    const fit = () => mainRef.current && setHeight(innerHeight - mainRef.current.getBoundingClientRect().top - scrollY);
    fit();
    addEventListener("resize", fit);
    return () => removeEventListener("resize", fit);
  }, []);

  const colors = useMemo(() => ({ broken: cssColor("--color-broken"), kept: cssColor("--color-kept"), amber: cssColor("--color-amber"),
    card: cssColor("--color-card"), ink: cssColor("--color-ink"), pop: cssColor("--color-pop"), brand: cssColor("--color-brand") }), []);

  // A slow breathing pulse on offices with no phone. It runs outside React: each frame only swaps the halo
  // layer's scale and opacity (deck.gl uniforms), so the page itself never re-renders. Off under reduced motion.
  useEffect(() => {
    if (reduce) return;
    let id = 0;
    const tick = (t: number) => {
      const f = frame.current;
      if (f) overlayRef.current?.setProps({ layers: [f.halo((Math.sin(t / 600) + 1) / 2), ...f.rest] });
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [reduce]);

  const points = useMemo(() => (data?.points ?? []).filter((p) => p.lat !== null && p.lng !== null), [data]);
  // "lookalikes" shows the listings named like an office type, with that type's real offices for comparison.
  const lookalikeTypes = useMemo(() => Object.entries(data?.types ?? {}).filter(([, t]) => t.lookalikes.length).map(([k]) => k), [data]);
  const isShown = (p: MapPoint) => filter === "all" || p.type === filter || p.status === filter || (filter === "lookalikes" && lookalikeTypes.includes(p.type));
  const shown = useMemo(() => points.filter((p) => filter === "all" || p.type === filter || p.status === filter
    || (filter === "lookalikes" && lookalikeTypes.includes(p.type))), [points, filter, lookalikeTypes]);
  const lookalikes = useMemo<Lookalike[]>(() => Object.values(data?.types ?? {}).flatMap((t) => t.lookalikes.map((l) => ({ ...l, of: t.profile.plural })))
    .filter((l) => l.lat !== null && l.lng !== null), [data]);
  const lookalikeOf = Object.values(data?.types ?? {}).filter((t) => t.lookalikes.length).map((t) => t.profile.short);
  const noPhone = useMemo(() => shown.filter((p) => p.status === "no_phone"), [shown]);
  const tone = (p: MapPoint) => colors[MAPS[p.status].tone === "kept" ? "kept" : MAPS[p.status].tone === "amber" ? "amber" : "broken"];
  // One arc from the first office to each other office that shows the same number.
  const arcs = useMemo(() => {
    const byId = Object.fromEntries(points.map((p) => [p.id, p]));
    return (data?.links ?? []).flatMap((l) => l.ids.slice(1).map((id) => ({ from: byId[l.ids[0]], to: byId[id], label: l.display }))).filter((a) => a.from && a.to)
      .map((a) => ({ ...a, km: Math.round(km(a.from, a.to)) }));
  }, [data, points]);

  const halo = (pulse: number) => new ScatterplotLayer<MapPoint>({
    id: "halo", data: noPhone, getPosition: (p) => [p.lng!, p.lat!], getRadius: (p) => radius(p) * 2, radiusUnits: "pixels",
    radiusScale: 1 + pulse * 0.6, opacity: 0.15 + 0.6 * (1 - pulse), getFillColor: [...colors.broken, 46], pickable: false,
  });
  const rest: Layer[] = [
    new ArcLayer<Arc>({
      id: "shared", data: arcs, getSourcePosition: (a) => [a.from.lng!, a.from.lat!], getTargetPosition: (a) => [a.to.lng!, a.to.lat!],
      getSourceColor: [...colors.amber, 255], getTargetColor: [...colors.amber, 255], getWidth: 3, widthUnits: "pixels", getHeight: 0.6,
      pickable: true, autoHighlight: true, highlightColor: [...colors.pop, 255], onClick: ({ object }) => object && showPair(object.from, object.to),
    }),
    new ScatterplotLayer<Lookalike>({
      id: "lookalikes", data: filter === "all" || filter === "lookalikes" ? lookalikes : [], getPosition: (l) => [l.lng!, l.lat!],
      radiusUnits: "pixels", getRadius: 5.5, filled: true, getFillColor: [...colors.amber, 30], stroked: true,
      getLineColor: [...colors.amber, 255], lineWidthUnits: "pixels", getLineWidth: 2, pickable: true, autoHighlight: true,
      highlightColor: [...colors.pop, 120],
    }),
    new ScatterplotLayer<MapPoint>({
      id: "offices", data: shown, getPosition: (p) => [p.lng!, p.lat!], radiusUnits: "pixels", getRadius: radius,
      // Dots grow in from nothing when they appear (on arrival and when a filter adds them) instead of popping in.
      transitions: reduce ? undefined : { getRadius: { duration: 650, easing: (t: number) => 1 - Math.pow(1 - t, 3), enter: () => [0] } },
      getFillColor: (p) => [...tone(p), p.status === "helpline" ? 140 : 255],
      stroked: true, getLineColor: [...colors.card, 255], lineWidthUnits: "pixels", getLineWidth: (p) => (p.type === "subregistrar" ? 1.5 : 2.5),
      pickable: true, autoHighlight: true, highlightColor: [...colors.pop, 255],
      onClick: ({ object }) => object && select(object),
    }),
    // A marigold ring around the office that is open in the card.
    new ScatterplotLayer<MapPoint>({
      id: "selected", data: selected && selected.lat !== null ? [selected] : [], getPosition: (p) => [p.lng!, p.lat!], radiusUnits: "pixels",
      getRadius: (p) => radius(p) + 6, filled: false, stroked: true, getLineColor: [...colors.pop, 255], lineWidthUnits: "pixels", getLineWidth: 3,
      pickable: false,
    }),
  ];
  const layers = [halo(0.5), ...rest];
  useEffect(() => { frame.current = { halo, rest }; });  // what the animation loop above draws from

  // Room the map must leave for the floating panels: the side panel on wide screens, the sheet or card on phones.
  const pad = (card: boolean) => wide ? { left: 420, right: card ? 460 : 60, top: 60, bottom: 60 } : { top: 70, left: 30, right: 30, bottom: card ? 330 : PEEK + 30 };

  // The map mounts only once its style and the offices are both ready, already framed on every office, so it never
  // flashes a blank style, jumps to a new view or drops dots in mid-move. It then fades in on its first full frame.
  const ready = !!data && (!!base || tilesFailed);
  const initialView = useMemo(() => {
    if (!points.length) return { longitude: 77.6, latitude: 12.97, zoom: 10.3, pitch: 30 };
    const lngs = points.map((p) => p.lng!), lats = points.map((p) => p.lat!);
    return { bounds: [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]] as [[number, number], [number, number]],
      fitBoundsOptions: { padding: pad(false) }, pitch: 30 };
  // Only the first framing matters: later resizes keep whatever view the visitor has moved to.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);
  // If tiles are slow (or offline), show the offices anyway rather than wait for the map to settle.
  useEffect(() => {
    if (!ready || revealed) return;
    const t = setTimeout(() => setRevealed(true), 2500);
    return () => clearTimeout(t);
  }, [ready, revealed]);

  /** Fit both offices that share a number into view. */
  function showPair(a: MapPoint, b: MapPoint) {
    setSelected(null);
    setExpanded(false);
    mapRef.current?.fitBounds([[Math.min(a.lng!, b.lng!), Math.min(a.lat!, b.lat!)], [Math.max(a.lng!, b.lng!), Math.max(a.lat!, b.lat!)]], {
      padding: wide ? { left: 460, right: 100, top: 140, bottom: 100 } : { top: 110, left: 50, right: 50, bottom: PEEK + 70 },
      duration: reduce ? 0 : 1600, pitch: 40 });
  }

  function select(p: MapPoint) {
    setSelected(p);
    setExpanded(false);
    if (p.lat === null) return;
    const view = { center: [p.lng!, p.lat!] as [number, number], zoom: 13.6, pitch: 45, padding: pad(true) };
    if (reduce) mapRef.current?.jumpTo(view);  // no flying for people who asked for less motion
    else mapRef.current?.flyTo({ ...view, duration: 1800, curve: 1.6 });
  }

  const counts = (s: MapPoint["status"]) => (data?.points ?? []).filter((p) => p.status === s).length;
  const statuses: MapsStatus[] = ["no_phone", "other", ...(counts("helpline") ? ["helpline" as const] : []), "official"];
  const filters = [{ id: "all", label: "All" }, ...Object.entries(data?.types ?? {}).map(([id, t]) => ({ id, label: capital(t.profile.plural) })),
    { id: "no_phone", label: "No phone" }, ...(lookalikes.length ? [{ id: "lookalikes", label: `Lookalikes · ${lookalikes.length}` }] : [])];

  // The phone sheet: lowered (peeking), raised, or tucked away while an office card is open.
  const sheetMax = Math.max(0, height - 64);
  const sheetY = selected ? sheetMax + 24 : expanded ? 0 : Math.max(0, sheetMax - PEEK);
  const onDragEnd = (_: unknown, info: PanInfo) => {
    if (Math.abs(info.velocity.y) > 300) setExpanded(info.velocity.y < 0);
    else if (Math.abs(info.offset.y) > 60) setExpanded(info.offset.y < 0);
  };

  const panelHead = (
    <>
      <h1 className="headline text-[1.5rem] leading-[1.05] md:text-[2.1rem]">What Google Maps shows for {data ? `${data.points.length} Bengaluru offices` : "each office"}.</h1>
      <div className={cn("mt-4 grid gap-1.5", statuses.length === 4 ? "grid-cols-4" : "grid-cols-3")}>
        {statuses.map((s) => (
          <div key={s} className="rounded-2xl bg-paper-2/80 px-2 py-2.5 text-center">
            <p className={cn("serif tnum text-[1.7rem] leading-none", STAT_TONE[s])}><CountUp value={counts(s)} /></p>
            <p className="mt-1.5 text-[10.5px] leading-tight text-ink-2"><span className="md:hidden">{MAPS[s].short}</span><span className="max-md:hidden">{MAPS[s].label}</span></p>
          </div>
        ))}
      </div>
    </>
  );

  const panelBody = (
    <>
      <div className="mt-4 flex flex-wrap gap-1" role="group" aria-label="Filter offices">
        {filters.map((f) => {
          const on = filter === f.id;
          return (
            <button key={f.id} type="button" onClick={() => setFilter(f.id)} aria-pressed={on}
              className={cn("relative isolate rounded-full px-3 py-1.5 text-xs font-semibold transition-colors duration-300", on ? "text-paper" : "bg-paper-2/70 text-ink-2 hover:text-ink")}>
              {on && <motion.span layoutId="map-filter" aria-hidden className="absolute inset-0 -z-10 rounded-full bg-brand" transition={{ type: "spring", stiffness: 420, damping: 38 }} />}
              {f.label}
            </button>
          );
        })}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] leading-tight text-ink-2" aria-label="Legend">
        <Swatch label="RTO or passport office"><circle cx="12" cy="8" r="6" fill="var(--color-broken)" stroke="var(--color-card)" strokeWidth="1.5" /></Swatch>
        <Swatch label="Sub-registrar office"><circle cx="12" cy="8" r="4" fill="var(--color-broken)" stroke="var(--color-card)" strokeWidth="1" /></Swatch>
        {counts("helpline") > 0 && <Swatch label="Paler amber: a helpline"><circle cx="12" cy="8" r="5" fill="var(--color-amber)" opacity="0.55" /></Swatch>}
        {lookalikes.length > 0 && <Swatch label={`Hollow ring: named like a ${lookalikeOf.join(" or ")}, not on the official list`}><circle cx="12" cy="8" r="4.5" fill="none" stroke="var(--color-amber)" strokeWidth="2" /></Swatch>}
        {arcs.length > 0 && <Swatch label="Arc: one number on two listings"><path d="M2 14 Q12 -2 22 14" fill="none" stroke="var(--color-amber)" strokeWidth="2" /></Swatch>}
        {!reduce && <Swatch label="Pulse: no phone on the listing"><circle cx="12" cy="8" r="7" fill="var(--color-broken)" opacity="0.18" /><circle cx="12" cy="8" r="4" fill="var(--color-broken)" /></Swatch>}
      </ul>
      {(data?.links.length ?? 0) > 0 && (
        <div className="mt-4 space-y-2 rounded-2xl bg-amber-soft px-3.5 py-3 text-xs leading-relaxed text-amber ring-1 ring-inset ring-current/15">
          {data!.links.map((l) => (
            <p key={l.display + l.ids.join()}>
              <b>One number, {l.names.length} offices.</b> The Google Maps listings of {l.names.join(l.names.length === 2 ? " and " : ", ")} {l.names.length === 2 ? "both " : "all "}
              show {l.display}, which isn't in the department's directory.{" "}
              {arcs.filter((a) => l.ids.includes(a.from.id)).map((a) => (
                <button key={a.to.id} type="button" onClick={() => showPair(a.from, a.to)} className="font-semibold underline underline-offset-2">
                  Show the {a.km} km line
                </button>
              ))}
            </p>
          ))}
        </div>
      )}
    </>
  );

  const list = (
    <ul className="p-2" aria-label="Offices">
      {(data?.points ?? []).filter(isShown).sort((a, b) => a.label.localeCompare(b.label)).map((p) => (
        <li key={p.id}>
          <button type="button" onClick={() => select(p)} aria-current={selected?.id === p.id || undefined}
            className={cn("group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-[13px] transition-colors hover:bg-paper-2/80",
              selected?.id === p.id && "bg-wash text-ink")}>
            <span className={cn("size-2.5 shrink-0 rounded-full", p.status === "no_listing" ? "border-2 border-broken" : toneBg[MAPS[p.status].tone],
              p.status === "helpline" && "opacity-60")} />
            <span className="flex-1 truncate">{p.label}</span>
            <span className="tnum text-[11px] text-muted">{p.lat === null ? "not on map" : p.score !== null ? p.score : ""}</span>
          </button>
        </li>
      ))}
    </ul>
  );

  const card = selected && (
    <motion.div key={selected.id} initial={reduce ? false : { opacity: 0, y: 24, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 24, scale: 0.98 }} transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }} role="dialog" aria-label={selected.label}
      className="glass absolute z-20 rounded-[1.75rem] border border-rule/70 p-5 shadow-[var(--shadow-float)] md:bottom-6 md:right-6 md:w-[400px] max-md:inset-x-3 max-md:bottom-3">
      <button type="button" onClick={() => setSelected(null)} className="absolute right-3.5 top-3.5 grid size-8 place-items-center rounded-full text-muted transition hover:bg-paper-2 hover:text-ink" aria-label="Close">
        <X className="size-4" />
      </button>
      <h2 className="headline pr-8 text-[1.6rem] leading-[1.08]">{selected.label}</h2>
      <dl className="mt-4 grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 border-t border-rule pt-4 text-[13px]">
        <dt className="text-muted">Google Maps</dt>
        <dd className="flex flex-wrap items-center gap-1.5"><Chip tone={MAPS[selected.status].tone}>{MAPS[selected.status].short}</Chip>
          {selected.phone && <Mono className="font-semibold">{selected.phone}</Mono>}{selected.unclaimed && <Chip tone="amber">Unclaimed</Chip>}</dd>
        <dt className="text-muted">AI Overview</dt><dd><Chip tone={AI[selected.ai].tone}>{AI[selected.ai].short}</Chip></dd>
        <dt className="text-muted">AI Mode</dt><dd><Chip tone={AI[selected.mode].tone}>{AI[selected.mode].short}</Chip></dd>
        {selected.bing && <><dt className="text-muted">Bing Maps</dt><dd><Chip tone={BING[selected.bing].tone}>{BING[selected.bing].label}</Chip></dd></>}
      </dl>
      <p className="mt-3 text-[13px] text-muted">
        {selected.reviews.toLocaleString("en-IN")} reviews{selected.score !== null ? ` · listing score ${selected.score}/100` : ""}{selected.lat === null ? " · not on the map" : ""}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to={`/office/${selected.id}`} className="inline-flex items-center gap-1.5 rounded-full bg-brand px-4 py-2 text-sm font-semibold text-paper shadow-sm transition hover:brightness-110">
          Open the office <ArrowRight className="size-4" />
        </Link>
        <Link to={`/?office=${selected.id}`} className="inline-flex items-center gap-1.5 rounded-full border border-rule bg-card/70 px-4 py-2 text-sm font-semibold text-ink transition hover:border-ink-2">
          <MessageCircleQuestion className="size-4" /> Ask about it
        </Link>
      </div>
    </motion.div>
  );

  return (
    <main ref={mainRef} className="kal-map relative overflow-hidden" style={{ height: height || "calc(100dvh - 6rem)" }}>
      {!ready && <div aria-hidden className="absolute inset-0 animate-pulse bg-paper-2/70" />}
      {ready && (
      <div className={cn("absolute inset-0 transition-opacity duration-700 ease-[var(--ease-out-expo)]", revealed ? "opacity-100" : "opacity-0")}>
      <MapGL ref={mapRef} initialViewState={initialView} maxPitch={60}
        mapStyle={mapStyle} attributionControl={{ compact: true }} style={{ width: "100%", height: "100%" }}
        onLoad={(e) => e.target.once("idle", () => setRevealed(true))}
        onError={() => setTilesFailed(true)} onData={(e) => { if (e.dataType === "source" && "isSourceLoaded" in e && e.isSourceLoaded) setTilesFailed(false); }}>
        <NavigationControl position={wide ? "bottom-right" : "top-right"} />
        <DeckOverlay overlayRef={overlayRef} layers={layers} getTooltip={({ object }: { object?: MapPoint | Arc | Lookalike }) => {
          if (!object) return null;
          const text = "pincode" in object
            ? `"${object.title}"\nNamed like one of the ${object.of}, but not on the official list.\nGoogle lists it as: ${object.category || "no category"} · PIN ${object.pincode}`
            : "from" in object
            ? `Same phone number on both Google Maps listings: ${object.label}\n${object.from.label}\n${object.to.label}\nAbout ${object.km} km apart in a straight line. Not in the department's directory.`
            : object.label ? `${object.label}\n${MAPS[object.status].label}` : null;
          return text && { text, className: "deck-tooltip", style: {
            background: `rgb(${colors.card.join(" ")} / 0.94)`, color: `rgb(${colors.ink.join(" ")})`, borderRadius: "14px", padding: "10px 12px",
            font: "500 12px/1.45 'Inter Variable', system-ui, sans-serif", maxWidth: "280px", boxShadow: "var(--shadow-float)",
            border: "1px solid var(--color-rule)", backdropFilter: "blur(12px)" } };
        }} />
      </MapGL>
      </div>
      )}

      {tilesFailed && (
        <p role="status" className="glass absolute right-3 top-3 z-10 flex max-w-xs items-start gap-2 rounded-2xl border border-rule/70 px-4 py-3 text-sm text-ink-2 shadow-[var(--shadow-soft)] max-md:left-3 max-md:right-14 max-md:max-w-none">
          <WifiOff className="mt-0.5 size-4 shrink-0 text-broken" aria-hidden />
          The street map couldn't load, probably because you're offline. The offices are still plotted; the list works as normal.
        </p>
      )}

      {wide ? (
        <motion.aside initial={reduce ? false : { opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="glass absolute bottom-4 left-4 top-4 z-10 flex w-[380px] flex-col overflow-hidden rounded-[1.75rem] border border-rule/70 shadow-[var(--shadow-float)]">
          <div className="border-b border-rule/70 p-5">{panelHead}{panelBody}</div>
          <div className="flex-1 overflow-y-auto overscroll-contain">{list}</div>
        </motion.aside>
      ) : (
        <motion.aside initial={reduce ? false : { y: sheetMax }} animate={{ y: sheetY }} transition={{ type: "spring", stiffness: 380, damping: 40 }}
          drag="y" dragListener={false} dragControls={drag} dragConstraints={{ top: 0, bottom: sheetMax - PEEK }} dragElastic={0.06} onDragEnd={onDragEnd}
          style={{ height: sheetMax }} aria-label="Offices on the map"
          className="glass absolute inset-x-0 bottom-0 z-10 flex flex-col overflow-hidden rounded-t-[1.75rem] border-t border-rule/70 shadow-[0_-12px_40px_-16px_rgb(28_21_48/0.35)]">
          <div className="touch-none px-5 pb-3" onPointerDown={(e) => drag.start(e)}>
            <button type="button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}
              className="mx-auto flex h-6 w-full items-center justify-center" aria-label={expanded ? "Lower the office list" : "Raise the office list"}>
              <span className="h-1.5 w-11 rounded-full bg-muted/40" />
            </button>
            {panelHead}
          </div>
          <div className="flex-1 overflow-y-auto overscroll-contain border-t border-rule/70">
            <div className="px-5 pb-1">{panelBody}</div>
            {list}
          </div>
        </motion.aside>
      )}

      <AnimatePresence>{card}</AnimatePresence>
    </main>
  );
}
