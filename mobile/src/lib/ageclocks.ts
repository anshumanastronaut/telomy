// Wearable biological-age clocks: Fitness age, Autonomic (recovery) age, and Cardiac (resting-HR) age, computed on the
// phone from whatever the connected devices provide (patch HRV, ring HR/HRV, Apple Health VO₂max/RHR/sleep). These are
// transparent, literature-grounded ESTIMATES from physiology — not the blood-based PhenoAge on the Longevity screen,
// and not a diagnosis. Every clock degrades: with an input it reports with a confidence; without it, it returns null and
// the UI asks for the missing signal. Nothing here throws on missing data.
//
// References (reference curves, not copied code):
//  • VO₂max decline ~0.40 (men) / 0.33 (women) ml·kg⁻¹·min⁻¹ per year; FRIEND/ACSM population norms.
//  • Non-exercise VO₂max estimate: Uth–Nes, VO₂max ≈ 15.3 · HRmax/HRrest (already in wellness.ts).
//  • HRV (RMSSD/SDNN) declines with age; Umetani 1998, Nunan 2010 population medians by decade.
//  • HRmax: Tanaka 2001 (208 − 0.7·age), in wellness.ts.
import { knots, vo2max as estVo2max } from './wellness';

export type Sex = 'male' | 'female' | null;
export type Clock = {
  key: 'fitness' | 'autonomic' | 'cardiac' | 'muscle';
  label: string;
  years: number | null;        // estimated biological age for this system
  delta: number | null;        // years older(+)/younger(−) than chronological
  confidence: 'high' | 'medium' | 'low' | null;
  basis: string;               // which inputs were actually used
  note: string;
};
export type AgeClocks = { chrono: number | null; clocks: Clock[]; overall: { years: number; delta: number; confidence: 'high' | 'medium' | 'low' } | null };

export type ClockInputs = {
  age?: number | null;
  sex?: Sex;
  restingHr?: number | null;   // bpm, resting/sleeping
  hrvRmssd?: number | null;    // ms (patch ECG preferred, else ring)
  hrvSdnn?: number | null;     // ms (Apple Health fallback)
  vo2max?: number | null;      // ml·kg⁻¹·min⁻¹ (measured, e.g. Apple Health) — preferred over the RHR estimate
  almi?: number | null;        // appendicular lean mass index, kg/m² (DEXA / BIA in the Vault)
  emg?: { mdfSlope?: number | null; rmsRel?: number | null } | null; // EMG patch: median-frequency fatigue slope (%/s), RMS vs young norm
};

const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));

