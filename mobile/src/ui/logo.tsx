import { Image } from 'expo-image';
import React from 'react';
import { useColorScheme } from 'react-native';

const SRC = {
  mark: { light: require('../../assets/images/logo-mark-ink.png'), dark: require('../../assets/images/logo-mark-white.png'), ratio: 600 / 263 },
  word: { light: require('../../assets/images/wordmark-ink.png'), dark: require('../../assets/images/wordmark-white.png'), ratio: 600 / 91 },
  full: { light: require('../../assets/images/logo-full-ink.png'), dark: require('../../assets/images/logo-full-white.png'), ratio: 600 / 450 },
};

/** Telomy logo, theme-aware. Width drives size; aspect ratio is fixed. */
export function Logo({ kind = 'mark', width = 64, tone }: { kind?: keyof typeof SRC; width?: number; tone?: 'light' | 'dark' }) {
  const scheme = useColorScheme();
  const t = tone ?? (scheme === 'dark' ? 'dark' : 'light');
  const s = SRC[kind];
  return <Image source={s[t]} style={{ width, height: width / s.ratio }} contentFit="contain" accessibilityLabel="Telomy" />;
}
