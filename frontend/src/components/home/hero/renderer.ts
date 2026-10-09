// One full-screen WebGL2 shader for the "unanswered call" hero: the sky, a rotary dial in soft focus in the corner,
// the ring tones spreading out as ripples that bend the light behind them, and the marigold answer settling round
// the ask box. Raw WebGL2 rather than three: it is a single triangle, so the chunk stays a few kilobytes.

export const MAX_WAVES = 16;
export const MAX_ORB = 16;

/** Everything the shader needs for one frame, in CSS px with the origin at the scene's top left. */
export type Frame = {
  time: number;
  /** x, y, born (s), depth (1 = the focus plane) per wavefront. */
  waves: Float32Array;
  amps: Float32Array;
  /** The ask box: centre x, y, half width, half height, corner radius. */
  box: [number, number, number, number, number];
  /** Where the answer reached the box, how warm, and how far round the box it has spread. */
  halo: [number, number, number, number];
  /** x, y, intensity, radius for the travelling marigold light and its trail. */
  orb: Float32Array;
  swirl: number;
  /** The dial: centre x, y, radius, wheel rotation (radians), and how soft its focus is. */
  dial: [number, number, number, number];
  dialSoft: number;
  /** An ellipse round the headline where the scene keeps quiet: centre x, y, radius x, y. */
  calm: [number, number, number, number];
};

const VERT = `#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2. - 1., 0., 1.);
}`;

