// Sleep from every device, fused into one night per date, plus sleep need, sleep debt and the Sleep Regularity Index.
//
// Source priority (best evidence first, one night per date, never double-counted):
//   1. Telomy patch: ECG staging (Conv1d + BiGRU on HRV + ECG-derived breathing, KYSleepStager) — 4 stages.
//   2. Apple Watch stages from Apple Health: independent PSG studies put Apple's 4-stage kappa at ≈ 0.53–0.60
//      (Schyvens et al. 2025; Robbins et al. 2024), the most independently validated consumer stager.
//   3. Ring only: sleep/wake from the ring's own 5-minute heart-rate log + iPhone motion (no stages — a 5-minute HR
//      series cannot stage sleep honestly), with the night's lowest HR and the ring's overnight HRV.
//   4. Other Apple Health sleep (iPhone schedule, third-party apps): duration and timing only.
// The ring's 5-min HR fills lowest HR / HRV into Watch nights when the ring was worn too.
//
// Sleep need follows WHOOP's published idea (need = baseline + strain + debt − naps), with transparent terms:
//   baseline 8 h (NSF 7–9 h) until 14 nights, then personal (mean of your longer half of nights, the sleep-extension
//   asymptote, Klerman & Dijk 2005), clamped 7–9 h; strain adds up to 45 min; 30 % of the current debt is added.
// Sleep debt is a decaying running balance (Van Dongen et al. 2003: deficits accumulate; surplus sleep repays part):
//   debt ← max(0, 0.85 · debt + need − slept), over the last 14 nights.
// Sleep Regularity Index (Phillips et al. 2017): −100 + 200 · P(same sleep/wake state 24 h apart), 5-min bins.
import type { HealthSleepSegment, PhoneActivity, RingHistorySample } from '../../modules/ky-ecg';
import type { Night } from './wellness';

export type SleepSource = 'patch' | 'watch' | 'ring' | 'health';
export const SOURCE_LABEL: Record<SleepSource, string> = {
  patch: 'Telomy patch · ECG stages', watch: 'Apple Watch · stages', ring: 'Telomy ring · heart rate + phone motion', health: 'Apple Health · duration',
};

const EPOCH = 30;
const localDate = (t: number) => { const d = new Date(t * 1000); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };
const mean = (a: number[]) => a.reduce((s, v) => s + v, 0) / a.length;
const median = (a: number[]) => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : NaN; };
const pct = (a: number[], q: number) => { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.floor(q * s.length))]; };

/** Night summary from a 30-s stage grid (0 wake, 1 light, 2 deep, 3 REM, 4 asleep-unstaged, -1 no data). */
function summarise(grid: number[], t0: number, staged: boolean): Omit<Night, 'id' | 'date' | 'hr5' | 'hrv5' | 'events'> | null {
  const asleep = grid.map((s) => s > 0);
  const first = asleep.indexOf(true), last = asleep.lastIndexOf(true);
  if (first < 0) return null;
  const span = grid.slice(first, last + 1).filter((s) => s >= 0);
  const tst = span.filter((s) => s > 0).length / 2;
  let awak = 0, run = 0;
  for (const s of span) { if (s === 0) run++; else { if (run >= 2) awak++; run = 0; } }
  const n = (c: number) => span.filter((s) => s === c).length / 2;
  const known = grid.filter((s) => s >= 0).length;
  const remAt = staged ? grid.indexOf(3) : -1;
  // REM cycles: REM bouts ≥ 5 min separated by ≥ 15 min of non-REM
  let cycles = 0, remRun = 0, gap = 99, gapBefore = 99;
  if (staged) for (const s of span) {
    if (s === 3) { if (remRun === 0) gapBefore = gap; remRun++; if (remRun === 10 && gapBefore >= 30) cycles++; gap = 0; }
    else { remRun = 0; gap++; }
  }
  return {
    start: t0, end: t0 + grid.length * EPOCH, tstMin: tst, efficiency: known ? tst / (known / 2) : 0,
    onsetMin: grid.slice(0, first).filter((s) => s >= 0).length / 2, wasoMin: n(0), awakenings: awak,
    hypnogram: grid.map((s) => (s < 0 ? 0 : s > 0 ? 1 : 0)), epochSec: EPOCH,
    midpoint: t0 + ((first + last + 1) / 2) * EPOCH,
    ...(staged ? { stages: grid.map((s) => (s === 4 ? 1 : s)), lightMin: n(1) + n(4), deepMin: n(2), remMin: n(3),
      remLatencyMin: remAt >= 0 ? (remAt - first) / 2 : undefined, remCycles: cycles } : {}),
  };
}

