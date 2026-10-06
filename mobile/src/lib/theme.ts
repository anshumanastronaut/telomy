// Telomy design tokens (UI Design System v1.0): Cloud Dancer / Ink, teal = science, copper = human.
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
};

const dark: typeof light = {
  bg: '#121413',
  surface: '#1B1E1C',
  surfaceAlt: '#242825',
  text: '#ECEAE4',
  muted: '#A19F97',
  faint: '#77756E',
  border: '#2E332F',
  borderStrong: '#454B46',
  teal: '#6FBBA4',
  tealSoft: '#1E3A33',
  copper: '#D69466',
  copperSoft: '#3A2A20',
  success: '#6CC394',
  successSoft: '#1E3528',
  warn: '#E0A84A',
  warnSoft: '#3A2F1A',
  danger: '#E07B69',
  dangerSoft: '#3E2320',
  graphite: '#A3A3A0',
  overlay: 'rgba(0,0,0,0.55)',
};

export type Palette = typeof light;

export function usePalette(): Palette {
  return useColorScheme() === 'dark' ? dark : light;
}

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40 };
export const radius = { sm: 6, md: 10, lg: 14, xl: 20, pill: 999 };

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
