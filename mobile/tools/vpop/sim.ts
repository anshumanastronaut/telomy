// Telomy virtual population — synthetic people with KNOWN truth, worn through models of every device, scored by the
// real app engines (lib/sleepfuse.ts, lib/wellness-core.ts). Synthetic data only: never shown as a user's data, never
// stored in a Vault. Purpose: find where the engines break (devices, ages, conditions, failure modes) before users do.
//
// Truth generator
//   Person: age 18–80, sex, fitness → resting HR, baseline RMSSD (age-declining, Nunan 2010 / Shaffer 2017 norms),
//   chronotype (bedtime ~ N(23:30, 60 min)), sleep need 7–9 h, conditions (insomnia, sleep apnoea, shift work).
//   Night: 30-s Markov hypnogram with time-of-night drift (deep early, REM late; AASM adult norms, deep ↓ with age),
//   onset latency, awakenings; HR / RMSSD / motion per epoch by stage (Trinder 2001 stage effects on HR/HRV).
// Device models (errors measured on real data, 2026-10-18 night; see docs/research/SLEEP_TRACKING.md)
//   patch  ECG beats → stages via the stager's EXTERNAL confusion (slpdb, κ≈0.36), may stop early, gaps
//   ring   5-min flash log HR (σ 5 bpm, per-person bias), HRV, BLE gaps; optional legacy clock bug (local as UTC)
//   watch  Apple Watch staged segments (published 4-stage confusion, κ≈0.53, Schyvens 2025)
//   phone  CoreMotion: still in bed, walking at get-up
import { fuseNights, healthNights, sleepNeed, sleepRegularity } from '../../src/lib/sleepfuse';
import { recoveryScore, sleepScore, type Night } from '../../src/lib/wellness-core';
import type { HealthSleepSegment, PhoneActivity, RingHistorySample } from '../../modules/ky-ecg';

// ------------------------------------------------------------------ rng
let seed = 1;
export const setSeed = (s: number) => { seed = s >>> 0 || 1; };
const rnd = () => { seed ^= seed << 13; seed >>>= 0; seed ^= seed >>> 17; seed ^= seed << 5; seed >>>= 0; return seed / 4294967296; };
const gauss = (m = 0, s = 1) => m + s * Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
const pick = <T,>(xs: T[], w: number[]) => { let r = rnd() * w.reduce((a, b) => a + b, 0); for (let i = 0; i < xs.length; i++) { r -= w[i]; if (r <= 0) return xs[i]; } return xs[xs.length - 1]; };
const clamp = (x: number, a: number, b: number) => Math.max(a, Math.min(b, x));

// ------------------------------------------------------------------ people
export type Devices = { patch: boolean; ring: boolean; watch: boolean; phone: boolean };
export type Person = {
  id: number; age: number; sex: 'f' | 'm'; rhr: number; rmssd: number; bedtime: number; needH: number;
  insomnia: boolean; apnea: boolean; shift: boolean; devices: Devices; ringBias: number; patchStopP: number;
};
const DEVICE_MIXES: [Devices, number][] = [
  [{ patch: false, ring: true, watch: false, phone: true }, 30], [{ patch: true, ring: true, watch: false, phone: true }, 20],
  [{ patch: false, ring: false, watch: true, phone: true }, 20], [{ patch: false, ring: true, watch: true, phone: true }, 15],
  [{ patch: true, ring: false, watch: false, phone: true }, 10], [{ patch: false, ring: false, watch: false, phone: true }, 5],
];
export function makePerson(id: number): Person {
  const age = Math.round(clamp(gauss(42, 15), 18, 80));
  const fit = gauss(0, 1);
  return {
    id, age, sex: rnd() < 0.5 ? 'f' : 'm',
    rhr: clamp(64 - 4 * fit + gauss(0, 4), 42, 85),
    rmssd: clamp(Math.exp(Math.log(55) - 0.018 * (age - 25) + 0.15 * fit + gauss(0, 0.25)), 10, 120),
    bedtime: gauss(23.5, 1.0), needH: clamp(gauss(8, 0.45), 7, 9),
    insomnia: rnd() < 0.1, apnea: rnd() < (age > 50 ? 0.15 : 0.05), shift: rnd() < 0.05,
    devices: pick(DEVICE_MIXES.map((d) => d[0]), DEVICE_MIXES.map((d) => d[1])),
    ringBias: gauss(0, 3), patchStopP: 0.15,
  };
}

