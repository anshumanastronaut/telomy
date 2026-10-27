// Validate the camera-PPG → HRV pipeline against the Welltory dataset (phone-camera R/G/B vs Polar-H10 RR).
import fs from 'node:fs';
import path from 'node:path';
import { analysePpg, hrv } from './ppg_hrv.mjs';

const DATA = path.join(path.dirname(new URL(import.meta.url).pathname), 'welltory-ppg-dataset', 'data');

function loadPpg(file) {
  const lines = fs.readFileSync(file, 'utf8').trim().split('\n');
  const t = [], r = [], g = [], b = [];
  for (let i = 1; i < lines.length; i++) {
    const [tt, rr, gg, bb] = lines[i].split(',').map(Number);
    if (Number.isFinite(tt)) { t.push(tt); r.push(rr); g.push(gg); b.push(bb); }
  }
  return { t, r, g, b };
}
function loadRr(file) { return fs.readFileSync(file, 'utf8').trim().split(/\s+/).map(Number).filter((x) => x >= 300 && x <= 1500); }

const subs = fs.readdirSync(DATA).filter((d) => d.startsWith('subject_')).sort();
let hrErrs = [], rmssdErrs = [], rmssdPct = [], good = 0;
console.log('subj   | refHR  ppgHR  dHR | refRMSSD ppgRMSSD dRMSSD | qual');
console.log('-------|-------------------|--------------------------|-----');
for (const s of subs) {
  const dir = path.join(DATA, s);
  const { t, r, g } = loadPpg(path.join(dir, 'PPG.csv'));
  // the pulsatile channel is whichever has real variance (red here; green ~0)
  const rv = r.reduce((a, b) => a + b, 0) / r.length, gv = g.reduce((a, b) => a + b, 0) / g.length;
  const chan = Math.abs(rv) > Math.abs(gv) ? r : g;
  const ref = hrv(loadRr(path.join(dir, 'RR.txt')));
  const ppg = analysePpg(t, chan);
  if (!ref || !ppg.meanHr) { console.log(`${s} | no result`); continue; }
  const dHr = ppg.meanHr - ref.meanHr, dR = ppg.rmssd - ref.rmssd;
  hrErrs.push(Math.abs(dHr)); rmssdErrs.push(Math.abs(dR)); rmssdPct.push(Math.abs(dR) / ref.rmssd);
  if (Math.abs(dHr) <= 3) good++;
  console.log(`${s} | ${ref.meanHr.toFixed(1).padStart(5)} ${ppg.meanHr.toFixed(1).padStart(5)} ${dHr.toFixed(1).padStart(5)} | ${ref.rmssd.toFixed(0).padStart(7)} ${ppg.rmssd.toFixed(0).padStart(8)} ${dR.toFixed(0).padStart(6)} | ${ppg.quality}`);
}
const mean = (a) => (a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
console.log('\n=== all readings (n=' + hrErrs.length + ') ===');
console.log('HR    MAE: ' + mean(hrErrs).toFixed(2) + ' bpm   | within ±3 bpm: ' + good + '/' + hrErrs.length);
console.log('RMSSD MAE: ' + mean(rmssdErrs).toFixed(1) + ' ms    | RMSSD MAPE: ' + (100 * mean(rmssdPct)).toFixed(1) + '%');
// what we'd actually accept: gate on quality
const G = 0.8;
const gHr = [], gR = [], gP = []; let gGood = 0, nAcc = 0, nRej = 0;
for (const s of subs) {
  const dir = path.join(DATA, s);
  const { t, r, g } = loadPpg(path.join(dir, 'PPG.csv'));
  const rv = r.reduce((a, b) => a + b, 0) / r.length, gv = g.reduce((a, b) => a + b, 0) / g.length;
  const ref = hrv(loadRr(path.join(dir, 'RR.txt'))), ppg = analysePpg(t, Math.abs(rv) > Math.abs(gv) ? r : g);
  if (!ref || !ppg.meanHr) continue;
  if (ppg.quality < G) { nRej++; continue; }
  nAcc++; gHr.push(Math.abs(ppg.meanHr - ref.meanHr)); gR.push(Math.abs(ppg.rmssd - ref.rmssd)); gP.push(Math.abs(ppg.rmssd - ref.rmssd) / ref.rmssd);
  if (Math.abs(ppg.meanHr - ref.meanHr) <= 3) gGood++;
}
console.log('\n=== accepted only (quality ≥ ' + G + '): ' + nAcc + ' accepted, ' + nRej + ' rejected ===');
console.log('HR    MAE: ' + mean(gHr).toFixed(2) + ' bpm   | within ±3 bpm: ' + gGood + '/' + nAcc);
console.log('RMSSD MAE: ' + mean(gR).toFixed(1) + ' ms    | RMSSD MAPE: ' + (100 * mean(gP)).toFixed(1) + '%');
