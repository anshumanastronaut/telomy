// Sinc's thinking indicator — the thinking-orbs dotted orb (MIT © 2026 Jakub Antalik, vendored engine) drawn on a
// real 2D canvas in a tiny transparent WebView, so it is pixel-identical to the original. Six states map to what
// Sinc is doing; changing `state` morphs in place without reloading.
import React, { useEffect, useMemo, useRef } from 'react';
import { View } from 'react-native';
import { WebView } from 'react-native-webview';
import { usePalette } from '@/lib/theme';
import { ORB_SRC } from './orbSource.generated';

export type OrbState = 'working' | 'searching' | 'solving' | 'listening' | 'composing' | 'shaping';

export function ThinkingOrb({ state = 'solving', size = 64, scale = 1 }: { state?: OrbState; size?: 64 | 20; scale?: number }) {
  const px = size * scale;
  const p = usePalette();
  const ref = useRef<WebView>(null);
  const html = useMemo(() => `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<style>html,body{margin:0;background:transparent;overflow:hidden}canvas{display:block}</style></head><body>
<script>${ORB_SRC.replace(/<\//g, '<\\/')}</script><script>window.setOrb(${JSON.stringify({ state, size, scale, dark: p.isDark })});</script></body></html>`,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [size, scale, p.isDark]);
  useEffect(() => { ref.current?.injectJavaScript(`window.setOrb(${JSON.stringify({ state })});true;`); }, [state]);
  return (
    <View style={{ width: px, height: px }} accessibilityRole="image" accessibilityLabel={`Sinc is ${state}`}>
      <WebView ref={ref} originWhitelist={['*']} source={{ html }} style={{ width: px, height: px, backgroundColor: 'transparent' }}
        scrollEnabled={false} bounces={false} pointerEvents="none" />
    </View>
  );
}
