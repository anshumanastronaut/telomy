// React Native host for the 3D twin scene. Maps the Twin's organ systems onto 3D organs, forwards taps back to the
// screen, and surfaces any WebGL/script error instead of failing silently.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';
import { WebView } from 'react-native-webview';
import { API } from '@/lib/api';
import { depth, usePalette } from '@/lib/theme';
import { T } from '@/ui/core';
import { sceneHtml, type OrganId, type OrganStatus } from './scene';

import { ORGAN_LABEL, SYSTEM_ORGANS, systemOfOrgan } from './organs';
export { ORGAN_LABEL, SYSTEM_ORGANS, systemOfOrgan };

export function Twin3D({ systems, selected, onSelect, height = 460, onInteract }: {
  systems: { name: string; status: string }[];
  selected: OrganId | null;
  onSelect: (o: OrganId | null) => void;
  height?: number;
  /** true while a finger is on the model — the parent stops scrolling so drag/pinch go to the 3D view */
  onInteract?: (active: boolean) => void;
}) {
  const p = usePalette();
  const ref = useRef<WebView>(null);
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const html = useMemo(() => sceneHtml(`${API}/static/telomy_anatomy.glb`), []);

  const status = useMemo(() => {
    const s: Partial<Record<OrganId, OrganStatus>> = {};
    for (const sys of systems) for (const o of SYSTEM_ORGANS[sys.name] ?? []) s[o] = (sys.status as OrganStatus) ?? 'none';
    return s;
  }, [systems]);

  useEffect(() => { if (ready) ref.current?.injectJavaScript(`window.setStatus(${JSON.stringify(status)});true;`); }, [ready, status]);
  useEffect(() => { if (ready) ref.current?.injectJavaScript(`window.select(${JSON.stringify(selected)});true;`); }, [ready, selected]);

  return (
    <View style={{ height, borderRadius: 28, overflow: 'hidden', backgroundColor: depth.stage }}
      onTouchStart={() => onInteract?.(true)} onTouchEnd={() => onInteract?.(false)} onTouchCancel={() => onInteract?.(false)}>
      <WebView
        ref={ref}
        originWhitelist={['*']}
        source={{ html }}
        style={{ backgroundColor: 'transparent' }}
        scrollEnabled={false}
        bounces={false}
        javaScriptEnabled
        onMessage={(e) => {
          try {
            const m = JSON.parse(e.nativeEvent.data);
            if (m.type === 'ready') setReady(true);
            else if (m.type === 'select') onSelect(m.organ ?? null);
            else if (m.type === 'error') setErr(m.message);
          } catch {}
        }}
      />
      {err ? <View style={{ position: 'absolute', bottom: 12, left: 12, right: 12 }}><T v="small" color={p.danger}>3D view error: {err}</T></View> : null}
      {!ready && !err ? <View style={{ position: 'absolute', top: '45%', left: 0, right: 0, alignItems: 'center' }}><T v="small" color={p.muted}>Building your twin…</T></View> : null}
    </View>
  );
}
