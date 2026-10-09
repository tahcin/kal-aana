var N=Object.defineProperty;var $=(l,e,s)=>e in l?N(l,e,{enumerable:!0,configurable:!0,writable:!0,value:s}):l[e]=s;var n=(l,e,s)=>$(l,typeof e!="symbol"?e+"":e,s);import{r as b,j as x}from"./react-DI_DoK0i.js";import{u as j}from"./index-BFDiHoxD.js";import"./router-BQTWBCEV.js";import"./motion--R3qeNyJ.js";const A=16,S=16,W=`#version 300 es
void main() {
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2. - 1., 0., 1.);
}`,U=`#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2 uSize;
uniform float uDpr, uTime, uSwirl, uDialSoft;
uniform vec4 uWave[${A}];
uniform float uAmp[${A}];
uniform vec4 uOrb[${S}];
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
  for (int i = 0; i < ${A}; i++) {
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
  for (int i = 0; i < ${S}; i++) {
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
}`;class V{constructor(e,s){n(this,"gl");n(this,"prog");n(this,"loc",{});n(this,"dpr",1);n(this,"w",1);n(this,"h",1);n(this,"canvas");n(this,"maxDpr");n(this,"quality",1);this.canvas=e,this.maxDpr=s;const t=e.getContext("webgl2",{antialias:!1,alpha:!1,depth:!1,stencil:!1,powerPreference:"high-performance"});if(!t)throw new Error("webgl2 unavailable");this.gl=t;const o=(a,h)=>{const r=t.createShader(a);if(t.shaderSource(r,h),t.compileShader(r),!t.getShaderParameter(r,t.COMPILE_STATUS))throw new Error(t.getShaderInfoLog(r)??"shader");return r},i=t.createProgram();if(t.attachShader(i,o(t.VERTEX_SHADER,W)),t.attachShader(i,o(t.FRAGMENT_SHADER,U)),t.linkProgram(i),!t.getProgramParameter(i,t.LINK_STATUS))throw new Error(t.getProgramInfoLog(i)??"link");this.prog=i,t.useProgram(i);for(const a of["uSize","uDpr","uTime","uSwirl","uDialSoft","uWave","uAmp","uOrb","uBox","uBoxR","uHalo","uDial","uCalm"])this.loc[a]=t.getUniformLocation(i,a);t.bindVertexArray(t.createVertexArray())}setQuality(e){e!==this.quality&&(this.quality=e,this.resize(this.w,this.h))}resize(e,s){this.w=e,this.h=s,this.dpr=Math.min(devicePixelRatio||1,this.maxDpr)*this.quality;const t=Math.round(e*this.dpr),o=Math.round(s*this.dpr);this.canvas.width!==t&&(this.canvas.width=t),this.canvas.height!==o&&(this.canvas.height=o)}draw(e){const{gl:s,loc:t}=this;s.viewport(0,0,this.canvas.width,this.canvas.height),s.uniform2f(t.uSize,this.w,this.h),s.uniform1f(t.uDpr,this.canvas.width/this.w),s.uniform1f(t.uTime,e.time),s.uniform1f(t.uSwirl,e.swirl),s.uniform1f(t.uDialSoft,e.dialSoft),s.uniform4fv(t.uWave,e.waves),s.uniform1fv(t.uAmp,e.amps),s.uniform4fv(t.uOrb,e.orb),s.uniform4f(t.uBox,e.box[0],e.box[1],e.box[2],e.box[3]),s.uniform1f(t.uBoxR,e.box[4]),s.uniform4fv(t.uHalo,e.halo),s.uniform4fv(t.uDial,e.dial),s.uniform4fv(t.uCalm,e.calm),s.drawArrays(s.TRIANGLES,0,3)}dispose(){this.gl.deleteProgram(this.prog)}}const G=.75,z=.19,X=.5,Q=2.45,B=3,D=.42,J=2.5,K=4.4,Y={near:1.16,mid:1,far:.84},y=l=>Math.min(1,Math.max(0,l)),C=l=>l<.5?4*l*l*l:1-Math.pow(-2*l+2,3)/2,O=l=>1-Math.pow(1-l,3),F=(l,e,s)=>{const t=y((s-l)/(e-l));return t*t*(3-2*t)};class Z{constructor(e,s,t,o,i,a){n(this,"renderer");n(this,"frags",[]);n(this,"t",0);n(this,"call",null);n(this,"nextCallAt",.6);n(this,"order",0);n(this,"waves",new Float32Array(A*4));n(this,"amps",new Float32Array(A));n(this,"head",0);n(this,"orb",new Float32Array(S*4));n(this,"halo",null);n(this,"dialAngle",0);n(this,"pointer",{x:0,y:0,sx:0,sy:0});n(this,"swirlFrom",-1);n(this,"size",{w:1,h:1});n(this,"box",{x:0,y:0,w:1,h:1});n(this,"boxR",30);n(this,"calm",[0,0,1,1]);n(this,"drawn",!1);n(this,"clearRight",0);n(this,"root");n(this,"layer");n(this,"signals");n(this,"dense");n(this,"onFirstDraw");this.renderer=new V(e,i?1.5:1.25),this.root=s,this.layer=t,this.signals=o,this.dense=i,this.onFirstDraw=a}setFragments(e){this.frags=e.map((s,t)=>{const o=[...s.querySelectorAll("[data-digit]")];return{el:s,dot:s.querySelector("[data-dot]"),digits:o,values:o.map(i=>Number(i.textContent)||10),depth:s.dataset.depth??"mid",calls:s.dataset.calls==="1",seed:t*1.7+.3,ringUntil:0,off:!1}}),this.call=null,this.nextCallAt=this.t+.6,this.fit()}measure(){var o;const e=this.root.getBoundingClientRect();this.size={w:e.width,h:e.height},this.renderer.resize(e.width,e.height),this.measureBox();const t=(this.root.closest(".kh-hero")??this.root).querySelector("#hero-title");if(t){const i=t.getBoundingClientRect(),a=(o=t.nextElementSibling)==null?void 0:o.getBoundingClientRect(),h=a?a.bottom:i.bottom;this.calm=[i.left-e.left+i.width/2,(i.top+h)/2-e.top,i.width*.62,(h-i.top)*.66]}else this.calm=[e.width/2,e.height*.42,e.width*.3,e.height*.3];this.fit()}fit(){const e=this.root.getBoundingClientRect(),s=this.root.closest(".kh-hero")??this.root,t=12,o=h=>{var f;const r=(f=s.querySelector(h))==null?void 0:f.getBoundingClientRect();return r?{x:r.left-e.left,y:r.top-e.top,w:r.width,h:r.height}:null},i=o('[aria-label="Example questions"]'),a=[o("#hero-title"),o("#hero-title + p"),i,this.box].filter(h=>!!h);this.clearRight=Math.max(this.box.x+this.box.w,i?i.x+i.w:0);for(const h of this.frags){const r=h.el.getBoundingClientRect(),f=r.left-e.left,m=r.top-e.top;h.off=a.some(u=>f<u.x+u.w+t&&f+r.width>u.x-t&&m<u.y+u.h+t&&m+r.height>u.y-t),h.off?h.el.dataset.off="":delete h.el.dataset.off}}measureBox(){const e=this.root.getBoundingClientRect(),s=(this.root.closest(".kh-hero")??this.root).querySelector("[data-ask-box]");if(s){const t=s.getBoundingClientRect();this.box={x:t.left-e.left,y:t.top-e.top,w:t.width,h:t.height},this.boxR=Math.min(parseFloat(getComputedStyle(s).borderTopLeftRadius)||30,t.height/2)}else this.box={x:e.width*.25,y:e.height*.66,w:e.width*.5,h:96}}setQuality(e){this.renderer.setQuality(e)}setPointer(e,s){const t=this.root.getBoundingClientRect();this.pointer.x=y((e-t.left)/t.width)*2-1,this.pointer.y=y((s-t.top)/t.height)*2-1}tick(e){e=Math.min(e,1/20),this.t+=e;const s=this.t,t=this.pointer;if(t.sx+=(t.x-t.sx)*Math.min(1,e*2.2),t.sy+=(t.y-t.sy)*Math.min(1,e*2.2),this.signals.gust>.5){this.signals.gust=0;const r=this.frags.filter(m=>{var u;return m!==((u=this.call)==null?void 0:u.frag)&&!m.off}),f=r[Math.floor(Math.random()*r.length)];f&&this.ring(f,.55,Y[f.depth])}!this.call&&s>=this.nextCallAt&&this.startCall();const o=this.call;let i=0;if(o){const r=(s-o.dialAt)/z,f=Math.max(0,Math.min(o.frag.digits.length,Math.floor(r)+1));if(s<o.quietAt&&o.frag.digits.forEach((m,u)=>{u<f&&(m.dataset.lit="")}),r>=0&&r<o.frag.values.length){const m=Math.floor(r),u=r-m,c=u<.45?O(u/.45):1-C((u-.45)/.55);i=o.frag.values[m]*.055*c}for(;o.fired<o.rings.length&&s>=o.rings[o.fired];)this.ring(o.frag,1,1),o.fired++;s>=o.quietAt&&o.frag.el.dataset.focus!==void 0&&(delete o.frag.el.dataset.focus,o.frag.digits.forEach(m=>delete m.dataset.lit)),s>=o.nextAt&&(this.call=null,this.nextCallAt=s)}this.dialAngle+=(i-this.dialAngle)*Math.min(1,e*22),this.updateOrb(o);for(const r of this.frags)r.ringUntil&&s>r.ringUntil&&(delete r.el.dataset.ring,r.ringUntil=0);let a=0;const h=this.signals.swirl;h?(this.swirlFrom<0&&(this.swirlFrom=s,this.measure()),a=C(y((s-this.swirlFrom)/(h.ms/1e3)))):this.swirlFrom>=0&&(this.swirlFrom=-1),(this.halo||a)&&this.measureBox(),this.layer.style.opacity=String(1-a*.75),this.place(),this.draw(a)}still(){this.t=20,this.measure();const e=this.frags.find(s=>s.calls&&!s.off);if(this.amps.fill(0),this.orb.fill(0),e){e.el.dataset.focus="",e.digits.forEach(i=>i.dataset.lit="");const[s,t]=this.dotAt(e);[1.1,1.1+D,3.3,3.3+D].forEach((i,a)=>this.push(s,t,this.t-i,1,a%2?.8:1));const o=this.targetFor(s,t);this.halo={x:o[0],y:o[1],at:this.t-3,reach:0}}this.place(),this.draw(0)}dispose(){this.renderer.dispose()}startCall(){const e=this.frags.filter(r=>r.calls&&!r.off);if(!e.length)return;const s=e[this.order++%e.length];this.measure();const t=this.t,o=t+G,i=o+s.digits.length*z,a=Array.from({length:B},(r,f)=>i+X+f*Q),h=a[B-1]+1.9;s.el.dataset.focus="",this.call={frag:s,t0:t,dialAt:o,rings:a,fired:0,quietAt:h,orbAt:h-.5,nextAt:h+K,from:[0,0],path:[]}}ring(e,s,t){const[o,i]=this.dotAt(e);this.push(o,i,this.t,t,s),this.push(o,i,this.t+D,t,s*.8),e.el.dataset.ring="",e.ringUntil=this.t+1.2,e.dot.style.animation="none",e.dot.offsetWidth,e.dot.style.animation=""}push(e,s,t,o,i){const a=this.head++%A;this.waves.set([e,s,t,o],a*4),this.amps[a]=i}dotAt(e){const s=this.root.getBoundingClientRect(),t=e.dot.getBoundingClientRect();return[t.left-s.left+t.width/2,t.top-s.top+t.height/2]}targetFor(e,s){const t=this.box;return e<t.x?[t.x+6,t.y+t.h/2]:e>t.x+t.w?[t.x+t.w-6,t.y+t.h/2]:[Math.min(t.x+t.w-40,Math.max(t.x+40,e)),s<t.y?t.y+4:t.y+t.h-4]}updateOrb(e){if(this.orb.fill(0),e&&this.t>=e.orbAt&&!e.path.length){const[s,t]=this.dotAt(e.frag),[o,i]=this.targetFor(s,t),a=s<this.box.x?-1:s>this.box.x+this.box.w?1:0,h=a?0:t<this.box.y?-1:1;e.path=[[s,t],[s+(o-s)*.1,t+(i-t)*.75],[o+a*170,i+h*120],[o,i]]}if(e&&e.path.length){const s=(this.t-e.orbAt)/J;if(s>=0&&s<=1.2){const t=F(0,.18,s)*(1-F(.8,1,s)),[o,i]=T(e.path,C(y(s)));this.orb.set([o,i,t*.95,9,o,i,t*.32,40],0);for(let a=2;a<S;a++){const[h,r]=T(e.path,C(y(s-(a-1)*.008))),f=Math.pow(1-(a-2)/(S-2),1.8);this.orb.set([h,r,t*.3*f,15-a*.5],a*4)}if(s>=.9&&(!this.halo||this.halo.at<e.orbAt)){const[a,h]=e.path[3];this.halo={x:a,y:h,at:this.t,reach:0}}}}}place(){const e=this.t,s=this.pointer;for(const t of this.frags){const o=t.depth==="near"?1.7:t.depth==="mid"?1:.5,i=Math.sin(e*.13+t.seed*5)*5*o-s.sx*12*o,a=Math.cos(e*.1+t.seed*3)*4*o-s.sy*8*o;t.el.style.transform=`translate3d(${i.toFixed(2)}px, ${a.toFixed(2)}px, 0)`}}draw(e){const{w:s,h:t}=this.size,o=this.box,i=this.t;let a=[0,0,0,0];if(this.halo){const c=i-this.halo.at,p=F(0,.6,c)*Math.exp(-Math.max(0,c-1.4)*.55);a=[this.halo.x,this.halo.y,p,30+(o.w*1.3+o.h)*O(y(c/2.2))],p<.002&&c>2&&(this.halo=null)}const h=e?this.amps.map(c=>c*(1-e)):this.amps,r=this.dense?t*.5:Math.min(s*.46,t*.26),[f,m]=this.dense?[Math.max(s+r*.34,this.clearRight+36+r),t*.56]:[s+r*.06,t+r*.2],u={time:i,waves:this.waves,amps:h,orb:this.orb,swirl:e,box:[o.x+o.w/2,o.y+o.h/2,o.w/2,o.h/2,this.boxR],halo:a,dial:[f-this.pointer.sx*14,m-this.pointer.sy*10,r,this.dialAngle],dialSoft:this.dense?.034:.04,calm:this.calm};this.renderer.draw(u),this.drawn||(this.drawn=!0,requestAnimationFrame(this.onFirstDraw))}}function T(l,e){const s=1-e,t=s*s*s,o=3*s*s*e,i=3*s*e*e,a=e*e*e;return[t*l[0][0]+o*l[1][0]+i*l[2][0]+a*l[3][0],t*l[0][1]+o*l[1][1]+i*l[2][1]+a*l[3][1]]}const tt={wide:[{x:.045,y:.15,side:"l",depth:"mid",calls:!0},{x:.09,y:.4,side:"l",depth:"near",calls:!0},{x:.04,y:.63,side:"l",depth:"far",calls:!0},{x:.075,y:.83,side:"l",depth:"mid",calls:!0},{x:.27,y:.05,side:"l",depth:"far",calls:!1},{x:.72,y:.055,side:"r",depth:"far",calls:!1}],narrow:[{x:.07,y:.05,side:"l",depth:"far",calls:!1},{x:.93,y:.12,side:"r",depth:"mid",calls:!1},{x:.07,y:.79,side:"l",depth:"mid",calls:!0},{x:.12,y:.89,side:"l",depth:"far",calls:!0}]};function et(l){const e=l.match(/\b(A?RTO) (.+?)(?: \((.+)\))?$/);if(!e)return l.replace(/, Bengaluru$/,"");const[,s,t,o]=e;return`${o&&!/ and /.test(o)?o:t} ${s}`}function lt({signals:l,still:e,running:s,dense:t,onReady:o}){const{data:i}=j("/api/overview"),a=b.useRef(null),h=b.useRef(null),r=b.useRef(null),f=b.useRef(null),m=tt[t?"wide":"narrow"],u=b.useMemo(()=>{if(!i)return[];const c=new Set,p=i.offices.filter(d=>/^080 /.test(d.official)&&!c.has(d.official)&&c.add(d.official)),g=p.filter(d=>d.type==="rto"),w=p.filter(d=>d.type!=="rto");return g.flatMap((d,E)=>E%3===1&&w.length?[w.shift(),d]:[d]).slice(0,m.length).map(d=>({id:d.id,name:et(d.label),number:d.official}))},[i,m.length]);return b.useEffect(()=>{if(!h.current||!a.current||!r.current)return;let c;try{c=new Z(h.current,a.current,r.current,l,t,o)}catch{return}f.current=c,c.measure();const p=new ResizeObserver(()=>{c.measure(),e&&c.still()});p.observe(a.current);const g=w=>c.setPointer(w.clientX,w.clientY);return e||addEventListener("pointermove",g,{passive:!0}),()=>{p.disconnect(),removeEventListener("pointermove",g),c.dispose(),f.current=null}},[l,t,e,o]),b.useEffect(()=>{const c=f.current;!c||!r.current||(c.setFragments([...r.current.querySelectorAll("[data-frag]")]),e&&c.still())},[u,e,t]),b.useEffect(()=>{const c=f.current;if(!c)return;if(e){c.still();return}if(!s)return;let p=0,g=performance.now(),w=16,v=1,d=0,E=-1e9,L=!1,k=0;const H=()=>{E=performance.now()};addEventListener("scroll",H,{passive:!0});const P=M=>{const R=M-g;if(g=M,p=requestAnimationFrame(P),M-E<160&&(L=!L)){k+=R;return}const _=R+k;if(k=0,R<250){w+=(R-w)*.01,d+=R;const q=w>22&&v>.6&&d>3e3,I=w<18&&v<1&&d>8e3;(q||I)&&(v=Math.round((v+(q?-.1:.1))*10)/10,c.setQuality(v),d=0)}c.tick(_/1e3)};return p=requestAnimationFrame(P),()=>{cancelAnimationFrame(p),removeEventListener("scroll",H)}},[e,s,t,u]),x.jsxs("div",{ref:a,className:"kc-scene absolute inset-0",children:[x.jsx("canvas",{ref:h,className:"absolute inset-0 size-full"}),x.jsx("div",{ref:r,className:"kc-layer absolute inset-0",children:u.map((c,p)=>{const g=m[p];let w=0;return x.jsxs("div",{"data-frag":!0,"data-depth":g.depth,"data-side":g.side,"data-calls":g.calls?"1":"0",className:"kc-frag",style:{top:`${g.y*100}%`,...g.side==="l"?{left:`${g.x*100}%`}:{right:`${(1-g.x)*100}%`},transitionDelay:`${p*90}ms`},children:[x.jsx("span",{"data-dot":!0,className:"kc-dot"}),x.jsxs("span",{className:"kc-text",children:[x.jsx("span",{className:"kc-num",children:[...c.number].map((v,d)=>v===" "?x.jsx("span",{className:"kc-gap"},d):x.jsx("span",{"data-digit":w++,children:v},d))}),x.jsx("span",{className:"kc-name",children:c.name})]})]},c.id)})})]})}export{lt as default};