/** Ring HR/HRV during a night: mean sleeping HR, lowest 15-min HR (and where in the night), median HRV. */
function ringOverlay(n: Night, ring: RingHistorySample[], dayHr: number | null): Partial<Night> {
  const inN = ring.filter((s) => s.t / 1000 >= n.start && s.t / 1000 < n.end);
  const hr = inN.filter((s) => s.hr).map((s) => ({ t: s.t / 1000, v: s.hr! }));
  const out: Partial<Night> = {};
  if (hr.length >= 12) {
    out.sleepHr = mean(hr.map((x) => x.v));
    let lo = Infinity, at = 0;
    for (let i = 1; i + 1 < hr.length; i++) { const m = (hr[i - 1].v + hr[i].v + hr[i + 1].v) / 3; if (m < lo) { lo = m; at = hr[i].t; } }
    if (isFinite(lo)) { out.lowestHr = lo; out.lowestHrAt = at; out.lowestHrPos = (at - n.start) / Math.max(1, n.end - n.start); }
    if (dayHr) out.hrDropPct = 100 * (1 - out.sleepHr / dayHr);
    out.hr5 = hr.map((x) => [x.t, x.v, x.v] as [number, number, number]);
  }
  const hrv = inN.filter((s) => s.hrv).map((s) => s.hrv!);
  if (hrv.length >= 6) { out.sleepRmssd = median(hrv); out.hrvSrc = 'ring'; }
  return out;
}

/** Daytime mean ring HR (10:00–20:00) the day before a night, for the nocturnal dip. */
function dayHrBefore(start: number, ring: RingHistorySample[]) {
  const d = new Date(start * 1000); d.setHours(10, 0, 0, 0);
  let a = d.getTime() / 1000; if (a > start) a -= 86400;
  const v = ring.filter((s) => s.hr && s.t / 1000 >= a && s.t / 1000 < a + 10 * 3600).map((s) => s.hr!);
  return v.length >= 24 ? mean(v) : null;
}

// ------------------------------------------------------------------ Apple Health nights

/** Cluster segments into nights (gaps < 2 h), one source per night (Watch stages preferred), ≥ 3 h asleep. */
export function healthNights(segs: HealthSleepSegment[]): Night[] {
  const out: Night[] = [];
  const sorted = [...segs].sort((a, b) => a.start - b.start);
  const clusters: HealthSleepSegment[][] = [];
  for (const s of sorted) {
    const c = clusters[clusters.length - 1];
    if (c && s.start - Math.max(...c.map((x) => x.end)) < 2 * 3600) c.push(s); else clusters.push([s]);
  }
  for (const c of clusters) {
    const staged = c.filter((s) => s.stage >= 1 && s.stage <= 3);
    const bySrc = new Map<string, HealthSleepSegment[]>();
    for (const s of c) bySrc.set(s.source, [...(bySrc.get(s.source) ?? []), s]);
    const asleepMin = (a: HealthSleepSegment[]) => a.filter((s) => s.stage >= 1 && s.stage <= 4).reduce((m, s) => m + (s.end - s.start) / 60, 0);
    // the source with staged segments wins; otherwise the one with the most sleep
    const stagedSrc = staged.length ? staged[0].source : null;
    const src = stagedSrc ?? [...bySrc.entries()].sort((a, b) => asleepMin(b[1]) - asleepMin(a[1]))[0][0];
    const use = bySrc.get(src)!;
    if (asleepMin(use) < 180) continue;
    const t0 = Math.min(...use.map((s) => s.start)), t1 = Math.max(...use.map((s) => s.end));
    const grid = new Array(Math.ceil((t1 - t0) / EPOCH)).fill(-1);
    // in-bed first (as wake), then sleep stages over it, awake last
    for (const pass of [5, 4, 1, 2, 3, 0]) for (const s of use) if (s.stage === pass) {
      for (let i = Math.floor((s.start - t0) / EPOCH); i < Math.ceil((s.end - t0) / EPOCH) && i < grid.length; i++) grid[i] = pass === 5 ? 0 : pass;
    }
    const isStaged = !!stagedSrc;
    const sm = summarise(grid, t0, isStaged);
    if (!sm) continue;
    const watch = isStaged || use.some((s) => s.watch);
    out.push({ ...sm, id: `hk-${Math.round(t0)}`, date: localDate(sm.end), hr5: [], hrv5: [], events: [],
      source: watch && isStaged ? 'watch' : 'health', sourceName: src });
  }
  return out;
}

// ------------------------------------------------------------------ ring-only nights

