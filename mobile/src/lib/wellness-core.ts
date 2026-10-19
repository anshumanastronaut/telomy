// Telomy wellness maths — pure functions, no React / native imports, so the engines run anywhere
// (the app, tests, and the virtual-population simulator in tools/vpop). The React hook lives in wellness.ts.
import type { CaptureMeta } from '../../modules/ky-ecg';
import type { SleepNeed, SleepSource } from './sleepfuse';


// ------------------------------------------------------------------ types

export type Night = {
  id: string; date: string; start: number; end: number;
  tstMin: number; efficiency: number; onsetMin?: number; wasoMin: number; awakenings: number;
  sleepHr?: number; sleepRmssd?: number; lateRmssd?: number; lowestHr?: number; lowestHrAt?: number; lowestHrPos?: number;
  hrDropPct?: number; respRate?: number; respRateUncalibrated?: number; hypnogram: number[]; epochSec: number;
  hr5: [number, number, number][]; hrv5: [number, number, number][]; events: { type: string; start: number; end: number }[];
  midpoint: number;  // unix time of the sleep midpoint
  stages?: number[];  // 4-stage model per 30-s epoch: 0 wake, 1 light, 2 deep, 3 REM, -1 no data
  lightMin?: number; deepMin?: number; remMin?: number; remLatencyMin?: number; remCycles?: number;
  source?: SleepSource; sourceName?: string;   // which device this night came from (lib/sleepfuse.ts)
  stageConfidence?: 'low';                      // 'low' = stages estimated from 5-min ring HR (not patch/watch-grade)
  hrvSrc?: 'ecg' | 'ring';
  skinTemp?: number;                          // night temperature, °C — compare only within the same tempSrc
  tempSrc?: 'ring' | 'whoop';                 // ring: coarse body estimate; WHOOP 4.0: skin, deviation-only                    // HRV scales differ by device: baselines only compare like with like
};
export type MinuteRec = { ts: string; hr: number; rmssd?: number; quality?: string; activity?: string; sleep?: string; motion?: number | null; resting?: number };
export type Contributor = { key: string; label: string; score: number | null; value: string; note: string };
export type Confidence = 'calibrating' | 'building' | 'solid';
export type Score = { score: number | null; label: string; contributors: Contributor[]; calibrating?: string; confidence?: Confidence };

// ------------------------------------------------------------------ helpers

