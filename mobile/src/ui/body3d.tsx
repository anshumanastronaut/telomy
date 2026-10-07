/**
 * Telomy body — an original, procedurally generated dot-matrix human ("scan" aesthetic), rendered with raw WebGL (expo-gl).
 *
 * Geometry: every 8.5 mm up the body we take the union of anatomical ellipses (head, neck, torso, shoulders, arms, hands,
 * legs, feet) and place dots on that outline, staggered row to row. Each dot carries its outward normal so the shader
 * brightens dots facing the viewer and fades the far side — the figure reads as a translucent solid. Region tags let the
 * digital twin morph the waist (fat / visceral fat) and limbs (lean mass) on the GPU.
 * No three.js: expo-gl exposes a WebGL1-style context, which three.js dropped in r163.
 */
import { ExpoWebGLRenderingContext, GLView } from 'expo-gl';
import React, { useEffect, useMemo, useRef } from 'react';
import { PanResponder, PixelRatio, View } from 'react-native';

export type Sex = 'male' | 'female';
type Ell = { cx: number; cz: number; rx: number; rz: number; region: number };
export type Anchor = { id: string; pos: [number, number, number] };
export type Projected = Record<string, { x: number; y: number; visible: boolean }>;

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
function keys(y: number, k: number[][]): number[] | null {
  if (y < k[0][0] || y > k[k.length - 1][0]) return null;
  for (let i = 0; i < k.length - 1; i++) {
    const [y0, ...a] = k[i];
    const [y1, ...b] = k[i + 1];
    if (y >= y0 && y <= y1) {
      const t = (y - y0) / (y1 - y0 || 1);
      const s = t * t * (3 - 2 * t);
      return a.map((v, j) => lerp(v, b[j], s));
    }
  }
  return null;
}
function ellipsoid(y: number, c: number[], r: number[], region: number, mirror = false): Ell[] {
  const d = (y - c[1]) / r[1];
  if (Math.abs(d) >= 1) return [];
  const f = Math.sqrt(1 - d * d);
  const e = { cx: c[0], cz: c[2], rx: r[0] * f, rz: r[2] * f, region };
  return mirror ? [e, { ...e, cx: -e.cx }] : [e];
}