// Population-median VO₂max for a given age/sex (ml·kg⁻¹·min⁻¹), and the inverse: the age at which `v` is median.
function vo2Ref(age: number, sex: Sex) {
  const base = sex === 'female' ? 42 : 50;
  const slope = sex === 'female' ? 0.33 : 0.40;
  return { median: base - slope * (age - 20), slope, base };
}
function fitnessAge(i: ClockInputs): Clock {
  const base: Clock = { key: 'fitness', label: 'Fitness age', years: null, delta: null, confidence: null,
    basis: '', note: 'VO₂max is the single best predictor of longevity. Connect your phone's health app or log a resting HR.' };
  if (i.age == null) return base;
  const measured = i.vo2max && i.vo2max > 10 ? i.vo2max : null;
  const estimated = !measured && i.restingHr ? estVo2max(i.age, i.restingHr) : null;
  const v = measured ?? estimated;
  if (!v) return base;
  const { slope } = vo2Ref(i.age, i.sex ?? null);
  // age where this VO₂max is the population median → fitness age
  const refAtChrono = vo2Ref(i.age, i.sex ?? null).median;
  const years = clamp(i.age + (refAtChrono - v) / slope, 18, 95);
  return { ...base, years, delta: years - i.age, confidence: measured ? 'high' : 'low',
    basis: measured ? `measured VO₂max ${v.toFixed(0)}` : `VO₂max est. ${v.toFixed(0)} from resting HR`,
    note: measured ? 'From your measured VO₂max vs population norms for your age and sex.'
      : 'Estimated from resting heart rate (Uth–Nes). A measured VO₂max from Apple Health is far more accurate.' };
}

// Median HRV (ms) by age — used to invert an HRV reading into an "autonomic age". RMSSD and SDNN track closely in
// resting data, so we feed either into the same curve with a small SDNN→RMSSD adjustment.
const RMSSD_BY_AGE: [number, number][] = [[20, 46], [30, 38], [40, 32], [50, 27], [60, 23], [70, 20], [80, 17]];
function autonomicAge(i: ClockInputs): Clock {
  const base: Clock = { key: 'autonomic', label: 'Recovery age', years: null, delta: null, confidence: null,
    basis: '', note: 'Reflects heart-rate variability (autonomic balance). Wear the patch or ring at rest to measure.' };
  if (i.age == null) return base;
  const rmssd = i.hrvRmssd && i.hrvRmssd > 2 ? i.hrvRmssd : (i.hrvSdnn && i.hrvSdnn > 2 ? i.hrvSdnn * 0.9 : null);
  if (!rmssd) return base;
  // invert the age→RMSSD curve: find the age whose median RMSSD equals this reading
  const ages = RMSSD_BY_AGE.map(([a]) => a);
  const inv: [number, number][] = RMSSD_BY_AGE.map(([a, r]) => [r, a]).sort((x, y) => x[0] - y[0]) as [number, number][];
  const years = clamp(knots(rmssd, inv), 18, 95);
  const high = i.hrvRmssd != null;  // patch/ring RMSSD is a real short-term measure; Health SDNN is coarser
  return { ...base, years, delta: years - i.age, confidence: high ? 'medium' : 'low',
    basis: `${i.hrvRmssd ? 'RMSSD' : 'SDNN'} ${Math.round(rmssd)} ms`,
    note: 'Higher HRV for your age reads as a younger, better-recovered autonomic system. Best measured at rest or asleep.' };
}

function cardiacAge(i: ClockInputs): Clock {
  const base: Clock = { key: 'cardiac', label: 'Cardiac age', years: null, delta: null, confidence: null,
    basis: '', note: 'Resting heart rate vs your chronological age. Measured from the ring, patch, or Apple Health.' };
  if (i.age == null || !i.restingHr || i.restingHr < 30) return base;
  // Resting HR is flatter with age than fitness is, so we use a gentle mapping: every 10 bpm above a ~60 bpm
  // reference ≈ +8 cardiac-age years (resting tachycardia tracks all-cause and CV mortality; Jensen 2013).
  const years = clamp(i.age + (i.restingHr - 60) * 0.8, 18, 95);
  return { ...base, years, delta: years - i.age, confidence: 'low', basis: `resting HR ${Math.round(i.restingHr)} bpm`,
    note: 'A lower resting heart rate generally reads as a younger, more efficient heart. This is a coarse signal; HRV and VO₂max matter more.' };
}

// Median ALMI (kg/m²) by age, from NHANES DXA reference data (Kelly 2009): lean mass is stable to ~40 then declines
// ~0.5–1 %/year. Inverting it gives a "muscle age". EMG (when the patch exists) refines it: older muscle fatigues
// faster (steeper median-frequency decline in a sustained contraction) and recruits with lower RMS per unit effort.
const ALMI_BY_AGE: Record<'male' | 'female', [number, number][]> = {
  male: [[20, 8.6], [30, 8.7], [40, 8.6], [50, 8.3], [60, 8.0], [70, 7.6], [80, 7.1]],
  female: [[20, 6.6], [30, 6.7], [40, 6.7], [50, 6.5], [60, 6.3], [70, 6.0], [80, 5.6]],
};
function muscleAge(i: ClockInputs): Clock {
  const base: Clock = { key: 'muscle', label: 'Muscle age', years: null, delta: null, confidence: null, basis: '',
    note: 'From muscle mass (DEXA/body-composition scan in your Vault). The Telomy EMG patch will add muscle quality and fatigue.' };
  if (i.age == null || !i.almi || i.almi < 3) return base;
  const curve = ALMI_BY_AGE[i.sex === 'female' ? 'female' : 'male'];
  // invert only the declining limb (≥ 40 y); above the peak reads as ≤ 35
  const decl = curve.filter(([a]) => a >= 40).map(([a, v]) => [v, a] as [number, number]).sort((x, y) => x[0] - y[0]);
  let years = i.almi >= decl[decl.length - 1][0] ? 35 - Math.min(10, (i.almi - decl[decl.length - 1][0]) * 10) : knots(i.almi, decl);
  let basis = `ALMI ${i.almi.toFixed(1)} kg/m²`, conf: Clock['confidence'] = 'medium';
  if (i.emg?.mdfSlope != null) {                    // each −0.1 %/s steeper than −0.3 %/s ≈ +3 y (fatigability)
    years += clamp((-0.3 - i.emg.mdfSlope) * 30, -10, 15); basis += ' + EMG fatigue'; conf = 'high';
  }
  years = clamp(years, 18, 95);
  return { ...base, years, delta: years - i.age, confidence: conf, basis,
    note: i.emg ? 'Muscle mass plus EMG-measured fatigue resistance.' : 'Muscle mass vs people your sex across ages. Strength training and 1.6 g/kg protein are the levers.' };
}

/** Compute all clocks plus a confidence-weighted overall. Pure, total, never throws. */
export function ageClocks(i: ClockInputs): AgeClocks {
  const clocks = [fitnessAge(i), autonomicAge(i), cardiacAge(i), muscleAge(i)];
  const w: Record<Clock['confidence'] & string, number> = { high: 1, medium: 0.6, low: 0.3 } as any;
  const used = clocks.filter((c) => c.years != null && c.confidence);
  let overall: AgeClocks['overall'] = null;
  // Never headline an overall age from one weak signal: need two clocks, or one at medium/high confidence.
  const trustworthy = used.length >= 2 || used.some((c) => c.confidence !== 'low');
  if (used.length && trustworthy && i.age != null) {
    const wsum = used.reduce((s, c) => s + w[c.confidence!], 0);
    const years = used.reduce((s, c) => s + c.years! * w[c.confidence!], 0) / wsum;
    const conf = used.some((c) => c.confidence === 'high') ? 'high' : used.length >= 2 ? 'medium' : 'low';
    overall = { years, delta: years - i.age, confidence: conf };
  }
  return { chrono: i.age ?? null, clocks, overall };
}
