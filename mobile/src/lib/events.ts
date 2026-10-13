// Flexible user events: anything that can change physiology, logged with its own time.
import type { SFSymbol } from 'expo-symbols';

export type EventKind = { k: string; label: string; icon: SFSymbol; color: string; hint: string };

export const EVENT_KINDS: EventKind[] = [
  { k: 'meal', label: 'Meal', icon: 'fork.knife', color: '#E39B68', hint: 'e.g. dal, rice, 2 rotis' },
  { k: 'snack', label: 'Snack', icon: 'carrot', color: '#E39B68', hint: 'e.g. almonds, banana' },
  { k: 'caffeine', label: 'Caffeine', icon: 'cup.and.saucer', color: '#B7865A', hint: 'e.g. espresso, 2 cups tea' },
  { k: 'alcohol', label: 'Alcohol', icon: 'wineglass', color: '#C9607A', hint: 'e.g. 2 beers, 1 glass wine' },
  { k: 'smoking', label: 'Smoking', icon: 'smoke', color: '#9AA29D', hint: 'e.g. 1 cigarette, vape' },
  { k: 'water', label: 'Water', icon: 'drop', color: '#6F8CF0', hint: 'e.g. 500 ml' },
  { k: 'supplement', label: 'Supplement', icon: 'pills', color: '#5CC9A7', hint: 'e.g. magnesium 400 mg' },
  { k: 'medication', label: 'Medication', icon: 'cross.case', color: '#5CC9A7', hint: 'name and dose' },
  { k: 'exercise', label: 'Exercise', icon: 'figure.run', color: '#FF9A5A', hint: 'e.g. 30 min run' },
  { k: 'stress', label: 'Stress', icon: 'bolt.heart', color: '#F2B94B', hint: 'what happened' },
  { k: 'nap', label: 'Nap', icon: 'bed.double', color: '#8EA8FF', hint: 'e.g. 20 min' },
  { k: 'symptom', label: 'Symptom', icon: 'exclamationmark.bubble', color: '#FF6B57', hint: 'e.g. headache, dizzy' },
  { k: 'custom', label: 'Custom', icon: 'pencil', color: '#A5ABA8', hint: 'anything you want to remember' },
];

export const kindOf = (k: string) => EVENT_KINDS.find((x) => x.k === k) ?? EVENT_KINDS[EVENT_KINDS.length - 1];