function sections(y: number, sex: Sex): Ell[] {
  const F = sex === 'female';
  const out: Ell[] = [];
  // head: cranium + jaw taper, with nose, brow, chin and ears so the face reads at a glance
  out.push(...ellipsoid(y, [0, 1.63, 0.0], [F ? 0.076 : 0.081, 0.112, 0.097], 0).map((e) => ({ ...e, rx: e.rx * (y < 1.61 ? 0.8 + 0.2 * Math.max(0, (y - 1.52) / 0.09) : 1) })));
  out.push(...ellipsoid(y, [0, 1.6, 0.088], [0.013, 0.028, 0.022], 0));          // nose
  out.push(...ellipsoid(y, [0, 1.655, 0.07], [0.055, 0.016, 0.03], 0));          // brow ridge
  out.push(...ellipsoid(y, [0, 1.535, 0.06], [0.03, 0.022, 0.03], 0));           // chin
  out.push(...ellipsoid(y, [F ? 0.077 : 0.082, 1.615, -0.005], [0.012, 0.03, 0.022], 0, true)); // ears
  const nk = keys(y, [[1.43, 0.06, 0.064, -0.005], [1.5, 0.05, 0.055, 0.0], [1.545, 0.048, 0.052, 0.012]]);
  if (nk) out.push({ cx: 0, rx: nk[0], rz: nk[1], cz: nk[2], region: 0 });
  // torso — y, half-width, half-depth, z-centre (closes between the legs, slopes into the trapezius)
  const torso = F
    ? keys(y, [[0.8, 0.05, 0.05, 0], [0.86, 0.13, 0.095, -0.005], [0.95, 0.175, 0.112, -0.012], [1.03, 0.16, 0.1, -0.005], [1.12, 0.122, 0.09, 0],
        [1.2, 0.13, 0.095, 0.004], [1.3, 0.145, 0.102, 0.008], [1.38, 0.15, 0.092, 0], [1.42, 0.13, 0.08, -0.004], [1.455, 0.075, 0.062, -0.005]])
    : keys(y, [[0.8, 0.05, 0.05, 0], [0.86, 0.13, 0.095, 0], [0.95, 0.155, 0.106, -0.004], [1.05, 0.142, 0.103, 0.004], [1.14, 0.142, 0.104, 0.008],
        [1.24, 0.155, 0.108, 0.01], [1.32, 0.168, 0.112, 0.012], [1.38, 0.172, 0.1, 0.004], [1.425, 0.15, 0.085, -0.004], [1.46, 0.08, 0.064, -0.006]]);
  if (torso) out.push({ cx: 0, rx: torso[0], rz: torso[1], cz: torso[2], region: 1 });
  if (F) out.push(...ellipsoid(y, [0.06, 1.265, 0.07], [0.058, 0.055, 0.05], 1, true));
  else out.push(...ellipsoid(y, [0.07, 1.3, 0.055], [0.075, 0.05, 0.06], 1, true)); // pectorals
  out.push(...ellipsoid(y, [F ? 0.158 : 0.172, 1.39, -0.004], [0.05, 0.05, 0.052], 2, true)); // deltoids
  // arms hang slightly away from the body, elbows a touch forward
  const ua = keys(y, [[1.1, F ? 0.2 : 0.216, 0.036, 0.038, 0.0], [1.22, F ? 0.193 : 0.207, 0.042, 0.045, -0.004], [1.33, F ? 0.183 : 0.196, 0.046, 0.048, -0.004], [1.39, F ? 0.175 : 0.188, 0.044, 0.046, -0.004]]);
  if (ua) for (const s of [1, -1]) out.push({ cx: s * ua[0], cz: ua[3], rx: ua[1], rz: ua[2], region: 2 });
  const fa = keys(y, [[0.85, F ? 0.222 : 0.24, 0.024, 0.022, 0.025], [0.92, F ? 0.218 : 0.236, 0.029, 0.03, 0.022], [1.02, F ? 0.212 : 0.228, 0.036, 0.037, 0.012], [1.1, F ? 0.203 : 0.218, 0.035, 0.037, 0.004]]);
  if (fa) for (const s of [1, -1]) out.push({ cx: s * fa[0], cz: fa[3], rx: fa[1], rz: fa[2], region: 2 });
  const hd = keys(y, [[0.68, F ? 0.226 : 0.244, 0.01, 0.022, 0.035], [0.74, F ? 0.228 : 0.247, 0.016, 0.04, 0.032], [0.8, F ? 0.226 : 0.245, 0.02, 0.045, 0.03], [0.85, F ? 0.222 : 0.24, 0.022, 0.03, 0.026]]);
  if (hd) for (const s of [1, -1]) out.push({ cx: s * hd[0], cz: hd[3], rx: hd[1], rz: hd[2], region: 2 });
  // legs: inner edges meet the closing torso; knee, calf bulge, slim ankle
  const lg = keys(y, [[0.06, 0.088, 0.028, 0.032, 0.0], [0.12, 0.088, 0.033, 0.036, -0.004], [0.3, 0.09, 0.05, 0.054, -0.012], [0.4, 0.09, 0.05, 0.052, -0.006],
    [0.49, 0.091, 0.045, 0.048, 0.004], [0.55, 0.092, 0.052, 0.054, 0.004], [0.72, F ? 0.094 : 0.09, 0.07, 0.072, 0.0], [0.88, F ? 0.096 : 0.088, F ? 0.088 : 0.082, 0.088, -0.005]]);
  if (lg) for (const s of [1, -1]) out.push({ cx: s * lg[0], cz: lg[3], rx: lg[1], rz: lg[2], region: 2 });
  const ft = keys(y, [[0.0, 0.042, 0.1, 0.045], [0.04, 0.038, 0.085, 0.032], [0.075, 0.03, 0.045, 0.006]]);
  if (ft) for (const s of [1, -1]) out.push({ cx: s * 0.09, cz: ft[2], rx: ft[0], rz: ft[1], region: 2 });
  return out;
}

const inside = (x: number, z: number, e: Ell) => ((x - e.cx) / e.rx) ** 2 + ((z - e.cz) / e.rz) ** 2 < 0.985;

