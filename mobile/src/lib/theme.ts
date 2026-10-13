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
  faint: '#9A988F',
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
  faint: '#69726D',
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

// Typography (UI Design System v1.0): Inter for UI, Fraunces as the display serif.
// The Telomy wordmark typeface is used only in the logo, splash and boot animation.
export const fonts = {
  display: 'Fraunces_500Medium',
  displayLight: 'Fraunces_400Regular',
  light: 'Inter_300Light',
  body: 'Inter_400Regular',
  medium: 'Inter_500Medium',
  bold: 'Inter_600SemiBold',
  mono: Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' }),
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