const FRAG = `#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2 uSize;
uniform float uDpr, uTime, uSwirl, uDialSoft;
uniform vec4 uWave[${MAX_WAVES}];
uniform float uAmp[${MAX_WAVES}];
uniform vec4 uOrb[${MAX_ORB}];
uniform vec4 uBox;
uniform float uBoxR;
uniform vec4 uHalo, uDial, uCalm;

const float PI = 3.14159265;
const float HOLE_R = .118, HOLE_C = .69, WHEEL = .9, CAP = .31;

float sdRound(vec2 p, vec2 b, float r) { vec2 q = abs(p) - b + r; return length(max(q, 0.)) + min(max(q.x, q.y), 0.) - r; }
mat2 rot2(float a) { float c = cos(a), s = sin(a); return mat2(c, -s, s, c); }
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

// Late light through a window: lavender above, warm cream below, the corners falling away to violet.
vec3 sky(vec2 p) {
  vec2 q = p / uSize;
  vec3 day = mix(vec3(.886, .847, .976), vec3(.961, .937, .965), smoothstep(0., .6, q.y));
  day = mix(day, vec3(.996, .945, .898), smoothstep(.5, 1., q.y));
  vec2 k = (q - vec2(.8, -.08)) * vec2(1., 1.5);
  day += vec3(1., .97, .93) * exp(-dot(k, k) * 2.6) * .1;
  float vig = smoothstep(.5, 1.25, length((q - vec2(.5, .42)) * vec2(1.15, 1.)));
  return mix(day, vec3(.72, .64, .92), vig * .34);
}

// The rotary dial's finger wheel: ten holes over 300 degrees, the gap (and the finger stop) out of frame.
vec2 holeVec(vec2 w) {
  float start = radians(100.);
  float k = floor(mod(atan(w.y, w.x) - start + PI / 12., 2. * PI) / (PI / 6.));
  if (k > 10.5) k = 0.;
  k = min(k, 9.);
  float th = start + k * PI / 6.;
  return w - HOLE_C * vec2(cos(th), sin(th));
}
float dialHeight(vec2 l) {
  float bw = uDialSoft, r = length(l);
  float plate = 1. - smoothstep(1. - bw, 1. + bw, r);
  float wheel = 1. - smoothstep(WHEEL - bw, WHEEL + bw, r);
  float hole = 1. - smoothstep(HOLE_R - bw, HOLE_R + bw, length(holeVec(rot2(uDial.w) * l)));
  float cap = 1. - smoothstep(CAP - bw, CAP + bw, r);
  return plate * .22 + wheel * (1. - hole) * .55 + cap * (.1 + .14 * max(0., 1. - r * r / (CAP * CAP)));
}

// The room: sky plus the dial, lit like a product shot (a big soft key from the top left, a rim from the right).
vec3 room(vec2 p) {
  vec3 col = sky(p);
  vec2 l = (p - uDial.xy) / uDial.z;
  float r = length(l);
  float shadow = 1. - smoothstep(.92, 1.4, length(l - vec2(.05, .07)));
  col *= 1. - shadow * .13;
  if (r > 1.1) return col;

  float e = .01, h = dialHeight(l);
  vec2 g = vec2(dialHeight(l + vec2(e, 0.)) - h, dialHeight(l + vec2(0., e)) - h) / e;
  vec3 n = normalize(vec3(-g * .05, 1.));
  vec3 L = normalize(vec3(-.55, -.7, .62));
  float dif = max(dot(n, L), 0.);
  float spec = pow(max(dot(n, normalize(L + vec3(0., 0., 1.))), 0.), 14.);
  float rim = pow(max(dot(n, normalize(vec3(.8, -.2, .25))), 0.), 6.);

  float bw = uDialSoft;
  vec2 v = holeVec(rot2(uDial.w) * l);
  float hd = length(v);
  float hole = 1. - smoothstep(HOLE_R - bw, HOLE_R + bw, hd);
  float wheel = (1. - smoothstep(WHEEL - bw, WHEEL + bw, r)) * (1. - hole);
  float cap = 1. - smoothstep(CAP - bw, CAP + bw, r);
  float plate = 1. - smoothstep(1. - bw * 1.4, 1. + bw * 1.4, r);
  // The floor of each hole is the plate, half in the shadow its top-left wall casts.
  float sun = 1. - smoothstep(HOLE_R - bw * 1.6, HOLE_R + bw * 1.6, length(v - vec2(.045, .055)));
  float ao = mix(1., mix(.66, 1., sun), hole * (1. - cap));

  vec3 albedo = mix(vec3(.97, .94, .89), vec3(.64, .56, .9), wheel);
  albedo = mix(albedo, vec3(.985, .965, .93), cap);
  vec3 lit = albedo * (vec3(.93, .9, 1.) * .62 + dif * .5) * mix(vec3(.78, .7, .95), vec3(1.), ao * ao);
  lit *= mix(1., ao, .5);
  lit += spec * .22 * vec3(1., .97, .94) * (.12 + wheel * .88);
  lit += rim * vec3(.15, .1, .25) * .35;
  return mix(col, lit, plate);
}

void main() {
  vec2 p = vec2(gl_FragCoord.x, uSize.y * uDpr - gl_FragCoord.y) / uDpr;
  float calm = mix(.06, 1., smoothstep(.62, 1.22, length((p - uCalm.xy) / uCalm.zw)));

  // Ring tones: each wavefront is a thin crisp line (soft when it is off the focus plane) riding a broad swell that
  // bends whatever is behind it, then thins out into silence.
  float line = 0., band = 0.;
  vec2 disp = vec2(0.);
  for (int i = 0; i < ${MAX_WAVES}; i++) {
    float a = uAmp[i];
    if (a <= 0.) continue;
    vec4 w = uWave[i];
    float age = uTime - w.z;
    if (age <= 0.) continue;
    vec2 d = p - w.xy;
    float r = length(d) + 1e-3;
    float R = uSize.y * .8 * w.w * (1. - exp(-age * .6));
    float env = smoothstep(0., .12, age) * exp(-age * .62) * (1. - smoothstep(3.6, 4.8, age)) * a;
    float lw = 1.2 + 7. * abs(w.w - 1.) + age * .6;
    float s = r - R;
    // The front, two fainter echoes trailing inside it, and a soft light band behind, brightest at the front.
    float e1 = s + 13. * w.w, e2 = s + 28. * w.w;
    float lines = exp(-s * s / (lw * lw)) + .45 * exp(-e1 * e1 / (lw * lw * 2.)) + .2 * exp(-e2 * e2 / (lw * lw * 3.));
    float b = s < 0. ? exp(s / (48. * w.w)) : exp(-s * s / (lw * lw * 3.));
    line += lines * env * 1.8 / (1. + lw * .45);
    band += b * env;
    float gw = 26. * w.w + R * .05;
    disp += d / r * (s / gw) * exp(-s * s / (gw * gw)) * env;
  }
  line *= calm; band *= calm; disp *= calm;

  vec3 col = room(p - disp * 9.);
  col = mix(col, vec3(1., .99, 1.), clamp(band, 0., 1.) * .26);
  col = mix(col, vec3(.35, .24, .74), clamp(line, 0., 1.) * .62);

  // The answer: marigold light that travels to the ask box and settles round it.
  float sd = sdRound(p - uBox.xy, uBox.zw, uBoxR);
  float reach = 1. - smoothstep(uHalo.w * .55, uHalo.w + 1., length(p - uHalo.xy));
  float warm = uHalo.z * reach * (exp(-max(sd, 0.) / 46.) * .62 + exp(-max(sd, 0.) / 120.) * .22 + exp(-(sd - 2.5) * (sd - 2.5) / 26.) * .8) * step(-3., sd);
  if (uSwirl > 0.) {
    // Sending: three thin warm rings close in on the box, one after another, and the box takes the glow.
    for (int k = 0; k < 3; k++) {
      float t = clamp(uSwirl * 1.35 - float(k) * .17, 0., 1.);
      float rr = 150. * pow(1. - t, 1.8);
      warm += exp(-(sd - rr) * (sd - rr) / 30.) * sin(PI * t) * .55 * mix(.25, 1., calm) * step(-3., sd);
    }
    warm += uSwirl * (exp(-max(sd, 0.) / 50.) * .65 + exp(-max(sd, 0.) / 140.) * .2) * step(-3., sd);
  }
  float orb = 0.;
  for (int i = 0; i < ${MAX_ORB}; i++) {
    vec4 o = uOrb[i];
    if (o.z <= 0.) continue;
    vec2 d = p - o.xy;
    orb += o.z * exp(-dot(d, d) / (o.w * o.w));
  }
  warm += orb * mix(.4, 1., calm);
  warm = clamp(warm, 0., 1.4);
  vec3 pop = vec3(1., .7, .1);
  col = mix(col, pop, min(warm, 1.) * .62) + pop * warm * .06;

  col += (hash(p * uDpr + fract(uTime)) - .5) / 255.;
  outColor = vec4(col, 1.);
}`;

