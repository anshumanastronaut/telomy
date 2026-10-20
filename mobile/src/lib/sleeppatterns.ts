// Normal sleep architecture, mined from expert-scored PSG (HMC sleep staging database, PhysioNet, CC BY 4.0;
// 151 nights, 30-s epochs; ~/telomy-lab/sleepstage/mine_patterns.py → sleep_patterns.json). Aggregate statistics only.
// Used to sanity-check any staged night (patch, WHOOP, Watch, ring firmware): a night that breaks several of these
// patterns keeps its total sleep and timing, but its stage minutes are shown as uncertain with the reason.
import type { Night } from './wellness-core';

export const NORMS = {
  sleepLatencyMin: { p10: 2.5, p50: 7.5, p90: 30.5 },
  remLatencyFromOnsetMin: { p10: 45, p50: 88.8, p90: 225.6 },     // first REM, minutes after sleep onset
  firstDeepFromOnsetMin: { p10: 9, p50: 22, p90: 76.4 },
  remCycleMin: { p10: 63.5, p50: 101.5, p90: 146.5 },             // REM-episode onset to the next
  remEpisodesPerNight: { p10: 2, p50: 4, p90: 5 },
  awakeningsOver1Min: { p10: 4, p50: 10, p90: 20 },
  // share of each stage by hour since sleep onset: wake, light, deep, REM
  mixByHour: [[0.17, 0.45, 0.35, 0.03], [0.12, 0.46, 0.27, 0.15], [0.14, 0.48, 0.25, 0.13], [0.13, 0.47, 0.22, 0.19],
    [0.13, 0.52, 0.16, 0.19], [0.14, 0.55, 0.12, 0.2], [0.15, 0.54, 0.1, 0.22], [0.12, 0.54, 0.09, 0.25]],
};

export type ArchitectureCheck = { ok: boolean; flags: string[] };

/** Flags patterns outside the 10th–90th percentile band of normal PSG nights. ≥ 2 flags → stages "uncertain". */
export function checkArchitecture(n: Night): ArchitectureCheck | null {
  const st = n.stages;
  if (!st?.length) return null;
  const onset = st.findIndex((s) => s > 0);
  if (onset < 0) return null;
  const s = st.slice(onset);
  const minsTo = (c: number) => { const i = s.indexOf(c); return i < 0 ? null : i / 2; };
  const flags: string[] = [];
  const rem0 = minsTo(3), deep0 = minsTo(2);
  if (rem0 != null && rem0 < NORMS.remLatencyFromOnsetMin.p10 * 0.5) flags.push(`REM ${Math.round(rem0)} min after falling asleep (usually 60–130 min)`);
  if (s.length > 180 && (deep0 == null || deep0 > 90)) flags.push('no deep sleep in the first 90 minutes (usually within 10–40 min)');
  const third = Math.floor(s.length / 3);
  if (third > 60) {
    const deepIn = (a: number[]) => a.filter((x) => x === 2).length / Math.max(1, a.length);
    if (deepIn(s.slice(-third)) > deepIn(s.slice(0, third)) + 0.05) flags.push('more deep sleep late in the night than early (normally the reverse)');
  }
  const eps: number[] = [];
  s.forEach((x, i) => { if (x === 3 && (!eps.length || i - eps[eps.length - 1] > 30)) eps.push(i); });
  if (s.length > 720 && eps.length === 0) flags.push('no REM in 6+ hours of sleep');
  const cyc = eps.slice(1).map((e, i) => (e - eps[i]) / 2);
  if (cyc.length >= 2) {
    const short = cyc.filter((c) => c < 40).length;
    if (short >= 2) flags.push('REM recurring every < 40 min (cycles are usually 80–120 min)');
  }
  return { ok: flags.length < 2, flags };
}
