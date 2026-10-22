// The single canonical registry of everything a person can log — one source of truth used by the Vault logger
// (log.tsx), the quick event logger (event.tsx) and the day timeline (daytimeline.tsx). Each kind has a stable
// key, a label, an SF Symbol, a timeline colour and a category, so a new kind shows up everywhere consistently.
import type { SFSymbol } from 'expo-symbols';

export type EventCat = 'intake' | 'behavior' | 'state' | 'therapy' | 'life';
export type EventKind = { k: string; label: string; icon: SFSymbol; color: string; cat: EventCat; hint: string };

export const EVENT_KINDS: EventKind[] = [
  // ── intake (food, drink, supplements) ──────────────────────────────────────────────
  { k: 'meal', label: 'Meal', icon: 'fork.knife', color: '#E39B68', cat: 'intake', hint: 'e.g. dal, rice, 2 rotis' },
  { k: 'snack', label: 'Snack', icon: 'carrot', color: '#E7B07E', cat: 'intake', hint: 'e.g. almonds, banana' },
  { k: 'late_meal', label: 'Late meal', icon: 'moon', color: '#C98A5A', cat: 'intake', hint: 'dinner after 9 pm' },
  { k: 'caffeine', label: 'Caffeine', icon: 'cup.and.saucer', color: '#C9A227', cat: 'intake', hint: 'e.g. espresso, 2 cups tea' },
  { k: 'caffeine_late', label: 'Late caffeine', icon: 'cup.and.saucer', color: '#B8922A', cat: 'intake', hint: 'coffee/tea after 3 pm' },
  { k: 'alcohol', label: 'Alcohol', icon: 'wineglass', color: '#C9607A', cat: 'intake', hint: 'e.g. 2 beers, 1 glass wine' },
  { k: 'water', label: 'Water', icon: 'drop', color: '#6F8CF0', cat: 'intake', hint: 'e.g. 500 ml' },
  { k: 'supplement', label: 'Supplement', icon: 'pills', color: '#5CC9A7', cat: 'intake', hint: 'e.g. magnesium 400 mg, glutathione' },
  { k: 'medication', label: 'Medication', icon: 'cross.case', color: '#49B390', cat: 'intake', hint: 'name and dose' },
  // ── behaviour ───────────────────────────────────────────────────────────────────────
  { k: 'smoking', label: 'Smoking', icon: 'smoke', color: '#8A9A94', cat: 'behavior', hint: 'e.g. 1 cigarette, vape' },
  { k: 'exercise', label: 'Exercise', icon: 'figure.run', color: '#FF9A5A', cat: 'behavior', hint: 'e.g. 30 min run' },
  { k: 'workout_hard', label: 'Hard workout', icon: 'figure.run', color: '#4FD08F', cat: 'behavior', hint: 'intervals, heavy lifting' },
  { k: 'nap', label: 'Nap', icon: 'bed.double', color: '#8EA8FF', cat: 'behavior', hint: 'e.g. 20 min' },
  // ── state (how you feel) ─────────────────────────────────────────────────────────────
  { k: 'stress', label: 'Stress', icon: 'bolt.heart', color: '#F2B94B', cat: 'state', hint: 'what happened' },
  { k: 'mood', label: 'How I feel', icon: 'face.smiling', color: '#F2C14E', cat: 'state', hint: 'good / low / anxious…' },
  { k: 'symptom', label: 'Symptom', icon: 'exclamationmark.bubble', color: '#FF6B57', cat: 'state', hint: 'e.g. headache, dizzy' },
  // ── therapy (centre / device sessions) ───────────────────────────────────────────────
  { k: 'sauna', label: 'Sauna', icon: 'flame', color: '#E0794B', cat: 'therapy', hint: 'e.g. 20 min, 80 °C' },
  { k: 'cold', label: 'Cold plunge / cryo', icon: 'snowflake', color: '#5BA8D6', cat: 'therapy', hint: 'ice bath / whole-body cryo' },
  { k: 'redlight', label: 'Red / NIR light', icon: 'light.max', color: '#E05B9A', cat: 'therapy', hint: 'photobiomodulation' },
  { k: 'vibroacoustic', label: 'Vibroacoustic', icon: 'waveform', color: '#A07BE0', cat: 'therapy', hint: 'sound/vibration therapy' },
  { k: 'hbot', label: 'HBOT', icon: 'lungs', color: '#4FD0C0', cat: 'therapy', hint: 'hyperbaric oxygen' },
  { k: 'pemf', label: 'PEMF', icon: 'dot.radiowaves.left.and.right', color: '#9E8CF0', cat: 'therapy', hint: 'pulsed electromagnetic field' },
  { k: 'hydrogen', label: 'Molecular hydrogen', icon: 'aqi.medium', color: '#78C8E0', cat: 'therapy', hint: 'H₂ inhalation / water' },
  // ── life ─────────────────────────────────────────────────────────────────────────────
  { k: 'travel', label: 'Travel', icon: 'airplane', color: '#7FB3D5', cat: 'life', hint: 'flight, time-zone change' },
  { k: 'life', label: 'Life event', icon: 'house', color: '#A5ABA8', cat: 'life', hint: 'anything notable' },
  { k: 'note', label: 'Note', icon: 'note.text', color: '#A5ABA8', cat: 'life', hint: 'remember this' },
  { k: 'custom', label: 'Custom', icon: 'pencil', color: '#A5ABA8', cat: 'life', hint: 'anything you want to remember' },
];

export const kindOf = (k: string) => EVENT_KINDS.find((x) => x.k === k) ?? EVENT_KINDS[EVENT_KINDS.length - 1];
/** Timeline colour for any kind (falls back through aliases, then neutral). */
export const EVENT_COLOR: Record<string, string> = Object.fromEntries(EVENT_KINDS.map((x) => [x.k, x.color]));
export const kindColor = (k: string) => EVENT_COLOR[k] ?? '#A5ABA8';
export const CATS: { cat: EventCat; label: string }[] = [
  { cat: 'intake', label: 'Food & drink' }, { cat: 'behavior', label: 'Activity' },
  { cat: 'state', label: 'How I feel' }, { cat: 'therapy', label: 'Therapy' }, { cat: 'life', label: 'Life' },
];

/** Device-LOCAL wall-clock as a naive ISO string (YYYY-MM-DDTHH:mm:ss). The app parses a tz-less ISO as local,
 * so sending this round-trips to the exact time the user picked — independent of the server's timezone (UTC). */
export function localIso(epochSec: number = Date.now() / 1000): string {
  const d = new Date(epochSec * 1000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
