// Canvas driver for the vendored thinking-orbs engine (MIT, © 2026 Jakub Antalik — vendor/thinking-orbs/LICENSE).
// Mirrors ThinkingOrb.ts's render loop without Vue; the app calls window.setOrb({ state, size, dark, speed }).
import { MODE_DRAWS } from '../vendor/thinking-orbs/src/engine/registry';
import { resolvePreset } from '../vendor/thinking-orbs/src/presets';

const canvas = document.createElement('canvas'); document.body.appendChild(canvas);
const ctx = canvas.getContext('2d')!;
let cfg = { state: 'solving', size: 64, dark: true, speed: 1, scale: 1 } as any, raf = 0;
function start() {
  cancelAnimationFrame(raf);
  // `scale` redraws the tuned 64/20 design larger at full resolution (no bitmap blur)
  const dpr = Math.min(3, window.devicePixelRatio || 1), size = cfg.size, k = cfg.scale || 1;
  canvas.width = Math.round(size * k * dpr); canvas.height = Math.round(size * k * dpr);
  canvas.style.width = canvas.style.height = size * k + 'px';
  const { mode, speed, opts } = resolvePreset(cfg.state, size);
  const draw = MODE_DRAWS[mode], eff = speed * (cfg.speed ?? 1);
  const loop = () => { ctx.setTransform(dpr * k, 0, 0, dpr * k, 0, 0); ctx.clearRect(0, 0, size, size); draw(ctx, size, (performance.now() / 1000) * eff, cfg.dark, opts); raf = requestAnimationFrame(loop); };
  loop();
}
(window as any).setOrb = (c: any) => { cfg = { ...cfg, ...c }; start(); };
start();
