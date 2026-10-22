// Web build of the 3D twin: the same three.js scene, in an <iframe> (no native WebView on the web). The iframe is
// same-origin (srcDoc), so the page can call the scene's setStatus/select directly; the scene's messages are bridged
// through a tiny ReactNativeWebView shim.
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View } from 'react-native';
import { API } from '@/lib/api';
import { depth, usePalette } from '@/lib/theme';
import { T } from '@/ui/core';
import { ORGAN_LABEL, SYSTEM_ORGANS, systemOfOrgan } from './organs';
import { sceneHtml, type OrganId, type OrganStatus } from './scene';
export { ORGAN_LABEL, SYSTEM_ORGANS, systemOfOrgan };

export function Twin3D({ systems, selected, onSelect, height = 460, onInteract }: {
  systems: { name: string; status: string }[]; selected: OrganId | null; onSelect: (o: OrganId | null) => void; height?: number; onInteract?: (a: boolean) => void;
}) {
  const p = usePalette();
  const ref = useRef<HTMLIFrameElement>(null);
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const html = useMemo(() => sceneHtml(`${API}/static/telomy_anatomy.glb`).replace('<head>', '<head><script>window.ReactNativeWebView={postMessage:function(m){parent.postMessage({__twin:m},"*")}}</script>'), []);
  const status = useMemo(() => {
    const s: Partial<Record<OrganId, OrganStatus>> = {};
    for (const sys of systems) for (const o of SYSTEM_ORGANS[sys.name] ?? []) s[o] = (sys.status as OrganStatus) ?? 'none';
    return s;
  }, [systems]);
  useEffect(() => {
    const on = (e: MessageEvent) => {
      if (!e.data?.__twin) return;
      try { const m = JSON.parse(e.data.__twin); if (m.type === 'ready') setReady(true); else if (m.type === 'select') onSelect(m.organ ?? null); else if (m.type === 'error') setErr(m.message); } catch {}
    };
    window.addEventListener('message', on); return () => window.removeEventListener('message', on);
  }, [onSelect]);
  const win = () => ref.current?.contentWindow as any;
  useEffect(() => { if (ready) win()?.setStatus?.(status); }, [ready, status]);
  useEffect(() => { if (ready) win()?.select?.(selected); }, [ready, selected]);
  return (
    <View style={{ height, borderRadius: 28, overflow: 'hidden', backgroundColor: depth.stage }}
      onPointerEnter={() => onInteract?.(true)} onPointerLeave={() => onInteract?.(false)}>
      <iframe ref={ref} srcDoc={html} title="Your 3D twin" style={{ width: '100%', height: '100%', border: 0 }} />
      {err ? <View style={{ position: 'absolute', bottom: 12, left: 12, right: 12 }}><T v="small" color={p.danger}>3D view error: {err}</T></View> : null}
      {!ready && !err ? <View style={{ position: 'absolute', top: '45%', left: 0, right: 0, alignItems: 'center' }}><T v="small" color={p.muted}>Building your twin…</T></View> : null}
    </View>
  );
}
