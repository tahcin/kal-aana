// The timeline of the "unanswered call" hero. One office number at a time comes into focus, is dialled digit by
// digit (the rotary dial in the corner turns with it), rings in the Indian double-ring cadence, and goes quiet. Then a
// warm marigold light leaves the number and settles round the ask box: the answer is here. The DOM numbers and the
// shader share this one clock, so the rings always leave from the number being dialled.
import { MAX_ORB, MAX_WAVES, Renderer, type Frame } from "./renderer";
import type { HeroSignals } from "./signals";

const FOCUS = 0.75;     // rack focus to the number before dialling starts
const DIGIT = 0.19;     // one dialled digit
const FIRST_RING = 0.5; // after the last digit
const RING_GAP = 2.45;  // a double ring, then the pause
const RINGS = 3;
const ECHO = 0.42;      // the second ring of each double ring
const ORB_DUR = 2.5;
const NEXT = 4.4;       // the answer glows on its own before the next call

const DEPTH = { near: 1.16, mid: 1, far: 0.84 } as const;
export type Depth = keyof typeof DEPTH;

type Frag = { el: HTMLElement; dot: HTMLElement; digits: HTMLElement[]; values: number[]; depth: Depth; calls: boolean; seed: number; ringUntil: number; off: boolean };
type Call = { frag: Frag; t0: number; dialAt: number; rings: number[]; fired: number; quietAt: number; orbAt: number; nextAt: number;
  from: [number, number]; path: [number, number][] };
type Rect = { x: number; y: number; w: number; h: number };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);
const smooth = (a: number, b: number, v: number) => { const t = clamp01((v - a) / (b - a)); return t * t * (3 - 2 * t); };

export class Director {
  private renderer: Renderer;
  private frags: Frag[] = [];
  private t = 0;
  private call: Call | null = null;
  private nextCallAt = 0.6;
  private order = 0;
  private waves = new Float32Array(MAX_WAVES * 4);
  private amps = new Float32Array(MAX_WAVES);
  private head = 0;
  private orb = new Float32Array(MAX_ORB * 4);
  private halo: { x: number; y: number; at: number; reach: number } | null = null;
  private dialAngle = 0;
  private pointer = { x: 0, y: 0, sx: 0, sy: 0 };
  private swirlFrom = -1;
  private size = { w: 1, h: 1 };
  private box: Rect = { x: 0, y: 0, w: 1, h: 1 };
  private boxR = 30;
  private calm: [number, number, number, number] = [0, 0, 1, 1];
  private drawn = false;
  private clearRight = 0;

  private root: HTMLElement;
  private layer: HTMLElement;
  private signals: HeroSignals;
  private dense: boolean;
  private onFirstDraw: () => void;

  constructor(canvas: HTMLCanvasElement, root: HTMLElement, layer: HTMLElement, signals: HeroSignals, dense: boolean, onFirstDraw: () => void) {
    this.renderer = new Renderer(canvas, dense ? 1.5 : 1.25);
    this.root = root; this.layer = layer; this.signals = signals; this.dense = dense; this.onFirstDraw = onFirstDraw;
  }

  /** The number elements, read from the DOM after React renders them. */
  setFragments(els: HTMLElement[]) {
    this.frags = els.map((el, i) => {
      const digits = [...el.querySelectorAll<HTMLElement>("[data-digit]")];
      return {
        el, dot: el.querySelector<HTMLElement>("[data-dot]")!, digits, values: digits.map((d) => Number(d.textContent) || 10),
        depth: (el.dataset.depth as Depth) ?? "mid", calls: el.dataset.calls === "1", seed: i * 1.7 + 0.3, ringUntil: 0, off: false,
      };
    });
    this.call = null;
    this.nextCallAt = this.t + 0.6;
    this.fit();
  }

  /** Re-read where the headline and the ask box sit, so the scene keeps clear of one and answers into the other. */
  measure() {
    const r = this.root.getBoundingClientRect();
    this.size = { w: r.width, h: r.height };
    this.renderer.resize(r.width, r.height);
    this.measureBox();
    const panel = this.root.closest(".kh-hero") ?? this.root;
    const title = panel.querySelector("#hero-title");
    if (title) {
      const t = title.getBoundingClientRect();
      const sub = title.nextElementSibling?.getBoundingClientRect();
      const bottom = sub ? sub.bottom : t.bottom;
      this.calm = [t.left - r.left + t.width / 2, (t.top + bottom) / 2 - r.top, t.width * 0.62, (bottom - t.top) * 0.66];
    } else {
      this.calm = [r.width / 2, r.height * 0.42, r.width * 0.3, r.height * 0.3];
    }
    this.fit();
  }

