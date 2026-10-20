// Web build of Sinc's orb: same vendored engine + driver, rendered in an <iframe> (no native WebView on the web).
import React, { useEffect, useMemo, useRef } from 'react';
import { usePalette } from '@/lib/theme';
import { ORB_SRC } from './orbSource.generated';
export type OrbState = 'working' | 'searching' | 'solving' | 'listening' | 'composing' | 'shaping';

export function ThinkingOrb({ state = 'solving', size = 64, scale = 1 }: { state?: OrbState; size?: 64 | 20; scale?: number }) {
  const p = usePalette();
  const ref = useRef<HTMLIFrameElement>(null);
  const px = size * scale;
  const html = useMemo(() => `<!doctype html><html><head><style>html,body{margin:0;background:transparent;overflow:hidden}canvas{display:block}</style></head><body>
<script>${ORB_SRC.replace(/<\//g, '<\\/')}</script><script>window.setOrb(${JSON.stringify({ state, size, scale, dark: p.isDark })});window.addEventListener('message',e=>window.setOrb(e.data));</script></body></html>`,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [size, scale, p.isDark]);
  useEffect(() => { ref.current?.contentWindow?.postMessage({ state }, '*'); }, [state]);
  return <iframe ref={ref} srcDoc={html} title={`Sinc is ${state}`} style={{ width: px, height: px, border: 0, background: 'transparent', pointerEvents: 'none' }} />;
}
