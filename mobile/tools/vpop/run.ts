// Run the virtual population through the real Telomy sleep/recovery engines and report where they break.
// usage: TZ=Asia/Kolkata npx tsx tools/vpop/run.ts [people=5000] [nights=14] [--legacy-bug]
// Pre-registered (validation rule 1): domain = every simulated night; primary metrics = TST MAE (min), onset/offset
// error (min), fragments per night (target 1.00), missed nights (target 0); stage minutes as signed bias.
import { writeFileSync } from 'fs';
import { makePerson, runPerson, setSeed, type NightResult } from './sim';

const N = Number(process.argv[2] ?? 5000), NIGHTS = Number(process.argv[3] ?? 14), legacy = process.argv.includes('--legacy-bug');
setSeed(20261019);
const rows: NightResult[] = [];
const t0 = Date.now();
for (let i = 0; i < N; i++) {
  rows.push(...runPerson(makePerson(i), NIGHTS, legacy).res);
  if ((i + 1) % 500 === 0) process.stderr.write(`${i + 1}/${N} people · ${((Date.now() - t0) / 1000).toFixed(0)} s\n`);
}

const q = (xs: number[], p: number) => { const s = [...xs].sort((a, b) => a - b); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : NaN; };
const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : NaN);
function summary(name: string, rs: NightResult[]) {
  const got = rs.filter((r) => r.estTst != null);
  const err = got.map((r) => r.estTst! - r.trueTst);
  const deep = got.filter((r) => r.estDeep != null).map((r) => r.estDeep! - r.trueDeep);
  const rem = got.filter((r) => r.estRem != null).map((r) => r.estRem! - r.trueRem);
  const on = got.map((r) => r.onsetErrMin!).filter(Number.isFinite), off = got.map((r) => r.offsetErrMin!).filter(Number.isFinite);
  return {
    group: name, nights: rs.length, missed: +(100 * (1 - got.length / Math.max(1, rs.length))).toFixed(1),
    tstBias: +mean(err).toFixed(1), tstMAE: +mean(err.map(Math.abs)).toFixed(1), tstP90: +q(err.map(Math.abs), 0.9).toFixed(0),
    onsetMAE: +mean(on.map(Math.abs)).toFixed(1), offsetMAE: +mean(off.map(Math.abs)).toFixed(1),
    fragmented: +(100 * got.filter((r) => r.fragments > 1).length / Math.max(1, got.length)).toFixed(1),
    deepBias: deep.length ? +mean(deep).toFixed(1) : null, remBias: rem.length ? +mean(rem).toFixed(1) : null,
  };
}
const groups: [string, (r: NightResult) => boolean][] = [
  ['ALL', () => true],
  ...[...new Set(rows.map((r) => r.devices))].map((d) => [`devices=${d}`, (r: NightResult) => r.devices === d] as [string, (r: NightResult) => boolean]),
  ['age<30', (r) => r.age < 30], ['age30-50', (r) => r.age >= 30 && r.age < 50], ['age50-65', (r) => r.age >= 50 && r.age < 65], ['age65+', (r) => r.age >= 65],
  ['insomnia', (r) => r.insomnia], ['sleep apnoea', (r) => r.apnea], ['shift work', (r) => r.shift],
  ['patch stopped early', (r) => r.patchStopped],
];
const table = groups.map(([n, f]) => summary(n, rows.filter(f)));
console.table(table);

// recovery sanity: does the score move with the true overnight HRV deviation? (it should, positively)
const rec = rows.filter((r) => r.recovery != null);
const xs = rec.map((r) => r.trueHrvZ), ys = rec.map((r) => r.recovery!);
const mx = mean(xs), my = mean(ys);
const rr = xs.reduce((a, x, i) => a + (x - mx) * (ys[i] - my), 0) / Math.sqrt(xs.reduce((a, x) => a + (x - mx) ** 2, 0) * ys.reduce((a, y) => a + (y - my) ** 2, 0));
console.log(`recovery vs true HRV deviation: r ${rr.toFixed(2)} over ${rec.length} nights · ${(Date.now() - t0) / 1000} s total`);
writeFileSync(`tools/vpop/report-${legacy ? 'legacy' : 'current'}.json`, JSON.stringify({ people: N, nights: NIGHTS, legacy, table, recoveryR: rr }, null, 1));