// ------------------------------------------------------------------ truth night
export type TruthNight = { start: number; stages: number[]; hr: number[]; rmssd: number[]; move: number[]; tstMin: number; deepMin: number; remMin: number };
// stage codes: 0 wake, 1 light, 2 deep, 3 REM
export function truthNight(p: Person, dayStart: number): TruthNight {
  const bed = dayStart + ((p.shift ? p.bedtime + 8 : p.bedtime) + gauss(0, p.insomnia ? 1 : 0.5)) * 3600;
  const latency = Math.max(2, p.insomnia ? gauss(40, 20) : gauss(12, 8));
  const asleepH = clamp(gauss(p.needH - 0.6 - (p.insomnia ? 1 : 0), 0.9), 3, 10.5);
  const n = Math.round((latency + asleepH * 60 * 1.06) * 2);
  const deepBase = clamp(0.2 - 0.0025 * (p.age - 25), 0.04, 0.22);
  const st: number[] = [];
  let s = 0;
  for (let i = 0; i < n; i++) {
    const tMin = i / 2;
    if (tMin < latency) { st.push(0); continue; }
    const f = (tMin - latency) / (asleepH * 60);                       // 0 → 1 across the sleep period
    const cyc = ((tMin - latency) % 95) / 95;                           // ~95-min ultradian cycle
    const wakeP = 0.004 + (p.insomnia ? 0.006 : 0) + (p.apnea ? 0.01 : 0) + (f > 0.9 ? 0.01 : 0);
    if (s === 0 && tMin >= latency + 1 && rnd() < 0.35) s = 1;
    else if (s !== 0 && rnd() < wakeP) s = 0;
    else if (s !== 0) {
      const deepW = deepBase * 4 * Math.max(0, 1 - 1.6 * f) * (cyc < 0.45 ? 1.5 : 0.3);
      const remW = (0.06 + 0.32 * f) * (cyc > 0.65 ? 2.5 : 0.15) * (tMin - latency > 60 ? 1 : 0);
      if (rnd() < 0.08) s = pick([1, 2, 3], [1, deepW * 2, remW * 2]);
    }
    st.push(s);
  }
  // final wake
  for (let i = 0; i < 10; i++) st.push(0);
  const hr: number[] = [], rm: number[] = [], mv: number[] = [];
  let ar = 0;
  for (let i = 0; i < st.length; i++) {
    ar = 0.9 * ar + gauss(0, 1.2);
    const circ = -3 * Math.sin(Math.PI * clamp(i / st.length, 0, 1));
    const off = [8, 0, -3, 3][st[i]] + (p.apnea && st[i] > 0 && rnd() < 0.1 ? 8 : 0);
    hr.push(p.rhr - 4 + off + circ + ar);
    rm.push(p.rmssd * [0.7, 1.0, 1.35, 0.75][st[i]] * Math.exp(gauss(0, 0.15)));
    mv.push(st[i] === 0 ? (rnd() < 0.6 ? 0.3 + rnd() : 0.02) : st[i] === 3 ? 0.005 : rnd() < 0.03 ? 0.25 : 0.01);
  }
  const tst = st.filter((x) => x > 0).length / 2;
  return { start: bed, stages: st, hr, rmssd: rm, move: mv, tstMin: tst, deepMin: st.filter((x) => x === 2).length / 2, remMin: st.filter((x) => x === 3).length / 2 };
}

// ------------------------------------------------------------------ device models
const PATCH_CONF = [[0.6, 0.3, 0.02, 0.08], [0.1, 0.65, 0.12, 0.13], [0.03, 0.45, 0.5, 0.02], [0.1, 0.4, 0.02, 0.48]];
const WATCH_CONF = [[0.65, 0.27, 0.02, 0.06], [0.07, 0.7, 0.12, 0.11], [0.02, 0.38, 0.58, 0.02], [0.05, 0.3, 0.02, 0.63]];
const confuse = (s: number, M: number[][]) => pick([0, 1, 2, 3], M[s]);

