// Device agreement on the night's score — a "signal, not verdict" check.
//
// When more than one device records the same sleep period (e.g. the Telomy patch AND a WHOOP), fuseNights()
// shows the most accurate one and keeps the others as `night.alts` (lib/sleepfuse.ts). Here we score each device
// the same way and report whether they agree. If they agree, that's quiet confidence in the number; if they
// disagree a lot, we say so plainly and name the device we're trusting (the ECG patch is the reference) — the
// person sees the spread instead of a single number presented as truth.
import { recoveryScore, sleepScore, type Night } from './wellness-core';
import type { SleepSource } from './sleepfuse';

const SHORT: Record<SleepSource, string> = {
  patch: 'Telomy patch', whoop: 'WHOOP', watch: 'Apple Watch', ring: 'Telomy ring', health: 'Phone health',
};
const shortLabel = (n: Night) => SHORT[(n.source ?? 'patch') as SleepSource] ?? n.sourceName ?? 'Device';

export type Agreement = {
  metric: 'recovery' | 'sleep';
  shown: { label: string; score: number };          // the device we display (highest priority)
  others: { label: string; score: number; delta: number }[];
  spread: number;                                    // max − min across all devices, in score points
  agree: boolean;                                    // within 8 points → agreement
  note: string;
};

/**
 * Compare the devices that recorded `night` on one score type. `history` is all nights (for the personal baseline,
 * exactly as the live score uses it). Returns null when only one device saw the night (nothing to compare) or the
 * chosen device can't be scored yet.
 */
export function nightAgreement(night: Night | undefined, history: Night[], metric: 'recovery' | 'sleep' = 'recovery'): Agreement | null {
  if (!night || !night.alts?.length) return null;
  const scoreOf = (n: Night): number | null =>
    metric === 'sleep' ? sleepScore(n, history).score : recoveryScore(n, history, sleepScore(n, history), []).score;
  const base = scoreOf(night);
  if (base == null) return null;
  const others = night.alts
    .map((a) => ({ label: shortLabel(a), score: scoreOf(a) }))
    .filter((o): o is { label: string; score: number } => o.score != null)
    .map((o) => ({ label: o.label, score: o.score, delta: o.score - base }));
  if (!others.length) return null;
  const all = [base, ...others.map((o) => o.score)];
  const spread = Math.max(...all) - Math.min(...all);
  const agree = spread <= 8;
  const word = metric === 'sleep' ? 'sleep score' : 'recovery';
  const list = others.map((o) => `${o.label} ${o.score}`).join(', ');
  const note = agree
    ? `Your devices agree on tonight's ${word} (within ${spread} point${spread === 1 ? '' : 's'}). We're showing your ${shortLabel(night)}, the most accurate.`
    : `Your devices disagree by ${spread} points on tonight's ${word} (${list}). We're showing your ${shortLabel(night)} — the ECG patch is the most accurate here — but treat the number as a range, not a verdict.`;
  return { metric, shown: { label: shortLabel(night), score: base }, others, spread, agree, note };
}