/** Interleaved [x, y, z, nx, nz, region] per dot. */
export function buildBody(sex: Sex, dy = 0.0085, ds = 0.0085): Float32Array {
  const out: number[] = [];
  let row = 0;
  for (let y = 0; y <= 1.745; y += dy, row++) {
    const els = sections(y, sex);
    for (let i = 0; i < els.length; i++) {
      const e = els[i];
      const circ = Math.PI * (3 * (e.rx + e.rz) - Math.sqrt((3 * e.rx + e.rz) * (e.rx + 3 * e.rz)));
      const n = Math.max(6, Math.round(circ / ds));
      const off = (row % 2) * 0.5;
      for (let k = 0; k < n; k++) {
        const a = ((k + off) / n) * Math.PI * 2;
        const x = e.cx + e.rx * Math.cos(a), z = e.cz + e.rz * Math.sin(a);
        let covered = false;
        for (let j = 0; j < els.length && !covered; j++) if (j !== i && inside(x, z, els[j])) covered = true;
        if (covered) continue;
        const nx = Math.cos(a) / e.rx, nz = Math.sin(a) / e.rz, l = Math.hypot(nx, nz);
        out.push(x, y, z, nx / l, nz / l, e.region);
      }
    }
  }
  return new Float32Array(out);
}

// ------------------------------------------------------------------ shaders (GLSL ES 1.0)
const VERT = `
precision highp float;
attribute vec3 aPos; attribute vec2 aNor; attribute float aRegion;
uniform float uYaw; uniform float uWaist; uniform float uLimb; uniform float uBreath; uniform float uSize;
uniform vec2 uAspect; uniform float uCamZ; uniform float uFocal; uniform float uLift;
varying float vFacing; varying float vY;
void main() {
  vec3 p = aPos;
  float torso = step(0.5, aRegion) * step(aRegion, 1.5);
  float belly = exp(-pow((p.y - 1.06) / 0.11, 2.0)) * torso;
  float limb = step(1.5, aRegion) * (uLimb - 1.0);
  float chest = exp(-pow((p.y - 1.28) / 0.09, 2.0)) * torso * uBreath;
  if (aRegion > 1.5) {
    float cx = sign(p.x) * min(abs(p.x), 0.2);
    p.x = cx + (p.x - cx) * (1.0 + limb); p.z *= 1.0 + limb;
  } else {
    p.x *= 1.0 + (uWaist - 1.0) * belly;
    p.z = p.z * (1.0 + (uWaist - 1.0) * belly * 1.35) + chest * 0.006;
  }
  float c = cos(uYaw), s = sin(uYaw);
  vec3 r = vec3(c * p.x + s * p.z, p.y - uLift, -s * p.x + c * p.z);
  vec2 n = vec2(c * aNor.x + s * aNor.y, -s * aNor.x + c * aNor.y);
  vFacing = n.y;
  vY = aPos.y;
  float depth = uCamZ - r.z;
  gl_Position = vec4(r.x * uFocal / uAspect.x, r.y * uFocal / uAspect.y, 0.0, depth);
  gl_PointSize = uSize * (uCamZ / depth);
}`;
const FRAG = `
precision mediump float;
uniform vec3 uColor; uniform vec3 uDeep; uniform float uFade;
varying float vFacing; varying float vY;
void main() {
  vec2 q = gl_PointCoord - 0.5;
  if (dot(q, q) > 0.25) discard;
  float face = smoothstep(-0.35, 0.9, vFacing);
  float legFade = mix(1.0 - uFade, 1.0, smoothstep(0.05, 0.8, vY));
  gl_FragColor = vec4(mix(uDeep, uColor, face), (0.10 + 0.90 * face) * legFade);
}`;
const LVERT = `
precision highp float;
attribute vec3 aPos;
uniform float uYaw; uniform vec2 uAspect; uniform float uCamZ; uniform float uFocal; uniform float uLift; uniform float uScale; uniform float uPt;
varying float vFacing;
void main() {
  vec3 p = vec3(aPos.x * uScale, aPos.y, aPos.z * uScale);
  float c = cos(uYaw), s = sin(uYaw);
  vec3 r = vec3(c * p.x + s * p.z, p.y - uLift, -s * p.x + c * p.z);
  vFacing = r.z;
  gl_Position = vec4(r.x * uFocal / uAspect.x, r.y * uFocal / uAspect.y, 0.0, uCamZ - r.z);
  gl_PointSize = uPt;
}`;
const LFRAG = `
precision mediump float;
uniform vec4 uColor; varying float vFacing;
void main() { gl_FragColor = vec4(uColor.rgb, uColor.a * (vFacing > -0.02 ? 1.0 : 0.25)); }`;