/**
 * Sleep/wake from the ring's 5-min HR log (+ iPhone motion), for nights with no patch or Watch.
 * A sample is "asleep-like" when its HR is within max(8 bpm, 12 %) of that night's 10th-percentile HR and the phone
 * wasn't walking/running/driving; a 3-sample median removes single blips; the longest run (gaps ≤ 30 min) ≥ 3 h is
 * the night. HR-based sleep/wake from consumer wearables agrees with PSG on sleep vs wake far better than on stages
 * (de Zambotti et al. 2019), so ring-only nights carry duration, timing, lowest HR and HRV — no stages.
 */
export function ringNights(ring: RingHistorySample[], phone: PhoneActivity[], days = 14): Night[] {
  const out: Night[] = [];
  const now = Date.now() / 1000;
  for (let d = 0; d < days; d++) {
    const eve = new Date((now - d * 86400) * 1000); eve.setHours(20, 0, 0, 0);
    const a = eve.getTime() / 1000 - 86400, b = a + 16 * 3600;     // 20:00 → 12:00 the next day
    if (a > now) continue;
    const hr = ring.filter((s) => s.hr && s.t / 1000 >= a && s.t / 1000 < b).map((s) => ({ t: s.t / 1000, v: s.hr! }));
    if (hr.length < 36) continue;
    const floor = pct(hr.map((x) => x.v), 0.1);
    const lim = floor + Math.max(8, 0.12 * floor);
    const moving = (t: number) => phone.some((p) => p.type !== 'still' && p.type !== 'unknown' && t >= p.start && t < p.end);
    const raw = hr.map((x) => (x.v <= lim && !moving(x.t) ? 1 : 0));
    const sm = raw.map((_, i) => median(raw.slice(Math.max(0, i - 1), i + 2)));
    let best: [number, number] | null = null, s0 = -1, lastSleep = -1;
    for (let i = 0; i <= hr.length; i++) {
      const asleep = i < hr.length && sm[i] === 1;
      if (asleep) { if (s0 < 0 || hr[i].t - hr[lastSleep].t > 1800) { if (s0 >= 0 && (!best || hr[lastSleep].t - hr[s0].t > best[1] - best[0])) best = [hr[s0].t, hr[lastSleep].t]; s0 = i; } lastSleep = i; }
      if (i === hr.length && s0 >= 0 && (!best || hr[lastSleep].t - hr[s0].t > best[1] - best[0])) best = [hr[s0].t, hr[lastSleep].t];
    }
    if (!best || best[1] - best[0] < 3 * 3600) continue;
    const t0 = best[0], t1 = best[1] + 300;
    const grid = new Array(Math.ceil((t1 - t0) / EPOCH)).fill(-1);
    hr.forEach((x, i) => {
      if (x.t < t0 || x.t >= t1) return;
      for (let k = 0; k < 10; k++) { const j = Math.floor((x.t - t0) / EPOCH) + k; if (j < grid.length) grid[j] = sm[i] ? 4 : 0; }
    });
    // fill short no-data gaps inside the night as asleep (ring's 5-min cadence skips samples while still)
    for (let i = 0; i < grid.length; i++) if (grid[i] === -1) grid[i] = 4;
    const s = summarise(grid, t0, false);
    if (!s) continue;
    out.push({ ...s, onsetMin: undefined, id: `ring-${Math.round(t0)}`, date: localDate(s.end), hr5: [], hrv5: [], events: [], source: 'ring', sourceName: 'Telomy ring' });
  }
  return out;
}

// ------------------------------------------------------------------ fusion

const overlap = (a: Night, b: Night) => Math.max(0, Math.min(a.end, b.end) - Math.max(a.start, b.start)) / Math.max(1, Math.min(a.end - a.start, b.end - b.start));

/** One night per sleep period: patch > Watch > ring > other Health; ring HR/HRV filled into nights that lack it. */
export function fuseNights(patch: Night[], health: Night[], ring: RingHistorySample[], phone: PhoneActivity[]): Night[] {
  const ringOnly = ringNights(ring, phone);
  const order: Night[] = [
    ...patch.map((n) => ({ ...n, source: 'patch' as const, sourceName: 'Telomy patch', hrvSrc: n.hrvSrc ?? ('ecg' as const) })),
    ...health.filter((n) => n.source === 'watch'), ...ringOnly, ...health.filter((n) => n.source !== 'watch'),
  ];
  const chosen: Night[] = [];
  for (const n of order) if (!chosen.some((c) => overlap(c, n) > 0.3)) chosen.push(n);
  return chosen.map((n) => {
    if (n.source === 'patch' && n.sleepRmssd && n.lowestHr) return n;
    const o = ringOverlay(n, ring, dayHrBefore(n.start, ring));
    const fill: Partial<Night> = {};
    for (const k of Object.keys(o) as (keyof Night)[]) if ((n as any)[k] == null || (Array.isArray((n as any)[k]) && !(n as any)[k].length)) (fill as any)[k] = (o as any)[k];
    return { ...n, ...fill };
  }).sort((a, b) => a.end - b.end);
}