  /** Hide any number that would touch the words or the ask box at this size (short or narrow windows), and keep the
   *  dial to the right of the box and the examples. */
  private fit() {
    const r = this.root.getBoundingClientRect();
    const panel = this.root.closest(".kh-hero") ?? this.root;
    const pad = 12;
    const rect = (q: string): Rect | null => {
      const b = panel.querySelector(q)?.getBoundingClientRect();
      return b ? { x: b.left - r.left, y: b.top - r.top, w: b.width, h: b.height } : null;
    };
    const chips = rect('[aria-label="Example questions"]');
    const blocks = [rect("#hero-title"), rect("#hero-title + p"), chips, this.box].filter((b): b is Rect => !!b);
    this.clearRight = Math.max(this.box.x + this.box.w, chips ? chips.x + chips.w : 0);
    for (const f of this.frags) {
      const e = f.el.getBoundingClientRect();
      const x = e.left - r.left, y = e.top - r.top;
      f.off = blocks.some((b) => x < b.x + b.w + pad && x + e.width > b.x - pad && y < b.y + b.h + pad && y + e.height > b.y - pad);
      if (f.off) f.el.dataset.off = ""; else delete f.el.dataset.off;
    }
  }

  /** The ask box grows and shrinks with the example in it, so this is re-read whenever the answer is glowing round it. */
  private measureBox() {
    const r = this.root.getBoundingClientRect();
    // The whole ask box (Composer marks it), so the glow wraps its true outline, round ends included.
    const boxEl = (this.root.closest(".kh-hero") ?? this.root).querySelector<HTMLElement>("[data-ask-box]");
    if (boxEl) {
      const b = boxEl.getBoundingClientRect();
      this.box = { x: b.left - r.left, y: b.top - r.top, w: b.width, h: b.height };
      this.boxR = Math.min(parseFloat(getComputedStyle(boxEl).borderTopLeftRadius) || 30, b.height / 2);
    } else {
      this.box = { x: r.width * 0.25, y: r.height * 0.66, w: r.width * 0.5, h: 96 };
    }
  }

  /** Render at a fraction of full resolution (1 = full); the scene is soft enough that 0.6 still looks the same. */
  setQuality(q: number) {
    this.renderer.setQuality(q);
  }

  setPointer(clientX: number, clientY: number) {
    const r = this.root.getBoundingClientRect();
    this.pointer.x = clamp01((clientX - r.left) / r.width) * 2 - 1;
    this.pointer.y = clamp01((clientY - r.top) / r.height) * 2 - 1;
  }

  /** One frame of the living scene. */
  tick(dt: number) {
    dt = Math.min(dt, 1 / 20);
    this.t += dt;
    const t = this.t;
    const p = this.pointer;
    p.sx += (p.x - p.sx) * Math.min(1, dt * 2.2);
    p.sy += (p.y - p.sy) * Math.min(1, dt * 2.2);

    // A new example question: somewhere else in the city, another phone rings.
    if (this.signals.gust > 0.5) {
      this.signals.gust = 0;
      const others = this.frags.filter((f) => f !== this.call?.frag && !f.off);
      const f = others[Math.floor(Math.random() * others.length)];
      if (f) this.ring(f, 0.55, DEPTH[f.depth]);
    }

    if (!this.call && t >= this.nextCallAt) this.startCall();
    const c = this.call;
    let dialTarget = 0;
    if (c) {
      const into = (t - c.dialAt) / DIGIT;
      const lit = Math.max(0, Math.min(c.frag.digits.length, Math.floor(into) + 1));
      if (t < c.quietAt) c.frag.digits.forEach((d, i) => { if (i < lit) d.dataset.lit = ""; });
      if (into >= 0 && into < c.frag.values.length) {
        // The wheel winds with the finger, then springs back: further for higher digits, as a real dial does.
        const k = Math.floor(into), u = into - k;
        const wind = u < 0.45 ? easeOut(u / 0.45) : 1 - easeInOut((u - 0.45) / 0.55);
        dialTarget = c.frag.values[k] * 0.055 * wind;
      }
      while (c.fired < c.rings.length && t >= c.rings[c.fired]) { this.ring(c.frag, 1, 1); c.fired++; }
      if (t >= c.quietAt && c.frag.el.dataset.focus !== undefined) {
        delete c.frag.el.dataset.focus;
        c.frag.digits.forEach((d) => delete d.dataset.lit);
      }
      if (t >= c.nextAt) { this.call = null; this.nextCallAt = t; }
    }
    this.dialAngle += (dialTarget - this.dialAngle) * Math.min(1, dt * 22);
    this.updateOrb(c);
    for (const f of this.frags) {
      if (f.ringUntil && t > f.ringUntil) { delete f.el.dataset.ring; f.ringUntil = 0; }
    }

    // Sending: the rings fall quiet and the warm light gathers into the box.
    let swirl = 0;
    const sw = this.signals.swirl;
    if (sw) {
      if (this.swirlFrom < 0) { this.swirlFrom = t; this.measure(); }
      swirl = easeInOut(clamp01((t - this.swirlFrom) / (sw.ms / 1000)));
    } else if (this.swirlFrom >= 0) {
      this.swirlFrom = -1;
    }
    if (this.halo || swirl) this.measureBox();
    this.layer.style.opacity = String(1 - swirl * 0.75);
    this.place();
    this.draw(swirl);
  }