export function patchNight(p: Person, t: TruthNight): Night | null {
  let n = t.stages.length;
  let stopped = false;
  if (rnd() < p.patchStopP) { n = Math.round(n * (0.35 + 0.4 * rnd())); stopped = true; }  // session ended early
  const stages = t.stages.slice(0, n).map((s) => (rnd() < 0.03 ? -1 : confuse(s, PATCH_CONF)));
  const asleep = stages.filter((s) => s > 0).length / 2;
  if (asleep < 30) return null;
  const known = stages.filter((s) => s >= 0).length / 2;
  const first = stages.findIndex((s) => s > 0), last = stages.length - 1 - [...stages].reverse().findIndex((s) => s > 0);
  const hrs = t.hr.slice(first, last);
  let lo = Infinity, at = 0;
  for (let i = 0; i + 10 < hrs.length; i += 10) { const m = hrs.slice(i, i + 10).reduce((a, b) => a + b, 0) / 10; if (m < lo) { lo = m; at = i; } }
  return {
    id: `p${p.id}-${t.start}`, date: '', start: t.start, end: t.start + n * 30, tstMin: asleep, efficiency: asleep / Math.max(1, known),
    onsetMin: first / 2, wasoMin: stages.slice(first, last).filter((s) => s === 0).length / 2, awakenings: 0,
    sleepRmssd: t.rmssd.slice(first, last).reduce((a, b) => a + b, 0) / Math.max(1, last - first), lowestHr: lo,
    lowestHrAt: t.start + (first + at) * 30, hrvSrc: 'ecg', hypnogram: stages.map((s) => (s > 0 ? 1 : 0)), epochSec: 30,
    hr5: [], hrv5: [], events: stopped ? [{ type: 'stopped_early', start: 0, end: 0 }] : [], midpoint: t.start + ((first + last) / 2) * 30,
    stages, deepMin: stages.filter((s) => s === 2).length / 2, remMin: stages.filter((s) => s === 3).length / 2,
    lightMin: stages.filter((s) => s === 1).length / 2,
  };
}

/** Ring 5-min log for a whole day around the night (day HR higher, BLE gaps), optional legacy clock bug. */
export function ringSamples(p: Person, t: TruthNight, dayStart: number, legacyClockBug = false): RingHistorySample[] {
  const out: RingHistorySample[] = [];
  const end = t.start + t.stages.length * 30;
  for (let ts = dayStart + 8 * 3600; ts < dayStart + 34 * 3600; ts += 300) {
    if (rnd() < 0.08) continue;                                    // BLE / measurement gaps
    const i = Math.floor((ts - t.start) / 30);
    const inNight = ts >= t.start && ts < end;
    const hrTrue = inNight ? t.hr[i] : p.rhr + 14 + gauss(0, 6) + (rnd() < 0.05 ? 40 : 0);
    const s: RingHistorySample = { t: (ts + (legacyClockBug ? 19800 : 0)) * 1000, hr: Math.round(hrTrue + p.ringBias + gauss(0, 5)) };
    if (rnd() < 0.5) s.hrv = Math.round((inNight ? t.rmssd[i] : p.rmssd * 0.6) * 1.2 * Math.exp(gauss(0, 0.25)));
    out.push(s);
  }
  return out;
}

export function watchSegments(t: TruthNight): HealthSleepSegment[] {
  const segs: HealthSleepSegment[] = [];
  let cur = -1, s0 = 0;
  const code = (s: number) => (s === 0 ? 0 : s) as 0 | 1 | 2 | 3;
  t.stages.forEach((s, i) => {
    const w = code(confuse(s, WATCH_CONF));
    if (w !== cur) { if (cur >= 0) segs.push({ start: t.start + s0 * 30, end: t.start + i * 30, stage: cur as any, source: 'Watch', watch: true }); cur = w; s0 = i; }
  });
  segs.push({ start: t.start + s0 * 30, end: t.start + t.stages.length * 30, stage: cur as any, source: 'Watch', watch: true });
  return segs;
}