const clamp = (x: number, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, x));
/** Piecewise-linear map through (x, y) knots (x ascending). */
export function knots(x: number, pts: [number, number][]) {
  if (x <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
    if (x <= x1) return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0);
  }
  return pts[pts.length - 1][1];
}
const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;
const sd = (a: number[]) => { const m = mean(a); return Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / Math.max(1, a.length - 1)); };
const median = (a: number[]) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : NaN; };
export const fmtDur = (min: number) => `${Math.floor(min / 60)}h ${String(Math.round(min % 60)).padStart(2, '0')}m`;
export const fmtClock = (t: number) => new Date(t * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
export const localDate = (t: number) => { const d = new Date(t * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

// ------------------------------------------------------------------ nights from captures

/** The overnight therapy id is 'sleep'; early auto-sleep builds wrote 'overnight_sleep'. */
export const isNight = (c: any) => c?.therapyId === 'sleep' || c?.therapyId === 'overnight_sleep';

export function nightsFrom(captures: CaptureMeta[]): Night[] {
  const out: Night[] = [];
  for (const c of captures as any[]) {
    const s = c.summary ?? {}, sl = s.sleep, nm = s.night ?? {};
    // a session left open (never stopped) still counts once it has been analysed — its end is the last epoch
    if (!isNight(c) || !sl || !(c.endedAt || sl.t0)) continue;
    const epoch = sl.epochSec ?? 30;
    const hyp: number[] = sl.hypnogram ?? [];
    const first = hyp.indexOf(1), last = hyp.lastIndexOf(1);
    const t0 = sl.t0 ?? c.startedAt;  // sleep epochs start with the ECG
    const end = c.endedAt ?? t0 + hyp.length * epoch;   // open session: ends at its last analysed epoch
    const mid = first >= 0 ? t0 + ((first + last + 1) / 2) * epoch : (c.startedAt + end) / 2;
    out.push({
      id: c.id, date: localDate(end), start: t0, end,
      tstMin: sl.totalSleepMin, efficiency: sl.efficiency, onsetMin: sl.onsetMin, wasoMin: sl.wasoMin, awakenings: sl.awakenings,
      sleepHr: nm.avgSleepHr ?? sl.sleepHr, sleepRmssd: nm.sleepRmssd ?? sl.sleepRmssd, lateRmssd: nm.lateRmssd,
      lowestHr: nm.lowestHr, lowestHrAt: nm.lowestHrAt, lowestHrPos: nm.lowestHrPos, hrDropPct: nm.hrDropPct,
      // ECG breathing rate withheld (2026-10-19): the two estimators lock onto a harmonic (21/min) or onto Mayer waves
      // (7/min) on real nights; it returns once calibrated against counted breaths. Kept raw for that calibration.
      respRate: undefined, respRateUncalibrated: nm.respRate,
      hypnogram: hyp, epochSec: epoch, hr5: nm.hr5 ?? [], hrv5: nm.hrv5 ?? [], events: s.events ?? [], midpoint: mid,
      stages: sl.stages, lightMin: sl.lightMin, deepMin: sl.deepMin, remMin: sl.remMin, remLatencyMin: sl.remLatencyMin, remCycles: sl.remCycles,
    });
  }
  return out.sort((a, b) => a.end - b.end);
}

// ------------------------------------------------------------------ sleep score

/**
 * 0–100 from contributors (each 0–100), weights renormalised over what is available.
 * Duration: NSF adult 7–9 h (Hirshkowitz 2015). Efficiency, latency, WASO, awakenings: NSF sleep-quality indicators
 * (Ohayon 2017: good ≥ 85 % / ≤ 15 min / ≤ 20 min / ≤ 1 long awakening). Restoration: overnight ln RMSSD vs personal
 * baseline. HR drop: nocturnal HR dipping ≥ 10 % is typical. Regularity: SD of sleep midpoint over the last 7 nights
 * (proxy for the Sleep Regularity Index, Phillips 2017).
 */
export function sleepScore(n: Night, history: Night[], needMin?: number, sri?: number | null): Score {
  const prev = history.filter((h) => h.end < n.end).slice(-30);
  const c: (Contributor & { w: number })[] = [];
  if (needMin) c.push({ key: 'duration', label: 'Sleep vs your need', w: 0.25, value: `${fmtDur(n.tstMin)} of ${fmtDur(needMin)}`, note: `${Math.round((100 * n.tstMin) / needMin)} % of what your body asked for`,
    score: knots(n.tstMin / needMin, [[0.5, 0], [0.7, 40], [0.85, 75], [0.95, 95], [1, 100], [1.35, 100], [1.5, 85]]) });
  else c.push({ key: 'duration', label: 'Total sleep', w: 0.25, value: fmtDur(n.tstMin), note: 'Adults need 7–9 h',
    score: knots(n.tstMin / 60, [[4, 0], [5, 35], [6, 65], [7, 100], [9, 100], [10, 90], [11, 75]]) });
  c.push({ key: 'efficiency', label: 'Efficiency', w: 0.12, value: `${Math.round(n.efficiency * 100)}%`, note: '85 % or more is good',
    score: knots(n.efficiency * 100, [[65, 0], [74, 25], [85, 75], [90, 100]]) });
  if (n.onsetMin != null) c.push({ key: 'latency', label: 'Time to fall asleep', w: 0.08, value: `${Math.round(n.onsetMin)} min`, note: '15 min or less is good',
    score: knots(n.onsetMin, [[15, 100], [30, 70], [45, 30], [60, 0]]) });
  c.push({ key: 'waso', label: 'Awake after falling asleep', w: 0.08, value: `${Math.round(n.wasoMin)} min`, note: '20 min or less is good',
    score: knots(n.wasoMin, [[20, 100], [35, 65], [50, 30], [80, 0]]) });
  const estW = n.stageConfidence === 'low' ? 0.04 : 0.09;   // ring HR-estimated stages count for less than the patch's
  if (n.deepMin != null && n.tstMin > 0) {
    const f = n.deepMin / n.tstMin;
    c.push({ key: 'deep', label: 'Deep sleep', w: estW, value: `${fmtDur(n.deepMin)} · ${Math.round(f * 100)}%`, note: 'Typical 13–23 % for adults (less with age)',
      score: knots(f, [[0.03, 0], [0.08, 40], [0.13, 85], [0.16, 100], [0.25, 100], [0.35, 85]]) });
  }
  if (n.remMin != null && n.tstMin > 0) {
    const f = n.remMin / n.tstMin;
    c.push({ key: 'rem', label: 'REM sleep', w: estW, value: `${fmtDur(n.remMin)} · ${Math.round(f * 100)}%`, note: 'Typical 20–25 % of sleep',
      score: knots(f, [[0.05, 0], [0.12, 45], [0.18, 85], [0.2, 100], [0.26, 100], [0.33, 80]]) });
  }
  c.push({ key: 'awakenings', label: 'Wake-ups', w: 0.04, value: `${n.awakenings}`, note: 'Brief wake-ups are normal; fewer is better',
    score: knots(n.awakenings, [[2, 100], [4, 65], [6, 30], [9, 0]]) });
  if (n.sleepRmssd) {
    const base = prev.filter((h) => (h.hrvSrc ?? 'ecg') === (n.hrvSrc ?? 'ecg')).map((h) => h.sleepRmssd).filter(Boolean).map((v) => Math.log(v!));
    const rb = robustBaseline(base, 0.05);
    if (rb && base.length >= 3) {
      const z = (Math.log(n.sleepRmssd) - rb.center) / (1.253 * rb.spread);
      c.push({ key: 'restoration', label: 'Restoration (HRV)', w: 0.13, value: `${Math.round(n.sleepRmssd)} ms`, note: 'Overnight HRV vs your normal',
        score: clamp(70 + 20 * z) });
    } else {
      c.push({ key: 'restoration', label: 'Restoration (HRV)', w: 0.13, value: `${Math.round(n.sleepRmssd)} ms`, note: `Learning your normal (${base.length}/3 nights)`, score: null });
    }
  }
  if (n.hrDropPct != null) c.push({ key: 'drop', label: 'Heart-rate drop', w: 0.08, value: `${Math.round(n.hrDropPct)}%`, note: 'A 10 % or larger drop in sleep is typical',
    score: knots(n.hrDropPct, [[0, 0], [5, 30], [10, 70], [15, 100]]) });
  const mids = [...prev.slice(-6), n].map((h) => { const d = new Date(h.midpoint * 1000); return ((d.getHours() + 12) % 24) * 60 + d.getMinutes(); });
  if (sri != null) {
    c.push({ key: 'regularity', label: 'Sleep regularity', w: 0.06, value: `SRI ${sri}`, note: 'Chance you are in the same state 24 h apart (80+ is regular)',
      score: knots(sri, [[40, 0], [60, 45], [75, 80], [85, 100]]) });
  } else if (mids.length >= 3) {
    const s = sd(mids);
    c.push({ key: 'regularity', label: 'Regular timing', w: 0.04, value: `±${Math.round(s)} min`, note: 'Same sleep timing every night helps',
      score: knots(s, [[30, 100], [60, 60], [90, 20], [120, 0]]) });
  }
  const used = c.filter((x) => x.score != null);
  const W = used.reduce((s, x) => s + x.w, 0);
  const score = W ? Math.round(used.reduce((s, x) => s + x.w * (x.score as number), 0) / W) : null;
  return { score, label: score == null ? '—' : score >= 85 ? 'Excellent' : score >= 70 ? 'Good' : score >= 55 ? 'Fair' : 'Poor',
    contributors: c.map(({ w, ...x }) => ({ ...x, score: x.score == null ? null : Math.round(x.score) })) };
}

// ------------------------------------------------------------------ recovery

/**
 * 0–100 from z-scores vs the personal baseline (previous ≤ 30 nights, needs 3):
 *  HRV: overnight ln RMSSD (Plews et al. 2013; Buchheit 2014: daily ln RMSSD vs rolling mean, SWC = 0.5 SD)  45 %
 *  Resting HR: lowest 5-min HR asleep (higher than usual = worse)                                            25 %
 *  Breathing rate: penalised only when above baseline (illness/strain signal)                                10 %
 *  Sleep score                                                                                               15 %
 *  Previous-day load: penalised when above the 7-day average                                                  5 %
 * Recovery = 100 / (1 + e^-(0.4 + 1.1 z)) → a normal day ≈ 60; green ≥ 67, amber 34–66, red ≤ 33 (WHOOP-style bands);
 * guidance words follow the same bands (≥ 80 Go for it, 67–79 Ready, 34–66 Pace yourself, ≤ 33 Recover).
 */
// ------------------------------------------------------------------ robust personal baselines

export type Baseline = { center: number; spread: number; n: number; status: 'calibrating' | 'provisional' | 'trusted' };
/**
 * Winsorised EWMA baseline (as in NOOP's Baselines, after the robust-statistics literature): centre half-life 14
 * nights, spread (mean absolute deviation) half-life 21; a value > 5 spreads away is ignored, otherwise it is folded
 * clamped to ±3 spreads so one odd night cannot drag the centre. z = (x − centre) / (1.253 · spread).
 * calibrating < 4 nights, provisional 4–13, trusted ≥ 14.
 */
export function robustBaseline(values: number[], floorSpread: number): Baseline | null {
  const v = values.filter((x) => Number.isFinite(x));
  if (!v.length) return null;
  const lc = 1 - 0.5 ** (1 / 14), ls = 1 - 0.5 ** (1 / 21);
  const seed = v.slice(0, Math.min(4, v.length));
  let c = median(seed), sp = Math.max(floorSpread, mean(seed.map((x) => Math.abs(x - c))) || floorSpread);
  for (const x of v.slice(seed.length)) {
    if (Math.abs(x - c) > 5 * 1.253 * sp) continue;
    const cl = clamp(x, c - 3 * 1.253 * sp, c + 3 * 1.253 * sp);
    c = lc * cl + (1 - lc) * c;
    sp = Math.max(floorSpread, ls * Math.abs(x - c) + (1 - ls) * sp);
  }
  return { center: c, spread: sp, n: v.length, status: v.length < 4 ? 'calibrating' : v.length < 14 ? 'provisional' : 'trusted' };
}
const zOf = (x: number, b: Baseline) => (x - b.center) / (1.253 * b.spread);

/**
 * 0–100 recovery from robust z-scores vs your own baseline (previous ≤ 30 nights from the same HRV device):
 *  HRV (overnight ln RMSSD; Plews 2013, Buchheit 2014)                                 50 %
 *  Resting HR (lowest sustained HR asleep; higher than usual = worse)                  20 %
 *  Sleep score                                                                         15 %
 *  Breathing rate (penalised only above your normal — illness/strain signal)            5 %
 *  Skin temperature (penalised by |deviation| either way — illness/overreach flag)      5 %
 *  Previous-day load (penalised above the 7-day average)                                5 %
 * Recovery = 100 / (1 + e^-(0.4 + 1.1 z)) → a normal day ≈ 60; green ≥ 67, amber 34–66, red ≤ 33.
 * Confidence: calibrating (< 4 nights, compared with typical adults), building (4–13), solid (≥ 14).
 */
export function recoveryScore(n: Night | undefined, history: Night[], sleep: Score | null, loads: number[]): Score {
  // A night with no trustworthy overnight HRV (e.g. WHOOP-only — WHOOP 4.0 R-R is re-delivered and inflated, so it is
  // not used for HRV) still gives a useful recovery from resting heart rate + sleep. Only when there is NO night, or a
  // night with neither HRV nor resting HR nor a sleep score, do we say there is nothing to read.
  if (!n) return { score: null, label: 'Wear the patch, ring or WHOOP tonight', contributors: [], confidence: 'calibrating', calibrating: 'Needs one night with a device' };
  const hasHrv = !!n.sleepRmssd;
  if (!hasHrv && !n.lowestHr && sleep?.score == null)
    return { score: null, label: 'Not enough from last night', contributors: [], confidence: 'calibrating', calibrating: 'Last night had no heart rate or sleep detail — wear the patch, ring or WHOOP to bed' };
  const prev = history.filter((h) => h.end < n.end && (h.hrvSrc ?? 'ecg') === (n.hrvSrc ?? 'ecg')).slice(-30);
  const c: (Contributor & { w: number; z: number | null })[] = [];
  const bH = hasHrv ? robustBaseline(prev.map((h) => h.sleepRmssd).filter(Boolean).map((v) => Math.log(v!)), 0.05) : null;
  const usable = bH && bH.status !== 'calibrating';
  const confidence: Confidence = !hasHrv ? 'building' : !usable ? 'calibrating' : bH!.status === 'provisional' ? 'building' : 'solid';
  const calibrating = !hasHrv ? 'Based on resting heart rate and sleep — wear the patch or ring for HRV-based recovery'
    : !usable ? `Learning your normal: night ${(bH?.n ?? 0) + 1} of 4` : undefined;
  if (hasHrv) {
    // until a baseline exists, compare with healthy-adult references (RMSSD ≈ 42 ms, ln-SD ≈ 0.35, Nunan 2010; RHR 60 ± 8)
    const zH = usable ? zOf(Math.log(n.sleepRmssd!), bH!) : (Math.log(n.sleepRmssd!) - Math.log(42)) / 0.35;
    c.push({ key: 'hrv', label: 'HRV', w: 0.5, z: zH, value: `${Math.round(n.sleepRmssd!)} ms`,
      note: usable ? `Your normal ${Math.round(Math.exp(bH!.center))} ms` : 'Compared with typical adults until your normal is learnt', score: clamp(60 + 20 * zH) });
  }
  if (n.lowestHr) {
    const b = robustBaseline(prev.map((h) => h.lowestHr).filter(Boolean) as number[], 1.5);
    const ok = b && b.status !== 'calibrating';
    const zR = ok ? -zOf(n.lowestHr, b!) : -(n.lowestHr - 60) / 8;
    c.push({ key: 'rhr', label: 'Resting heart rate', w: 0.2, z: zR, value: `${Math.round(n.lowestHr)} bpm`,
      note: ok ? `Your normal ${Math.round(b!.center)} bpm` : 'Lowest sustained heart rate asleep', score: clamp(60 + 20 * zR) });
  }
  if (n.respRate) {
    const b = robustBaseline(prev.map((h) => h.respRate).filter(Boolean) as number[], 0.5);
    const ok = b && b.status !== 'calibrating';
    const zB = ok ? -Math.max(0, zOf(n.respRate, b!)) : 0;
    c.push({ key: 'resp', label: 'Breathing rate', w: 0.05, z: zB, value: `${n.respRate.toFixed(1)} /min`,
      note: ok ? `Your normal ${b!.center.toFixed(1)} /min` : 'Learning your normal', score: clamp(70 + 20 * zB) });
  }
  if (n.skinTemp) {
    const b = robustBaseline(prev.filter((h) => h.tempSrc === n.tempSrc).map((h) => h.skinTemp).filter(Boolean) as number[], 0.2);
    if (b && b.status !== 'calibrating') {
      const d = n.skinTemp - b.center, zT = -Math.abs(d) / 0.3;
      c.push({ key: 'temp', label: 'Skin temperature', w: 0.05, z: zT, value: `${d >= 0 ? '+' : ''}${d.toFixed(1)} °C`,
        note: 'Change from your normal; a big shift either way can mean illness or overreaching', score: clamp(70 + 20 * zT) });
    }
  }
  if (sleep?.score != null) {
    const zS = (sleep.score - 70) / 15;
    c.push({ key: 'sleep', label: 'Sleep', w: 0.15, z: zS, value: `${sleep.score}`, note: sleep.label, score: sleep.score });
  }
  if (loads.length >= 2) {
    const y = loads[loads.length - 1], avg = mean(loads.slice(0, -1));
    const zL = -Math.max(0, (y - avg) / Math.max(10, sd(loads)));
    c.push({ key: 'load', label: 'Yesterday’s strain', w: 0.05, z: zL, value: strainFromTrimp(y).toFixed(1), note: 'Higher than usual load slows recovery', score: clamp(70 + 20 * zL) });
  }
  const W = c.reduce((s, x) => s + x.w, 0);
  const z = c.reduce((s, x) => s + x.w * (x.z ?? 0), 0) / W;
  const score = Math.round(100 / (1 + Math.exp(-(0.4 + 1.1 * z))));
  return { score, label: readiness(score), calibrating, confidence, contributors: c.map(({ w, z: _z, ...x }) => ({ ...x, score: x.score == null ? null : Math.round(x.score) })) };
}

// ------------------------------------------------------------------ illness heads-up

export type IllnessSignal = { key: string; label: string; detail: string };
/**
 * Early-illness pattern (as in NOOP's illness watch; RHR↑ + HRV↓ + skin temp↑ is the classic pre-symptom signature,
 * Mishra 2020 Nat Biomed Eng, Radin 2020 Lancet Digit Health): the last 2 nights vs a baseline of up to 28 nights
 * ending 3 nights earlier. Flags when ≥ 2 of: resting HR ≥ +5 bpm, HRV ≤ −20 %, skin temp ≥ +0.6 °C,
 * breathing ≥ +1.5 /min. Needs ≥ 14 nights. A wellness nudge, not a diagnosis.
 */
export function illnessWatch(nights: Night[]): { flagged: boolean; signals: IllnessSignal[] } | null {
  if (nights.length < 14) return null;
  const recent = nights.slice(-2), base = nights.slice(-31, -3);
  const m = (xs: (number | undefined)[]) => { const v = xs.filter((x): x is number => x != null && Number.isFinite(x)); return v.length ? mean(v) : null; };
  const out: IllnessSignal[] = [];
  const rr = m(recent.map((n) => n.lowestHr)), rb = m(base.map((n) => n.lowestHr));
  if (rr != null && rb != null && rr >= rb + 5) out.push({ key: 'rhr', label: 'Resting heart rate up', detail: `+${Math.round(rr - rb)} bpm` });
  const sameSrc = (n: Night) => (n.hrvSrc ?? 'ecg') === (recent[recent.length - 1].hrvSrc ?? 'ecg');
  const hr = m(recent.filter(sameSrc).map((n) => n.sleepRmssd)), hb = m(base.filter(sameSrc).map((n) => n.sleepRmssd));
  if (hr != null && hb != null && hr <= hb * 0.8) out.push({ key: 'hrv', label: 'HRV down', detail: `${Math.round((hr / hb - 1) * 100)} %` });
  const ts = recent[recent.length - 1].tempSrc, sameT = (n: Night) => n.tempSrc === ts;
  const tr = m(recent.filter(sameT).map((n) => n.skinTemp)), tb = m(base.filter(sameT).map((n) => n.skinTemp));
  if (tr != null && tb != null && tr - tb >= 0.6) out.push({ key: 'temp', label: 'Skin temperature up', detail: `+${(tr - tb).toFixed(1)} °C` });
  const br = m(recent.map((n) => n.respRate)), bb = m(base.map((n) => n.respRate));
  if (br != null && bb != null && br - bb >= 1.5) out.push({ key: 'resp', label: 'Breathing faster', detail: `+${(br - bb).toFixed(1)} /min` });
  return { flagged: out.length >= 2, signals: out };
}

/** Apple-style guidance words for a recovery score. */
export function readiness(score: number) {
  return score >= 80 ? 'Go for it' : score >= 67 ? 'Ready' : score >= 34 ? 'Pace yourself' : 'Recover';  // matches the colour bands
}

// ------------------------------------------------------------------ strain, zones, stress (daytime minutes)

export const hrMax = (age: number) => 208 - 0.7 * age; // Tanaka et al. 2001
/**
 * Edwards TRIMP (1993): minutes in 50–60 / 60–70 / 70–80 / 80–90 / 90–100 % HRmax, weighted 1–5.
 * Strain (0–21) = 4 ln(1 + TRIMP / 6): Telomy's log mapping (WHOOP's Borg-style 0–21 scale is proprietary).
 * ~10 easy minutes ≈ 3, a 45-min moderate run ≈ 13, a hard 90-min session ≈ 17.
 */
export function zonesFor(mins: MinuteRec[], age: number) {
  const max = hrMax(age), zones = [0, 0, 0, 0, 0];
  for (const m of mins) {
    if (!m.hr || m.quality === 'poor' || m.quality === 'no_contact') continue;
    const f = m.hr / max;
    if (f >= 0.5) zones[Math.min(4, Math.floor((f - 0.5) * 10))] += 1;
  }
  const trimp = zones.reduce((s, v, i) => s + v * (i + 1), 0);
  return { zones, trimp };
}
export const strainFromTrimp = (t: number) => Math.min(21, 4 * Math.log(1 + t / 6));

/**
 * Stress (awake, not exercising): a minute is "stress" when HR ≥ resting + 10 bpm and its RMSSD is below the person's
 * 25th percentile of calm-minute RMSSD; "calm" when HR ≤ resting + 5 and RMSSD ≥ their median (Firstbeat-style
 * HRV stress/recovery classification, Firstbeat white paper 2014). Score = 100 × stress / (stress + calm + neutral).
 */
export function stressFor(mins: MinuteRec[], resting: number, rmssdRef: number[]) {
  const q25 = rmssdRef.length >= 20 ? [...rmssdRef].sort((a, b) => a - b)[Math.floor(rmssdRef.length / 4)] : 25;
  const q50 = rmssdRef.length >= 20 ? median(rmssdRef) : 35;
  let stress = 0, calm = 0, neutral = 0;
  const timeline: { ts: string; level: 0 | 1 | 2 }[] = [];
  for (const m of mins) {
    if (!m.hr || m.sleep === 'asleep' || m.activity === 'active' || m.activity === 'moving') continue;
    if (m.quality !== 'good' && m.quality !== 'acceptable') continue;
    let lvl: 0 | 1 | 2 = 1;
    if (m.hr >= resting + 10 && (m.rmssd == null || m.rmssd < q25)) lvl = 2;
    else if (m.hr <= resting + 5 && m.rmssd != null && m.rmssd >= q50) lvl = 0;
    lvl === 2 ? stress++ : lvl === 0 ? calm++ : neutral++;
    timeline.push({ ts: m.ts, level: lvl });
  }
  const total = stress + calm + neutral;
  return { score: total >= 30 ? Math.round((100 * stress) / total) : null, stressMin: stress, calmMin: calm, minutes: total, timeline };
}

/** VO₂max estimate, Uth et al. 2004: 15.3 × HRmax / HRrest (±~5 ml/kg/min). HRrest = personal resting HR (awake). */
export const vo2max = (age: number, restingHr: number) => (restingHr > 30 ? 15.3 * (hrMax(age) / restingHr) : null);

// ------------------------------------------------------------------ coach line

export function coachLine(rec: Score, sleep: Score | null, n?: Night) {
  if (rec.score == null) return 'Wear the band tonight and tap Overnight sleep: tomorrow you get recovery, sleep and breathing.';
  const hrv = rec.contributors.find((c) => c.key === 'hrv');
  const parts: string[] = [];
  if (n) parts.push(`You slept ${fmtDur(n.tstMin)}`);
  if (hrv) parts.push(`HRV ${hrv.value}`);
  const lead = parts.join(', ');
  const advice = rec.score >= 80 ? 'a good day to push hard.' : rec.score >= 67 ? 'a normal training day is fine.'
    : rec.score >= 34 ? 'keep intensity moderate today.' : 'favour rest, light movement and an early night.';
  return `${lead}: ${advice}`;
}

// ------------------------------------------------------------------ hook

export type DayEvent = { t: number; end: number; label: string };
export type UserEventRec = { kind: string; label: string; note?: string; t: number; captureId?: string };

/** Per-night scores for trends: each night scored against the nights before it (as it was that morning). */
export function nightSeries(nights: Night[]) {
  return nights.map((n) => {
    const s = sleepScore(n, nights);
    const r = recoveryScore(n, nights, s, []);
    return { n, sleep: s.score, recovery: r.score };
  });
}

/** Personal normal range: mean ± 1 SD of the previous ≤ 30 values (needs 3). */
export function normalBand(values: number[]) {
  if (values.length < 3) return null;
  const m = mean(values), s = sd(values);
  return { lo: m - s, hi: m + s, mean: m };
}