const hex = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);

function program(gl: ExpoWebGLRenderingContext, vs: string, fs: string) {
  const mk = (type: number, src: string) => {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) || 'shader');
    return s;
  };
  const p = gl.createProgram()!;
  gl.attachShader(p, mk(gl.VERTEX_SHADER, vs));
  gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) || 'link');
  return p;
}

const RINGS = (F: boolean) => [
  { x: F ? 0.197 : 0.21, y: 1.21, rx: 0.068, rz: 0.06, waist: false },
  { x: -(F ? 0.197 : 0.21), y: 1.21, rx: 0.068, rz: 0.06, waist: false },
  { x: 0, y: 1.08, rx: F ? 0.17 : 0.178, rz: 0.13, waist: true },
];

export const CAM = { z: 2.45, fov: 32, lift: 0.86 };

/** Project a body-space point to screen pixels with the same camera as the shader. */
export function project(pos: number[], yaw: number, w: number, h: number) {
  const f = 1 / Math.tan((CAM.fov * Math.PI) / 360);
  const c = Math.cos(yaw), s = Math.sin(yaw);
  const x = c * pos[0] + s * pos[2], y = pos[1] - CAM.lift, z = -s * pos[0] + c * pos[2];
  const d = CAM.z - z;
  const asp = w / h;
  const ndcX = (x * f) / (asp >= 1 ? asp : 1) / d, ndcY = (y * f) / (asp >= 1 ? 1 : 1 / asp) / d;
  return { x: (ndcX * 0.5 + 0.5) * w, y: (-ndcY * 0.5 + 0.5) * h, visible: z >= -0.02 };
}