  /** Reduced motion: one composed moment, mid-call, with the answer already warm round the box. */
  still() {
    this.t = 20;
    this.measure();
    const f = this.frags.find((x) => x.calls && !x.off);
    this.amps.fill(0);
    this.orb.fill(0);
    if (f) {
      f.el.dataset.focus = "";
      f.digits.forEach((d) => (d.dataset.lit = ""));
      const [x, y] = this.dotAt(f);
      [1.1, 1.1 + ECHO, 3.3, 3.3 + ECHO].forEach((age, i) => this.push(x, y, this.t - age, 1, i % 2 ? 0.8 : 1));
      const target = this.targetFor(x, y);
      this.halo = { x: target[0], y: target[1], at: this.t - 3, reach: 0 };
    }
    this.place();
    this.draw(0);
  }

  dispose() {
    this.renderer.dispose();
  }

  private startCall() {
    const callers = this.frags.filter((f) => f.calls && !f.off);
    if (!callers.length) return;
    const frag = callers[this.order++ % callers.length];
    this.measure();
    const t = this.t, dialAt = t + FOCUS;
    const lastDigit = dialAt + frag.digits.length * DIGIT;
    const rings = Array.from({ length: RINGS }, (_, i) => lastDigit + FIRST_RING + i * RING_GAP);
    const quietAt = rings[RINGS - 1] + 1.9;
    frag.el.dataset.focus = "";
    this.call = { frag, t0: t, dialAt, rings, fired: 0, quietAt, orbAt: quietAt - 0.5, nextAt: quietAt + NEXT, from: [0, 0], path: [] };
  }

  private ring(f: Frag, amp: number, depth: number) {
    const [x, y] = this.dotAt(f);
    this.push(x, y, this.t, depth, amp);
    this.push(x, y, this.t + ECHO, depth, amp * 0.8);
    f.el.dataset.ring = "";
    f.ringUntil = this.t + 1.2;
    // Restart the dot's pulse even if it is already pulsing.
    f.dot.style.animation = "none";
    void f.dot.offsetWidth;
    f.dot.style.animation = "";
  }

  private push(x: number, y: number, born: number, depth: number, amp: number) {
    const i = this.head++ % MAX_WAVES;
    this.waves.set([x, y, born, depth], i * 4);
    this.amps[i] = amp;
  }

  private dotAt(f: Frag): [number, number] {
    const r = this.root.getBoundingClientRect(), d = f.dot.getBoundingClientRect();
    return [d.left - r.left + d.width / 2, d.top - r.top + d.height / 2];
  }

  /** Where the answer enters the box: the side facing the number, so its path skirts the headline. */
  private targetFor(x: number, y: number): [number, number] {
    const b = this.box;
    if (x < b.x) return [b.x + 6, b.y + b.h / 2];
    if (x > b.x + b.w) return [b.x + b.w - 6, b.y + b.h / 2];
    return [Math.min(b.x + b.w - 40, Math.max(b.x + 40, x)), y < b.y ? b.y + 4 : b.y + b.h - 4];
  }