export class Renderer {
  private gl: WebGL2RenderingContext;
  private prog: WebGLProgram;
  private loc: Record<string, WebGLUniformLocation | null> = {};
  private dpr = 1;
  private w = 1;
  private h = 1;

  private canvas: HTMLCanvasElement;
  private maxDpr: number;

  constructor(canvas: HTMLCanvasElement, maxDpr: number) {
    this.canvas = canvas; this.maxDpr = maxDpr;
    const gl = canvas.getContext("webgl2", { antialias: false, alpha: false, depth: false, stencil: false, powerPreference: "high-performance" });
    if (!gl) throw new Error("webgl2 unavailable");
    this.gl = gl;
    const shader = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) ?? "shader");
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, shader(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog) ?? "link");
    this.prog = prog;
    gl.useProgram(prog);
    for (const n of ["uSize", "uDpr", "uTime", "uSwirl", "uDialSoft", "uWave", "uAmp", "uOrb", "uBox", "uBoxR", "uHalo", "uDial", "uCalm"]) {
      this.loc[n] = gl.getUniformLocation(prog, n);
    }
    gl.bindVertexArray(gl.createVertexArray());
  }

  /** Fraction of the full resolution to render at; lowered on a device that can't keep up (see Scene.tsx). */
  private quality = 1;

  setQuality(q: number) {
    if (q === this.quality) return;
    this.quality = q;
    this.resize(this.w, this.h);
  }

  resize(w: number, h: number) {
    this.w = w; this.h = h;
    this.dpr = Math.min(devicePixelRatio || 1, this.maxDpr) * this.quality;
    const cw = Math.round(w * this.dpr), ch = Math.round(h * this.dpr);
    // Assigning a canvas's size wipes it, even to the same value, which shows as a blank frame: only on a real change.
    if (this.canvas.width !== cw) this.canvas.width = cw;
    if (this.canvas.height !== ch) this.canvas.height = ch;
  }

  draw(f: Frame) {
    const { gl, loc } = this;
    gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    gl.uniform2f(loc.uSize, this.w, this.h);
    gl.uniform1f(loc.uDpr, this.canvas.width / this.w);
    gl.uniform1f(loc.uTime, f.time);
    gl.uniform1f(loc.uSwirl, f.swirl);
    gl.uniform1f(loc.uDialSoft, f.dialSoft);
    gl.uniform4fv(loc.uWave, f.waves);
    gl.uniform1fv(loc.uAmp, f.amps);
    gl.uniform4fv(loc.uOrb, f.orb);
    gl.uniform4f(loc.uBox, f.box[0], f.box[1], f.box[2], f.box[3]);
    gl.uniform1f(loc.uBoxR, f.box[4]);
    gl.uniform4fv(loc.uHalo, f.halo);
    gl.uniform4fv(loc.uDial, f.dial);
    gl.uniform4fv(loc.uCalm, f.calm);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }

  // The context itself is left to the canvas: React's strict mode remounts on the same canvas, and a context that
  // was explicitly lost can't be had back.
  dispose() {
    this.gl.deleteProgram(this.prog);
  }
}
