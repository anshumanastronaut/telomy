// Camera-PPG → heart rate + HRV + a stress estimate. The caller (the Measure screen) supplies per-frame samples
// captured from the back camera with the torch on and a fingertip over the lens: for each frame, the average RED
// channel value (the pulsatile channel in transmissive finger PPG) and the frame timestamp in ms.
//
// Validated offline against the Welltory PPG dataset (phone-camera R/G/B + Polar-H10 RR ground truth), 21 subjects:
//   accepted reads (quality ≥ 0.8): HR MAE 0.37 bpm, 16/16 within ±3 bpm; RMSSD MAE ≈20 ms (directional).
// HR is reliable; HRV/RMSSD is an estimate, and low-quality reads are rejected rather than shown.
// See research/ppg-validation/ for the pipeline, harness and numbers.

export const FS = 100; // Hz, uniform resample target (upsampling from ~30 fps gives sub-sample peak timing for RMSSD)

export type HrvResult = {
  hr: number; meanIbi: number; sdnn: number; rmssd: number; pnn50: number;
  n: number; quality: number; durSec: number; stress: number | null;
};

function resample(tms: number[], v: number[], fs = FS): Float64Array {
  const t0 = tms[0], t1 = tms[tms.length - 1];
  const n = Math.max(2, Math.floor(((t1 - t0) / 1000) * fs));
  const out = new Float64Array(n);
  let j = 0;
  for (let i = 0; i < n; i++) {
    const t = t0 + (i * 1000) / fs;
    while (j < tms.length - 2 && tms[j + 1] < t) j++;
    const a = tms[j], b = tms[j + 1], f = b > a ? (t - a) / (b - a) : 0;
    out[i] = v[j] + f * (v[j + 1] - v[j]);
  }
  return out;
}

function movingAvg(x: ArrayLike<number>, w: number): Float64Array {
  const n = x.length, out = new Float64Array(n); let acc = 0;
  for (let i = 0; i < n; i++) { acc += x[i]; if (i >= w) acc -= x[i - w]; out[i] = acc / Math.min(i + 1, w); }
  const half = Math.floor(w / 2), c = new Float64Array(n);
  for (let i = 0; i < n; i++) c[i] = out[Math.min(n - 1, i + half)];
  return c;
}

/** Baseline removal (~0.75 s) + smoothing (~0.14 s) to suppress the dicrotic notch (a double-peak source). */
function bandlimit(x: Float64Array, fs = FS): Float64Array {
  const base = movingAvg(x, Math.round(0.75 * fs));
  const hp = new Float64Array(x.length);
  for (let i = 0; i < x.length; i++) hp[i] = x[i] - base[i];
  return movingAvg(hp, Math.max(2, Math.round(0.14 * fs)));
}

/** Adaptive systolic-peak detection with a 0.30 s refractory period and parabolic sub-sample refinement. */
function detectPeaks(x: Float64Array, fs = FS): number[] {
  const n = x.length, win = Math.round(2 * fs), rms = new Float64Array(n);
  let acc = 0;
  for (let i = 0; i < n; i++) { acc += x[i] * x[i]; if (i >= win) acc -= x[i - win] * x[i - win]; rms[i] = Math.sqrt(acc / Math.min(i + 1, win)) || 1e-9; }
  const refractory = Math.round(0.3 * fs), peaks: number[] = [];
  let last = -refractory;
  for (let i = 1; i < n - 1; i++) {
    if (x[i] > 0.45 * rms[i] && x[i] >= x[i - 1] && x[i] > x[i + 1] && i - last >= refractory) {
      const d = x[i - 1] - 2 * x[i] + x[i + 1];
      const shift = d !== 0 ? (0.5 * (x[i - 1] - x[i + 1])) / d : 0;
      peaks.push((i + Math.max(-0.5, Math.min(0.5, shift))) / fs);
      last = i;
    }
  }
  return peaks;
}

const median = (arr: number[]): number => {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b), h = s.length >> 1;
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
};

type Beat = { d: number; ok: boolean };
/** IBIs (ms) tagged valid/invalid vs a local median, with sequence/adjacency preserved so RMSSD uses only
 *  successive differences between truly adjacent normal beats (dropping a beat must not create a false jump). */
function ibisFrom(peaksSec: number[]): Beat[] {
  const ibi: Beat[] = [];
  for (let i = 1; i < peaksSec.length; i++) { const d = (peaksSec[i] - peaksSec[i - 1]) * 1000; ibi.push({ d, ok: d >= 300 && d <= 1500 }); }
  for (let i = 0; i < ibi.length; i++) {
    const lo = Math.max(0, i - 5), hi = Math.min(ibi.length, i + 6);
    const m = median(ibi.slice(lo, hi).filter((x) => x.ok).map((x) => x.d));
    if (!m || Math.abs(ibi[i].d - m) / m > 0.2) ibi[i].ok = false;
  }
  return ibi;
}

function hrvFrom(seq: Beat[]): Omit<HrvResult, 'quality' | 'durSec' | 'stress'> | null {
  const nn = seq.filter((x) => x.ok).map((x) => x.d);
  if (nn.length < 5) return null;
  const med = median(nn), mean = nn.reduce((a, b) => a + b, 0) / nn.length;
  const sdnn = Math.sqrt(nn.reduce((a, b) => a + (b - mean) ** 2, 0) / (nn.length - 1));
  let ss = 0, pairs = 0, nn50 = 0;
  for (let i = 1; i < seq.length; i++) if (seq[i].ok && seq[i - 1].ok) { const dd = seq[i].d - seq[i - 1].d; ss += dd * dd; pairs++; if (Math.abs(dd) > 50) nn50++; }
  return { hr: 60000 / med, meanIbi: med, sdnn, rmssd: pairs ? Math.sqrt(ss / pairs) : NaN, pnn50: pairs ? (100 * nn50) / pairs : 0, n: nn.length };
}

/** A normative 0–100 stress estimate from HR and RMSSD. Higher heart rate and lower HRV read as more stress. Until
 *  the app has the person's own calm baseline this is normative; it sharpens as their baseline builds. */
function stressFromHrv(hr: number, rmssd: number): number {
  const s = 50 + (hr - 65) * 1.1 - (rmssd - 40) * 0.7;
  return Math.max(1, Math.min(100, Math.round(s)));
}

/** Full pipeline: per-frame red-channel averages + timestamps (ms) → HR, HRV and a stress estimate + quality 0–1. */
export function analysePpg(tms: number[], red: number[], fs = FS): HrvResult | null {
  if (tms.length < fs || tms[tms.length - 1] - tms[0] < 20000) return null; // need ~20 s+
  const bl = bandlimit(resample(tms, red, fs), fs);
  const h = hrvFrom(ibisFrom(detectPeaks(bl, fs)));
  const durSec = (tms[tms.length - 1] - tms[0]) / 1000;
  if (!h || !h.hr) return null;
  const expected = (durSec * h.hr) / 60;
  const quality = Math.max(0, Math.min(1, h.n / expected));
  return { ...h, durSec: Math.round(durSec), quality: Math.round(quality * 100) / 100, stress: Number.isFinite(h.rmssd) ? stressFromHrv(h.hr, h.rmssd) : null };
}