  private updateOrb(c: Call | null) {
    this.orb.fill(0);
    if (c && this.t >= c.orbAt && !c.path.length) {
      // Leave the number heading toward the box's height, then come in level with the side it enters by.
      const [x0, y0] = this.dotAt(c.frag);
      const [x3, y3] = this.targetFor(x0, y0);
      const nx = x0 < this.box.x ? -1 : x0 > this.box.x + this.box.w ? 1 : 0;
      const ny = nx ? 0 : y0 < this.box.y ? -1 : 1;
      c.path = [[x0, y0], [x0 + (x3 - x0) * 0.1, y0 + (y3 - y0) * 0.75], [x3 + nx * 170, y3 + ny * 120], [x3, y3]];
    }
    if (c && c.path.length) {
      const u = (this.t - c.orbAt) / ORB_DUR;
      if (u >= 0 && u <= 1.2) {
        const env = smooth(0, 0.18, u) * (1 - smooth(0.8, 1, u));
        // A bright core, a soft glow round it, and a fading tail along the path behind.
        const [hx, hy] = bezier(c.path, easeInOut(clamp01(u)));
        this.orb.set([hx, hy, env * 0.95, 9, hx, hy, env * 0.32, 40], 0);
        for (let j = 2; j < MAX_ORB; j++) {
          const [x, y] = bezier(c.path, easeInOut(clamp01(u - (j - 1) * 0.008)));
          const fall = Math.pow(1 - (j - 2) / (MAX_ORB - 2), 1.8);
          this.orb.set([x, y, env * 0.3 * fall, 15 - j * 0.5], j * 4);
        }
        if (u >= 0.9 && (!this.halo || this.halo.at < c.orbAt)) {
          const [x, y] = c.path[3];
          this.halo = { x, y, at: this.t, reach: 0 };
        }
      }
    }
  }

  /** Drift the numbers in depth and let them part a little with the pointer, the near ones most. */
  private place() {
    const t = this.t, p = this.pointer;
    for (const f of this.frags) {
      const k = f.depth === "near" ? 1.7 : f.depth === "mid" ? 1 : 0.5;
      const x = Math.sin(t * 0.13 + f.seed * 5) * 5 * k - p.sx * 12 * k;
      const y = Math.cos(t * 0.1 + f.seed * 3) * 4 * k - p.sy * 8 * k;
      f.el.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`;
    }
  }

  private draw(swirl: number) {
    const { w, h } = this.size, b = this.box, t = this.t;
    let halo: [number, number, number, number] = [0, 0, 0, 0];
    if (this.halo) {
      const a = t - this.halo.at;
      const warmth = smooth(0, 0.6, a) * Math.exp(-Math.max(0, a - 1.4) * 0.55);
      halo = [this.halo.x, this.halo.y, warmth, 30 + (b.w * 1.3 + b.h) * easeOut(clamp01(a / 2.2))];
      if (warmth < 0.002 && a > 2) this.halo = null;
    }
    const amps = swirl ? this.amps.map((a) => a * (1 - swirl)) : this.amps;
    // The dial: half of it in from the right edge on a wide screen, a corner of it below the examples on a phone.
    const R = this.dense ? h * 0.5 : Math.min(w * 0.46, h * 0.26);
    const [dx, dy] = this.dense ? [Math.max(w + R * 0.34, this.clearRight + 36 + R), h * 0.56] : [w + R * 0.06, h + R * 0.2];
    const frame: Frame = {
      time: t, waves: this.waves, amps, orb: this.orb, swirl,
      box: [b.x + b.w / 2, b.y + b.h / 2, b.w / 2, b.h / 2, this.boxR],
      halo,
      dial: [dx - this.pointer.sx * 14, dy - this.pointer.sy * 10, R, this.dialAngle],
      dialSoft: this.dense ? 0.034 : 0.04,
      calm: this.calm,
    };
    this.renderer.draw(frame);
    if (!this.drawn) { this.drawn = true; requestAnimationFrame(this.onFirstDraw); }
  }
}

function bezier(p: [number, number][], t: number): [number, number] {
  const m = 1 - t;
  const a = m * m * m, b = 3 * m * m * t, c = 3 * m * t * t, d = t * t * t;
  return [a * p[0][0] + b * p[1][0] + c * p[2][0] + d * p[3][0], a * p[0][1] + b * p[1][1] + c * p[2][1] + d * p[3][1]];
}