export function phoneMotion(t: TruthNight): PhoneActivity[] {
  const end = t.start + t.stages.length * 30;
  return [{ type: 'walking', start: t.start - 1200, end: t.start - 300, confidence: 2 }, { type: 'still', start: t.start - 300, end, confidence: 2 },
    { type: 'walking', start: end + 300, end: end + 900, confidence: 2 }];
}

// ------------------------------------------------------------------ run one person through the engines
export type NightResult = {
  person: number; age: number; devices: string; insomnia: boolean; apnea: boolean; shift: boolean; legacyBug: boolean;
  trueTst: number; estTst: number | null; trueDeep: number; estDeep: number | null; trueRem: number; estRem: number | null;
  fragments: number; onsetErrMin: number | null; offsetErrMin: number | null; source: string | null;
  sleepScore: number | null; recovery: number | null; trueHrvZ: number; patchStopped: boolean;
};

export function runPerson(p: Person, nights = 14, legacyBug = false) {
  const base = Math.floor(Date.UTC(2026, 8, 1) / 1000) - 19800;     // 2026-09-01 00:00 IST
  const res: NightResult[] = [];
  const allPatch: Night[] = [], segs: HealthSleepSegment[] = [], ring: RingHistorySample[] = [], phone: PhoneActivity[] = [];
  const truths: TruthNight[] = [];
  for (let d = 0; d < nights; d++) {
    const day = base + d * 86400;
    const t = truthNight(p, day);
    truths.push(t);
    if (p.devices.patch && rnd() < 0.85) { const pn = patchNight(p, t); if (pn) allPatch.push(pn); }
    if (p.devices.watch && rnd() < 0.9) segs.push(...watchSegments(t));
    if (p.devices.ring && rnd() < 0.92) ring.push(...ringSamples(p, t, day, legacyBug));
    if (p.devices.phone) phone.push(...phoneMotion(t));
  }
  const realNow = Date.now;
  Date.now = () => (base + nights * 86400 + 12 * 3600) * 1000;
  let fused: Night[] = [];
  try { fused = fuseNights(allPatch, healthNights(segs), ring.sort((a, b) => a.t - b.t), phone); }
  finally { Date.now = realNow; }
  const lnBase = Math.log(p.rmssd);
  for (const t of truths) {
    const tEnd = t.start + t.stages.length * 30;
    const firstSleep = t.start + t.stages.findIndex((s) => s > 0) * 30;
    const lastSleep = t.start + (t.stages.length - 1 - [...t.stages].reverse().findIndex((s) => s > 0)) * 30;
    const hits = fused.filter((n) => n.end > t.start - 3600 && n.start < tEnd + 3600);
    const est = hits.sort((a, b) => b.tstMin - a.tstMin)[0];
    const sl = est ? sleepScore(est, fused) : null;
    const rec = est ? recoveryScore(est, fused, sl, []) : null;
    const meanRm = t.rmssd.filter((_, i) => t.stages[i] > 0).reduce((a, b) => a + b, 0) / Math.max(1, t.stages.filter((s) => s > 0).length);
    res.push({
      person: p.id, age: p.age, devices: Object.entries(p.devices).filter(([, v]) => v).map(([k]) => k).join('+'),
      insomnia: p.insomnia, apnea: p.apnea, shift: p.shift, legacyBug,
      trueTst: t.tstMin, estTst: est ? hits.reduce((a, n) => a + n.tstMin, 0) : null,
      trueDeep: t.deepMin, estDeep: est?.deepMin ?? null, trueRem: t.remMin, estRem: est?.remMin ?? null,
      fragments: hits.length, onsetErrMin: est ? (est.start + (est.onsetMin ?? 0) * 60 - firstSleep) / 60 : null,
      offsetErrMin: est ? (est.end - lastSleep) / 60 : null, source: est?.sourceName ?? est?.source ?? null,
      sleepScore: sl?.score ?? null, recovery: rec?.score ?? null, trueHrvZ: (Math.log(meanRm) - lnBase) / 0.15,
      patchStopped: allPatch.some((n) => n.start === t.start && n.events.some((e) => e.type === 'stopped_early')),
    });
  }
  return { res, need: sleepNeed(fused, 10), sri: sleepRegularity(fused) };
}
