// Camera-PPG → HRV pipeline, written to be portable to the app (lib/ppg.ts). Pure JS, no deps.
// Pipeline: pick the pulsatile channel → resample to uniform fs → band-limit (baseline removal + light smoothing)
// → adaptive peak detection with a refractory period → inter-beat intervals → artefact rejection → HRV metrics.
// Validated offline against the Welltory PPG dataset (phone-camera R/G/B + Polar-H10 RR ground truth).

export const FS = 100; // Hz, uniform resample target — upsampling from ~30 fps gives sub-sample peak timing
// (parabolic-refined on the smooth band-limited curve), which is what RMSSD needs; 30 Hz quantisation inflates it.

/** Linear-resample an irregular (t_ms, v) series onto a uniform grid at fs Hz. */
export function resample(tms, v, fs = FS) {
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

const movingAvg = (x, w) => {
  const n = x.length, out = new Float64Array(n); let acc = 0;
  for (let i = 0; i < n; i++) {
    acc += x[i];
    if (i >= w) acc -= x[i - w];
    out[i] = acc / Math.min(i + 1, w);
  }
  // centre the window
  const half = Math.floor(w / 2), c = new Float64Array(n);
  for (let i = 0; i < n; i++) c[i] = out[Math.min(n - 1, i + half)];
  return c;
};

/** Band-limit to the pulse band: remove baseline wander (subtract a ~0.75 s moving average) then smooth enough to
 *  suppress the dicrotic notch (~0.14 s), which otherwise causes a second peak per beat. */
export function bandlimit(x, fs = FS) {
  const base = movingAvg(x, Math.round(0.75 * fs));
  const hp = x.map((v, i) => v - base[i]);
  return movingAvg(hp, Math.max(2, Math.round(0.14 * fs)));
}

/** Adaptive systolic-peak detection with a refractory period (max ~210 bpm). */
export function detectPeaks(x, fs = FS) {
  const n = x.length;
  // normalise by a rolling RMS so the threshold adapts to amplitude drift
  const win = Math.round(2 * fs);
  const rms = new Float64Array(n);
  { let acc = 0; for (let i = 0; i < n; i++) { acc += x[i] * x[i]; if (i >= win) acc -= x[i - win] * x[i - win]; rms[i] = Math.sqrt(acc / Math.min(i + 1, win)) || 1e-9; } }
  const refractory = Math.round(0.30 * fs); // 200 bpm ceiling
  const peaks = [];
  let last = -refractory;
  for (let i = 1; i < n - 1; i++) {
    if (x[i] > 0.45 * rms[i] && x[i] >= x[i - 1] && x[i] > x[i + 1] && i - last >= refractory) {
      // parabolic refine
      const d = x[i - 1] - 2 * x[i] + x[i + 1];
      const shift = d !== 0 ? (0.5 * (x[i - 1] - x[i + 1])) / d : 0;
      peaks.push((i + Math.max(-0.5, Math.min(0.5, shift))) / fs); // seconds
      last = i;
    }
  }
  return peaks; // peak times in seconds
}

const median = (arr) => { if (!arr.length) return 0; const s = [...arr].sort((a, b) => a - b); const h = s.length >> 1; return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2; };

/** Inter-beat intervals (ms) from peak times, each tagged valid/invalid against a local median. Crucially the
 *  sequence and adjacency are preserved so RMSSD can use only successive differences between truly adjacent
 *  normal beats — dropping a beat must NOT create a spurious huge successive difference. */
export function ibisFrom(peaksSec) {
  const ibi = [];
  for (let i = 1; i < peaksSec.length; i++) {
    const d = (peaksSec[i] - peaksSec[i - 1]) * 1000;
    ibi.push({ d, ok: d >= 300 && d <= 1500 });
  }
  for (let i = 0; i < ibi.length; i++) {
    const lo = Math.max(0, i - 5), hi = Math.min(ibi.length, i + 6);
    const m = median(ibi.slice(lo, hi).filter((x) => x.ok).map((x) => x.d));
    if (!m || Math.abs(ibi[i].d - m) / m > 0.2) ibi[i].ok = false; // >20% from local normal = artefact
  }
  return ibi;
}

/** Time-domain HRV from the tagged IBI sequence. Mean HR uses the robust median of normal beats; RMSSD/pNN50 use
 *  successive differences only where BOTH beats are normal AND adjacent (i.e. no artefact between them). */
export function hrv(ibiTagged) {
  // accept a plain number[] (e.g. the Polar reference) or the tagged sequence from ibisFrom
  const seq = typeof ibiTagged[0] === 'number' ? ibiTagged.map((d) => ({ d, ok: d >= 300 && d <= 1500 })) : ibiTagged;
  const nn = seq.filter((x) => x.ok).map((x) => x.d);
  if (nn.length < 5) return null;
  const med = median(nn);
  const mean = nn.reduce((a, b) => a + b, 0) / nn.length;
  const sdnn = Math.sqrt(nn.reduce((a, b) => a + (b - mean) ** 2, 0) / (nn.length - 1));
  let ss = 0, pairs = 0, nn50 = 0;
  for (let i = 1; i < seq.length; i++) {
    if (seq[i].ok && seq[i - 1].ok) { const dd = seq[i].d - seq[i - 1].d; ss += dd * dd; pairs++; if (Math.abs(dd) > 50) nn50++; }
  }
  const rmssd = pairs ? Math.sqrt(ss / pairs) : NaN;
  return { meanHr: 60000 / med, meanIbi: med, sdnn, rmssd, pnn50: pairs ? (100 * nn50) / pairs : 0, n: nn.length };
}

/** Full pipeline from an (t_ms, red[]) camera PPG recording → HRV + a quality score 0–1. */
export function analysePpg(tms, red, fs = FS) {
  const rs = resample(tms, red, fs);
  const bl = bandlimit(rs, fs);
  const peaks = detectPeaks(bl, fs);
  const ibi = ibisFrom(peaks);
  const h = hrv(ibi);
  const durSec = (tms[tms.length - 1] - tms[0]) / 1000;
  const expectedBeats = h ? (durSec * h.meanHr) / 60 : 0;
  // quality = share of expected beats we recovered as clean, normal intervals
  const quality = h && expectedBeats > 0 ? Math.max(0, Math.min(1, h.n / expectedBeats)) : 0;
  return { ...(h || {}), quality: Math.round(quality * 100) / 100, durSec: Math.round(durSec) };
}
