import React, { useState } from 'react';
import { View } from 'react-native';

import { usePalette } from '@/lib/theme';

/** Minimal dependency-free slider (tap or drag along the track). */
export default function Slider({ value, max, onChange }: { value: number; max: number; onChange: (v: number) => void }) {
  const p = usePalette();
  const [w, setW] = useState(1);
  const set = (x: number) => onChange(Math.round(Math.max(0, Math.min(1, x / w)) * max));
  return (
    <View
      onLayout={(e) => setW(e.nativeEvent.layout.width)}
      onStartShouldSetResponder={() => true}
      onMoveShouldSetResponder={() => true}
      onResponderGrant={(e) => set(e.nativeEvent.locationX)}
      onResponderMove={(e) => set(e.nativeEvent.locationX)}
      accessibilityRole="adjustable"
      accessibilityValue={{ min: 0, max, now: value }}
      style={{ height: 32, justifyContent: 'center' }}>
      <View style={{ height: 4, borderRadius: 2, backgroundColor: p.surfaceAlt }} />
      <View style={{ position: 'absolute', left: (value / Math.max(max, 1)) * (w - 20), width: 20, height: 20, borderRadius: 10, backgroundColor: p.teal }} />
    </View>
  );
}
