// Telomy design tokens (UI Design System v1.0): Cloud Dancer / Ink, teal = science, copper = human.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useSyncExternalStore } from 'react';
import { Platform, useColorScheme } from 'react-native';

const light = {
  bg: '#F0EEE9',
  surface: '#FFFFFF',
  surfaceAlt: '#E8E5DE',
  text: '#1B1C1A',
  muted: '#6B6A64',
  faint: '#78766E',  // ≥ 4.5:1 on bg (HIG small-text contrast)
  border: '#D9D5CC',
  borderStrong: '#B9B4A8',
  teal: '#1F5C4E',
  tealSoft: '#DCE8E3',
  copper: '#A9643A',
  copperSoft: '#F3E6DB',
  success: '#2F7A55',
  successSoft: '#DDEEE4',
  warn: '#A86E12',
  warnSoft: '#F5EAD3',
  danger: '#A33A2A',
  dangerSoft: '#F6E0DB',
  graphite: '#5A5A58',
  overlay: 'rgba(20,20,18,0.35)',
  isDark: false,
  onAccent: '#FFFFFF',  // text/icons on teal, copper or other accent fills
};

// "Telomy Ink" (2026-10): dark-first, layered surfaces, colour reserved for data (WHOOP / Ultrahuman / Apple Fitness).
const dark: typeof light = {
  bg: '#090D0B',
  surface: '#121916',
  surfaceAlt: '#1A231F',
  text: '#F1F0EB',
  muted: '#9BA39F',
  faint: '#7F8984',  // ≥ 4.5:1 on bg
  border: '#212B26',
  borderStrong: '#34403A',
  teal: '#5CC9A7',
  tealSoft: '#14302A',
  copper: '#E39B68',
  copperSoft: '#352419',
  success: '#4FD08F',
  successSoft: '#123325',
  warn: '#F2B94B',
  warnSoft: '#3A2E14',
  danger: '#FF6B57',
  dangerSoft: '#3D1C17',
  graphite: '#A5ABA8',
  overlay: 'rgba(0,0,0,0.6)',
  isDark: true,
  onAccent: '#07110D',
};

export type Palette = typeof light;

// Appearance: Telomy is dark-first. Profile → Appearance can switch to Light or follow the system.
export type Appearance = 'dark' | 'light' | 'system';
const APPEARANCE_KEY = 'telomy.appearance';
let appearance: Appearance = 'dark';
const appearanceListeners = new Set<() => void>();
AsyncStorage.getItem(APPEARANCE_KEY).then((v) => {
  if (v === 'dark' || v === 'light' || v === 'system') { appearance = v; appearanceListeners.forEach((l) => l()); }
}).catch(() => {});
export function setAppearance(a: Appearance) {
  appearance = a; appearanceListeners.forEach((l) => l());
  AsyncStorage.setItem(APPEARANCE_KEY, a).catch(() => {});
}
export function useAppearance(): Appearance {
  return useSyncExternalStore((cb) => { appearanceListeners.add(cb); return () => appearanceListeners.delete(cb); }, () => appearance);
}
/** The scheme in effect ('dark' | 'light'). Use instead of useColorScheme(). */
export function useScheme(): 'dark' | 'light' {
  const sys = useColorScheme();
  const a = useAppearance();
  return a === 'system' ? (sys === 'dark' ? 'dark' : 'light') : a;
}

export function usePalette(): Palette {
  return useScheme() === 'dark' ? dark : light;
}

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40 };
export const radius = { sm: 8, md: 12, lg: 16, xl: 22, pill: 999 };

/** Data colours — one hue per signal, identical in every tile, icon and chart, so a colour *means* something
 *  (heart is always coral, SpO₂ always blue). UI chrome stays neutral; colour is reserved for data. */
export const data = {
  heart: '#FF6B57', hrv: '#4FD08F', spo2: '#5B8DEF', temp: '#E0894F', breath: '#6FC7D6', activity: '#2F8F6B',
  stress: '#C98A1B', sleep: '#8EA8FF', deep: '#5468D4', rem: '#B58CFF', recovery: '#4FD08F', age: '#7A6FF0',
  glucose: '#E06C9F', muscle: '#D9A441',
} as const;

/** Text and lines on the always-dark "ink" surfaces (Home hero, detail heroes, live ECG) — whatever the app theme.
 *  Replaces 16 ad-hoc white transparencies with six roles. */
