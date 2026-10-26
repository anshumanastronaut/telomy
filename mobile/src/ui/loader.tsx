// Telomy loader motion — a side-on DNA double helix / infinity: two strands 180° apart whose beads sweep past each
// other and meet at the crossing nodes, with a slow twist running across the columns. One shared clock drives every
// column, so the whole thing moves in sync. Lightweight (Reanimated + SVG, no canvas) so it can live anywhere a
// screen or Sinc is thinking. Use <Loading> (ui/core) for the standard centred case.
import React from 'react';
import { Text, View } from 'react-native';
import Animated, { SharedValue, useAnimatedProps, useDerivedValue, useFrameCallback, useSharedValue } from 'react-native-reanimated';
import Svg, { Circle, Line } from 'react-native-svg';

import { fonts, space, usePalette } from '@/lib/theme';

const ACircle = Animated.createAnimatedComponent(Circle);
const ALine = Animated.createAnimatedComponent(Line);

const SPEED = 1.0;   // radians/sec — slow, graceful rotation
const TWIST = 0.55;  // phase step per column — the helix twist across the row

function Rung({ i, clock, w, n, h, color }: { i: number; clock: SharedValue<number>; w: number; n: number; h: number; color: string }) {
  const s = w / n;
  const cx = s * (i + 0.5);
  const cy = h / 2;
  const Hm = h * 0.42;
  const R = Math.max(2.4, Math.min(6.5, s * 0.17));
  // one shared value per column: the strand offset, a slow sine with a per-column phase (the twist).
  const sp = useDerivedValue(() => Math.sin(clock.value * SPEED - i * TWIST));
  const line = useAnimatedProps(() => {
    const v = sp.value, a = Math.abs(v);
    return { y1: cy - Hm * v, y2: cy + Hm * v, opacity: 0.18 + 0.5 * a, strokeWidth: 1 + 0.7 * a };
  });
  const top = useAnimatedProps(() => ({ cy: cy - Hm * sp.value, r: R * (1.22 - 0.3 * Math.abs(sp.value)) }));
  const bot = useAnimatedProps(() => ({ cy: cy + Hm * sp.value, r: R * (1.22 - 0.3 * Math.abs(sp.value)) }));
  return (
    <>
      <ALine x1={cx} x2={cx} stroke={color} strokeLinecap="round" animatedProps={line} />
      <ACircle cx={cx} fill={color} animatedProps={top} />
      <ACircle cx={cx} fill={color} animatedProps={bot} />
    </>
  );
}

/** The DNA-wave loader — Telomy's motion signature. `size`: inline (cards/screens), hero (big states), or mark
 *  (tiny, for an avatar/header). width/height/count override the preset for a custom fit. */
export function TelomyLoader({ size = 'inline', message, tint, width, height, count }: { size?: 'inline' | 'hero' | 'mark'; message?: string; tint?: string; width?: number; height?: number; count?: number }) {
  const p = usePalette();
  const color = tint ?? p.teal;
  const preset = size === 'hero' ? { w: 210, h: 90, n: 11 } : size === 'mark' ? { w: 46, h: 24, n: 5 } : { w: 120, h: 48, n: 9 };
  const w = width ?? preset.w;
  const h = height ?? preset.h;
  const n = count ?? preset.n;
  const clock = useSharedValue(0);
  useFrameCallback((f) => {
    clock.value = (f.timeSinceFirstFrame ?? 0) / 1000;
  });
  return (
    <View style={{ alignItems: 'center', justifyContent: 'center', gap: message ? space[3] : 0, paddingVertical: size === 'mark' ? 0 : space[3] }}>
      <Svg width={w} height={h}>
        {Array.from({ length: n }).map((_, i) => (
          <Rung key={i} i={i} clock={clock} w={w} n={n} h={h} color={color} />
        ))}
      </Svg>
      {message ? <Text style={{ fontFamily: fonts.body, fontSize: 13, color: p.muted, letterSpacing: 0.2 }}>{message}</Text> : null}
    </View>
  );
}