// ------------------------------------------------------------------ need, debt, regularity

export type SleepNeed = {
  needMin: number; baselineMin: number; strainMin: number; debtMin: number; repayMin: number; personal: boolean;
  lastNightPct: number | null;           // last night's sleep as a share of that night's need (WHOOP "sleep performance")
  bedtime: number | null; wake: number | null;   // suggested tonight (unix s) from your usual wake time
};

const strainAdd = (strain: number) => (strain <= 10 ? 0 : strain >= 21 ? 45 : strain <= 14 ? (strain - 10) * 3.75 : strain <= 18 ? 15 + (strain - 14) * 5 : 35 + (strain - 18) * 3.33);

/** `strainByDate`: day strain (0–21) keyed by local date (the day before each night ends). */
export function sleepNeed(nights: Night[], strainToday: number, strainByDate: Record<string, number> = {}): SleepNeed {
  const recent = nights.slice(-30);
  const personal = recent.length >= 14;
  const longer = [...recent].map((n) => n.tstMin).sort((a, b) => b - a).slice(0, Math.ceil(recent.length / 2));
  const baselineMin = personal ? Math.max(420, Math.min(540, mean(longer))) : 480;
  let debt = 0, lastNeed = baselineMin;
  const last14 = nights.slice(-14);
  last14.forEach((n, i) => {
    const prevDay = localDate(n.start - 6 * 3600);   // the day before the night (a 01:00 bedtime counts as the previous day)
    // debt accrues against baseline + strain only (adding the repayment term here would feed back on itself)
    const need = baselineMin + strainAdd(strainByDate[prevDay] ?? 0);
    // skip-day gap: missing nights are unknown, not zero sleep — only decay the balance
    const gapDays = i ? Math.max(0, Math.round((n.end - last14[i - 1].end) / 86400) - 1) : 0;
    debt *= 0.85 ** gapDays;
    debt = Math.max(0, 0.85 * debt + need - n.tstMin);
    lastNeed = need;
  });
  const last = nights[nights.length - 1];
  const strainMin = strainAdd(strainToday);
  const repayMin = Math.min(90, 0.3 * debt);
  const needMin = baselineMin + strainMin + repayMin;
  const wakes = nights.slice(-7).map((n) => { const d = new Date(n.end * 1000); return d.getHours() * 60 + d.getMinutes(); });
  let wake: number | null = null, bedtime: number | null = null;
  if (wakes.length >= 3) {
    const w = median(wakes);
    const t = new Date(); t.setHours(0, 0, 0, 0);
    wake = t.getTime() / 1000 + 86400 + w * 60;
    const latency = median(nights.slice(-7).map((n) => n.onsetMin ?? 15));
    bedtime = wake - (needMin + latency) * 60;
  }
  return { needMin, baselineMin, strainMin, debtMin: debt, repayMin, personal,
    lastNightPct: last ? Math.min(1.2, last.tstMin / lastNeed) : null, bedtime, wake };
}

/** Phillips 2017 SRI from consecutive nights (5-min bins over the 24 h from 18:00); null until 4 day-pairs. */
export function sleepRegularity(nights: Night[]): number | null {
  const byDate = new Map(nights.map((n) => [n.date, n]));
  const mask = (n: Night) => {
    const d = new Date(n.end * 1000); d.setHours(18, 0, 0, 0);
    const a = d.getTime() / 1000 - 86400;
    const m = new Array(288).fill(0);
    n.hypnogram.forEach((h, i) => { if (h) { const j = Math.floor((n.start + i * n.epochSec - a) / 300); if (j >= 0 && j < 288) m[j] = 1; } });
    return m;
  };
  let same = 0, total = 0, pairs = 0;
  for (const n of nights.slice(-8)) {
    const prev = new Date(n.end * 1000 - 86400000);
    const p = byDate.get(localDate(prev.getTime() / 1000));
    if (!p) continue;
    const a = mask(p), b = mask(n);
    for (let i = 0; i < 288; i++) { total++; if (a[i] === b[i]) same++; }
    pairs++;
  }
  return pairs >= 4 ? Math.round(-100 + (200 * same) / total) : null;
}