export function BodyScene({ sex = 'male', waist = 1, limb = 1, anchors, onProject, height = 520, rings = true, color = '#2BB3E3' }: {
  sex?: Sex; waist?: number; limb?: number; anchors: Anchor[]; onProject: (p: Projected) => void; height?: number; rings?: boolean; color?: string;
}) {
  const data = useMemo(() => buildBody(sex), [sex]);
  const yaw = useRef(0.2);
  const target = useRef({ waist, limb });
  const live = useRef({ waist: 1, limb: 1 });
  const dragging = useRef<{ on: boolean; start: number }>({ on: false, start: 0 });
  const size = useRef({ w: 1, h: height });
  const raf = useRef<number | null>(null);
  const anchorsRef = useRef(anchors);
  anchorsRef.current = anchors;
  const projRef = useRef(onProject);
  projRef.current = onProject;
  useEffect(() => { target.current = { waist, limb }; }, [waist, limb]);
  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current); }, []);

  const pan = useMemo(() => PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (_e, g) => Math.abs(g.dx) > 4 && Math.abs(g.dx) > Math.abs(g.dy),
    onPanResponderGrant: () => { dragging.current = { on: true, start: yaw.current }; },
    onPanResponderMove: (_e, g) => { yaw.current = dragging.current.start + g.dx / 90; },
    onPanResponderRelease: () => { dragging.current.on = false; },
    onPanResponderTerminate: () => { dragging.current.on = false; },
  }), []);

  function onContext(gl: ExpoWebGLRenderingContext) {
    const W = gl.drawingBufferWidth, H = gl.drawingBufferHeight;
    const pr = PixelRatio.get();
    const prog = program(gl, VERT, FRAG);
    const lprog = program(gl, LVERT, LFRAG);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const n = data.length / 6;
    const ringData = RINGS(sex === 'female').map((r) => {
      const pts: number[] = [];
      for (let i = 0; i < 720; i++) {
        const a = (i / 720) * Math.PI * 2;
        pts.push(r.x + r.rx * Math.cos(a), r.y, r.rz * Math.sin(a));
      }
      const b = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, b);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pts), gl.STATIC_DRAW);
      return { b, waist: r.waist };
    });
    const U = (p: WebGLProgram, k: string) => gl.getUniformLocation(p, k);
    const f = 1 / Math.tan((CAM.fov * Math.PI) / 360);
    const asp = W / H;
    const aspect = asp >= 1 ? [asp, 1] : [1, 1 / asp];
    const col = hex(color);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.disable(gl.DEPTH_TEST);
    let t0 = Date.now(), lastProj = 0;

    const frame = () => {
      const now = Date.now();
      const t = (now - t0) / 1000;
      const dt = 1 / 60;
      if (!dragging.current.on) {
        const goal = 0.22 * Math.sin(t * 0.22);
        const wrapped = Math.atan2(Math.sin(yaw.current), Math.cos(yaw.current));
        yaw.current = wrapped + (goal - wrapped) * dt * 0.8;
      }
      live.current.waist += (target.current.waist - live.current.waist) * dt * 3;
      live.current.limb += (target.current.limb - live.current.limb) * dt * 3;
      gl.viewport(0, 0, W, H);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      // dots
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      const aPos = gl.getAttribLocation(prog, 'aPos'), aNor = gl.getAttribLocation(prog, 'aNor'), aReg = gl.getAttribLocation(prog, 'aRegion');
      gl.enableVertexAttribArray(aPos);
      gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 24, 0);
      gl.enableVertexAttribArray(aNor);
      gl.vertexAttribPointer(aNor, 2, gl.FLOAT, false, 24, 12);
      gl.enableVertexAttribArray(aReg);
      gl.vertexAttribPointer(aReg, 1, gl.FLOAT, false, 24, 20);
      gl.uniform1f(U(prog, 'uYaw'), yaw.current);
      gl.uniform1f(U(prog, 'uWaist'), live.current.waist);
      gl.uniform1f(U(prog, 'uLimb'), live.current.limb);
      gl.uniform1f(U(prog, 'uBreath'), Math.sin(t * 1.6));
      gl.uniform1f(U(prog, 'uSize'), 1.45 * pr);
      gl.uniform2f(U(prog, 'uAspect'), aspect[0], aspect[1]);
      gl.uniform1f(U(prog, 'uCamZ'), CAM.z);
      gl.uniform1f(U(prog, 'uFocal'), f);
      gl.uniform1f(U(prog, 'uLift'), CAM.lift);
      gl.uniform3f(U(prog, 'uColor'), col[0], col[1], col[2]);
      gl.uniform3f(U(prog, 'uDeep'), 0.78, 0.9, 0.96);
      gl.uniform1f(U(prog, 'uFade'), 0.8);
      gl.drawArrays(gl.POINTS, 0, n);
      gl.disableVertexAttribArray(aNor);
      gl.disableVertexAttribArray(aReg);
      // measurement rings
      if (rings) {
        gl.useProgram(lprog);
        const lp = gl.getAttribLocation(lprog, 'aPos');
        gl.uniform1f(U(lprog, 'uYaw'), yaw.current);
        gl.uniform2f(U(lprog, 'uAspect'), aspect[0], aspect[1]);
        gl.uniform1f(U(lprog, 'uCamZ'), CAM.z);
        gl.uniform1f(U(lprog, 'uFocal'), f);
        gl.uniform1f(U(lprog, 'uLift'), CAM.lift);
        ringData.forEach((r, i) => {
          gl.bindBuffer(gl.ARRAY_BUFFER, r.b);
          gl.enableVertexAttribArray(lp);
          gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 12, 0);
          gl.uniform1f(U(lprog, 'uScale'), r.waist ? live.current.waist : live.current.limb);
          gl.uniform4f(U(lprog, 'uColor'), 0.07, 0.52, 0.74, 0.55 + 0.4 * Math.sin(t * 1.4 + i) ** 2);
          gl.uniform1f(U(lprog, 'uPt'), 1.6 * pr);
          gl.drawArrays(gl.POINTS, 0, 720);
        });
      }
      gl.flush();
      gl.endFrameEXP();
      if (now - lastProj > 80) {
        lastProj = now;
        const out: Projected = {};
        for (const a of anchorsRef.current) out[a.id] = project(a.pos, yaw.current, size.current.w, size.current.h);
        projRef.current(out);
      }
      raf.current = requestAnimationFrame(frame);
    };
    frame();
  }

  return (
    <View style={{ height }} {...pan.panHandlers} onLayout={(e) => { size.current = { w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height }; }}>
      <GLView key={sex} style={{ flex: 1 }} onContextCreate={onContext} msaaSamples={4} />
    </View>
  );
}

export const pixelRatio = PixelRatio.get();
