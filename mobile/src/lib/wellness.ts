// Telomy wellness scores, computed on the phone from the ECG band (works offline).
// Inputs: overnight-sleep captures (KYSleepNight + KYNightMetrics summaries) and per-minute band summaries
// (Documents/wellness/minutes). Every score is a wellness estimate, not a diagnosis. Methods and sources:
// docs/devices/WELLNESS_SCORES.md.
import { useCallback, useEffect, useState } from 'react';
import { Band, bandAvailable } from './band';
import type { CaptureMeta } from '../../modules/ky-ecg';

// ------------------------------------------------------------------ types

export type Night = {
  id: string; date: string; start: number; end: number;
  tstMin: number; efficiency: number; onsetMin?: number; wasoMin: number; awakenings: number;
  sleepHr?: number; sleepRmssd?: number; lateRmssd?: number; lowestHr?: number; lowestHrAt?: number; lowestHrPos?: number;
  hrDropPct?: number; respRate?: number; hypnogram: number[]; epochSec: number;
  hr5: [number, number, number][]; hrv5: [number, number, number][]; events: { type: string; start: number; end: number }[];
  midpoint: number;  // unix time of the sleep midpoint
};
export type MinuteRec = { ts: string; hr: number; rmssd?: number; quality?: string; activity?: string; sleep?: string; motion?: number | null; resting?: number };
export type Contributor = { key: string; label: string; score: number | null; value: string; note: string };
export type Score = { score: number | null; label: string; contributors: Contributor[]; calibrating?: string };

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
const localDate = (t: number) => { const d = new Date(t * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

// ------------------------------------------------------------------ nights from captures

export function nightsFrom(captures: CaptureMeta[]): Night[] {
  const out: Night[] = [];
  for (const c of captures as any[]) {
    const s = c.summary ?? {}, sl = s.sleep, nm = s.night ?? {};
    if (c.therapyId !== 'sleep' || !sl || !c.endedAt) continue;
    const epoch = sl.epochSec ?? 30;
    const hyp: number[] = sl.hypnogram ?? [];
    const first = hyp.indexOf(1), last = hyp.lastIndexOf(1);
    const t0 = sl.t0 ?? c.startedAt;  // sleep epochs start with the ECG
    const mid = first >= 0 ? t0 + ((first + last + 1) / 2) * epoch : (c.startedAt + c.endedAt) / 2;
    out.push({
      id: c.id, date: localDate(c.endedAt), start: t0, end: c.endedAt,
      tstMin: sl.totalSleepMin, efficiency: sl.efficiency, onsetMin: sl.onsetMin, wasoMin: sl.wasoMin, awakenings: sl.awakenings,
      sleepHr: nm.avgSleepHr ?? sl.sleepHr, sleepRmssd: nm.sleepRmssd ?? sl.sleepRmssd, lateRmssd: nm.lateRmssd,
      lowestHr: nm.lowestHr, lowestHrAt: nm.lowestHrAt, lowestHrPos: nm.lowestHrPos, hrDropPct: nm.hrDropPct, respRate: nm.respRate,
      hypnogram: hyp, epochSec: epoch, hr5: nm.hr5 ?? [], hrv5: nm.hrv5 ?? [], events: s.events ?? [], midpoint: mid,
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
export function sleepScore(n: Night, history: Night[]): Score {
  const prev = history.filter((h) => h.end < n.end).slice(-30);
  const c: (Contributor & { w: number })[] = [];
  c.push({ key: 'duration', label: 'Total sleep', w: 0.3, value: fmtDur(n.tstMin), note: 'Adults need 7–9 h',
    score: knots(n.tstMin / 60, [[4, 0], [5, 35], [6, 65], [7, 100], [9, 100], [10, 90], [11, 75]]) });
  c.push({ key: 'efficiency', label: 'Efficiency', w: 0.15, value: `${Math.round(n.efficiency * 100)}%`, note: '85 % or more is good',
    score: knots(n.efficiency * 100, [[65, 0], [74, 25], [85, 75], [90, 100]]) });
  if (n.onsetMin != null) c.push({ key: 'latency', label: 'Time to fall asleep', w: 0.1, value: `${Math.round(n.onsetMin)} min`, note: '15 min or less is good',
    score: knots(n.onsetMin, [[15, 100], [30, 70], [45, 30], [60, 0]]) });
  c.push({ key: 'waso', label: 'Awake after falling asleep', w: 0.1, value: `${Math.round(n.wasoMin)} min`, note: '20 min or less is good',
    score: knots(n.wasoMin, [[20, 100], [35, 65], [50, 30], [80, 0]]) });
  c.push({ key: 'awakenings', label: 'Wake-ups', w: 0.05, value: `${n.awakenings}`, note: 'Brief wake-ups are normal; fewer is better',
    score: knots(n.awakenings, [[2, 100], [4, 65], [6, 30], [9, 0]]) });
  if (n.sleepRmssd) {
    const base = prev.map((h) => h.sleepRmssd).filter(Boolean).map((v) => Math.log(v!));
    if (base.length >= 3) {
      const z = (Math.log(n.sleepRmssd) - mean(base)) / Math.max(0.05, sd(base));
      c.push({ key: 'restoration', label: 'Restoration (HRV)', w: 0.15, value: `${Math.round(n.sleepRmssd)} ms`, note: 'Overnight HRV vs your normal',
        score: clamp(70 + 20 * z) });
    } else {
      c.push({ key: 'restoration', label: 'Restoration (HRV)', w: 0.15, value: `${Math.round(n.sleepRmssd)} ms`, note: `Learning your normal (${base.length}/3 nights)`, score: null });
    }
  }
  if (n.hrDropPct != null) c.push({ key: 'drop', label: 'Heart-rate drop', w: 0.1, value: `${Math.round(n.hrDropPct)}%`, note: 'A 10 % or larger drop in sleep is typical',
    score: knots(n.hrDropPct, [[0, 0], [5, 30], [10, 70], [15, 100]]) });
  const mids = [...prev.slice(-6), n].map((h) => { const d = new Date(h.midpoint * 1000); return ((d.getHours() + 12) % 24) * 60 + d.getMinutes(); });
  if (mids.length >= 3) {
    const s = sd(mids);
    c.push({ key: 'regularity', label: 'Regular timing', w: 0.05, value: `±${Math.round(s)} min`, note: 'Same sleep timing every night helps',
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
export function recoveryScore(n: Night | undefined, history: Night[], sleep: Score | null, loads: number[]): Score {
  if (!n || !n.sleepRmssd) return { score: null, label: 'Wear the band tonight', contributors: [], calibrating: 'Needs one night with the band' };
  const prev = history.filter((h) => h.end < n.end).slice(-30);
  const c: (Contributor & { w: number; z: number | null })[] = [];
  const lnb = prev.map((h) => h.sleepRmssd).filter(Boolean).map((v) => Math.log(v!));
  const calibrating = lnb.length < 3 ? `Learning your normal: night ${lnb.length + 1} of 4` : undefined;
  // until a baseline exists, compare with healthy-adult references (RMSSD ≈ 42 ± 15 ms, Nunan 2010; RHR 60 ± 8)
  const hm = lnb.length >= 3 ? mean(lnb) : Math.log(42), hs = lnb.length >= 3 ? Math.max(0.08, sd(lnb)) : 0.35;
  const zH = (Math.log(n.sleepRmssd) - hm) / hs;
  c.push({ key: 'hrv', label: 'HRV', w: 0.45, z: zH, value: `${Math.round(n.sleepRmssd)} ms`,
    note: lnb.length >= 3 ? `Your normal ${Math.round(Math.exp(hm))} ms` : 'Compared with typical adults until your normal is learnt', score: clamp(60 + 20 * zH) });
  if (n.lowestHr) {
    const rb = prev.map((h) => h.lowestHr).filter(Boolean) as number[];
    const rm = rb.length >= 3 ? mean(rb) : 60, rs = rb.length >= 3 ? Math.max(1.5, sd(rb)) : 8;
    const zR = -(n.lowestHr - rm) / rs;
    c.push({ key: 'rhr', label: 'Resting heart rate', w: 0.25, z: zR, value: `${Math.round(n.lowestHr)} bpm`,
      note: rb.length >= 3 ? `Your normal ${Math.round(rm)} bpm` : 'Lowest 5-min heart rate asleep', score: clamp(60 + 20 * zR) });
  }
  if (n.respRate) {
    const bb = prev.map((h) => h.respRate).filter(Boolean) as number[];
    const zB = bb.length >= 3 ? -Math.max(0, (n.respRate - mean(bb)) / Math.max(0.5, sd(bb))) : 0;
    c.push({ key: 'resp', label: 'Breathing rate', w: 0.1, z: zB, value: `${n.respRate.toFixed(1)} /min`,
      note: bb.length >= 3 ? `Your normal ${mean(bb).toFixed(1)} /min` : 'Learning your normal', score: clamp(70 + 20 * zB) });
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
  return { score, label: readiness(score), calibrating, contributors: c.map(({ w, z: _z, ...x }) => ({ ...x, score: x.score == null ? null : Math.round(x.score) })) };
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

export type Wellness = {
  loading: boolean; nights: Night[]; last?: Night; sleep: Score | null; recovery: Score; age: number;
  today: { minutes: MinuteRec[]; zones: number[]; trimp: number; strain: number; stress: ReturnType<typeof stressFor>; worn: number; activeMin: number };
  yesterdayTrimp: number | null; restingHr: number | null; vo2: number | null; reload: () => void; sessionsToday: DayEvent[];
};

const reanalysed = new Set<string>();
let pending: Promise<void> | null = null;
const reloaders = new Set<() => void>();

export function useWellness(ageHint?: number | null): Wellness {
  const [state, setState] = useState<{ nights: Night[]; minutes: MinuteRec[]; age: number; sessions: DayEvent[] } | null>(null);
  const load = useCallback(async () => {
    const caps = bandAvailable ? Band.listCaptures() : [];
    // nights recorded before the night metrics existed: re-analyse once (in the background) so they get them.
    // One shared job: every mounted instance waits for it, then all reload.
    const stale = (caps as any[]).filter((c) => c.therapyId === 'sleep' && c.endedAt && (c.summary as any)?.sleep?.t0 == null && !reanalysed.has(c.id));
    if (stale.length && !pending) {
      pending = (async () => { for (const c of stale) { reanalysed.add(c.id); await Band.reanalyseCapture(c.id); } })()
        .finally(() => { pending = null; reloaders.forEach((r) => r()); });
    }
    if (pending) { await pending; return; }  // the finally() above reloads every instance
    const minutes = (bandAvailable ? await Band.wellnessRead('minutes', 8) : []) as MinuteRec[];
    let age = ageHint ?? null;
    if (age) Band.wellnessAppend('profile', { age });
    else age = ((await Band.wellnessRead('profile', 60)).filter((p) => p.age).pop()?.age as number) ?? 35;
    const dayStart = new Date(); dayStart.setHours(0, 0, 0, 0);
    const sessions: DayEvent[] = (caps as any[]).filter((c) => c.therapyId !== 'sleep' && c.startedAt >= dayStart.getTime() / 1000)
      .map((c) => ({ t: c.startedAt, end: c.endedAt ?? c.startedAt, label: c.therapy }));
    setState({ nights: nightsFrom(caps), minutes, age: age!, sessions });
  }, [ageHint]);
  useEffect(() => { reloaders.add(load); load(); return () => { reloaders.delete(load); }; }, [load]);

  const nights = state?.nights ?? [];
  const age = state?.age ?? 35;
  const last = nights[nights.length - 1];
  const fresh = last && Date.now() / 1000 - last.end < 20 * 3600 ? last : undefined;  // today's night
  const sleep = fresh ? sleepScore(fresh, nights) : null;
  const mins = state?.minutes ?? [];
  const todayKey = localDate(Date.now() / 1000), yKey = localDate(Date.now() / 1000 - 86400);
  const byDay = (k: string) => mins.filter((m) => m.ts.startsWith(k));
  const dayTrimps = Array.from({ length: 8 }, (_, i) => localDate(Date.now() / 1000 - (7 - i) * 86400))
    .map((k) => byDay(k)).filter((d) => d.length >= 60).map((d) => zonesFor(d, age).trimp);
  const recovery = recoveryScore(fresh, nights, sleep, dayTrimps.length && byDay(yKey).length >= 60 ? dayTrimps : []);
  const tm = byDay(todayKey);
  const { zones, trimp } = zonesFor(tm, age);
  const restings = mins.map((m) => m.resting).filter(Boolean) as number[];
  const restingHr = restings.length ? restings[restings.length - 1] : null;
  const calmRef = mins.filter((m) => m.rmssd && m.activity === 'rest' && m.sleep !== 'asleep').map((m) => m.rmssd!) ;
  const stress = stressFor(tm, restingHr ?? 65, calmRef);
  return {
    loading: !state, nights, last: fresh, sleep, recovery, age,
    today: { minutes: tm, zones, trimp, strain: strainFromTrimp(trimp), stress, worn: tm.length,
      activeMin: tm.filter((m) => m.activity === 'active').length },
    yesterdayTrimp: byDay(yKey).length >= 60 ? zonesFor(byDay(yKey), age).trimp : null,
    restingHr, vo2: restingHr ? vo2max(age, restingHr) : null, reload: load, sessionsToday: state?.sessions ?? [],
  };
}