export const onInk = {
  primary: 'rgba(255,255,255,0.88)', secondary: 'rgba(255,255,255,0.72)', muted: 'rgba(255,255,255,0.6)',
  faint: 'rgba(255,255,255,0.4)', track: 'rgba(255,255,255,0.12)', hairline: 'rgba(255,255,255,0.08)',
} as const;

/** Depth: the warm shadow tint for light-mode cards, and the near-black stage behind 3D / full-bleed media. */
export const depth = { shadow: '#2B2418', stage: '#06090A' } as const;

/** The data colour for a signal, from its id or label ("rhr", "Deep sleep", "spo2"…); undefined = use the accent. */
export function signalColor(id?: string | null): string | undefined {
  const k = (id ?? '').toLowerCase();
  if (/rem/.test(k)) return data.rem;
  if (/deep/.test(k)) return data.deep;
  if (/sleep/.test(k)) return data.sleep;
  if (/hrv|rmssd|sdnn/.test(k)) return data.hrv;
  if (/spo2|oxygen/.test(k)) return data.spo2;
  if (/temp/.test(k)) return data.temp;
  if (/resp|breath/.test(k)) return data.breath;
  if (/step|walk|active|vo2|strain|fitness/.test(k)) return data.activity;
  if (/stress/.test(k)) return data.stress;
  if (/glucose|hba1c|sugar/.test(k)) return data.glucose;
  if (/muscle|lean|almi/.test(k)) return data.muscle;
  if (/rhr|heart|pulse|hr\b|bpm/.test(k)) return data.heart;
  return undefined;
}

/** Type scale — a 1.2 (minor-third) ramp from 13 pt. Every size in the app comes from here; 22 ad-hoc sizes was the
 *  single biggest source of the "generated" look. Display sizes use Fraunces, everything else Inter. */
export const type = { micro: 11, caption: 13, body: 15, lead: 17, title: 20, h2: 24, h1: 30, hero: 40, display: 56, giant: 76 } as const;

/** Motion — never linear. ease-out for things arriving, ease-in-out for things moving, springs for direct
 *  manipulation (press, drag, toggles). Durations scale with distance travelled. */
export const motion = {
  fast: 160, base: 240, slow: 360,
  easeOut: [0.22, 1, 0.36, 1] as const,      // "expo out": quick arrival, soft landing
  easeInOut: [0.65, 0, 0.35, 1] as const,
  spring: { damping: 18, stiffness: 220, mass: 1 },     // taps, toggles — crisp, no wobble
  springSoft: { damping: 22, stiffness: 140, mass: 1 }, // sheets, cards settling
} as const;

// Typography (UI Design System v1.0): Inter for UI, Fraunces as the display serif.
// The Telomy wordmark typeface is used only in the logo, splash and boot animation.
// --- Direction 5: Telomy brand — TelomySans headlines, Geist body, Geist Mono numerals ---
// TelomySans is a 70-glyph brand/display face (letters + digits + basic punctuation, no ₹/µ/arrows), so it carries
// headlines only; Geist handles body/UI and Geist Mono the data, where the missing glyphs actually appear.
export const fonts = {
  display: 'TelomySans_Bold',
  displayLight: 'TelomySans_Regular',
  light: 'Geist_300Light',
  body: 'Geist_400Regular',
  medium: 'Geist_500Medium',
  bold: 'Geist_600SemiBold',
  mono: 'GeistMono_500Medium',
};

export function ff(weight?: string | number) {
  const w = Number(weight ?? 400);
  return w >= 600 ? fonts.bold : w >= 500 ? fonts.medium : w <= 300 ? fonts.light : fonts.body;
}

export function statusColor(p: Palette, status?: string | null) {
  switch (status) {
    case 'optimal':
    case 'typical':
    case 'absent':
    case 'signed':
    case 'helpful':
      return { fg: p.success, bg: p.successSoft };
    case 'in_range':
    case 'awaiting':
    case 'info':
      return { fg: p.warn, bg: p.warnSoft };
    case 'out_of_range':
    case 'variant':
    case 'detected':
    case 'rejected':
    case 'harmful':
      return { fg: p.danger, bg: p.dangerSoft };
    default:
      return { fg: p.muted, bg: p.surfaceAlt };
  }
}

export const statusLabel: Record<string, string> = {
  optimal: 'Optimal',
  in_range: 'In range',
  out_of_range: 'Out of range',
  variant: 'Risk variant',
  typical: 'Typical',
  detected: 'Detected',
  absent: 'Not detected',
  info: 'Info',
  awaiting: 'Awaiting clinician',
  signed: 'Signed off',
  rejected: 'Rejected',
  none: 'Not reviewed',
};
