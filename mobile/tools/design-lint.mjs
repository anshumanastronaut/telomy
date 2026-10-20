#!/usr/bin/env node
// Design lint: hardcoded colours and font sizes may only go DOWN. Every value should come from src/lib/theme.ts
// (palette, data, type, space, radius, motion). The baseline below is today's debt; lower it as screens are migrated.
//   node tools/design-lint.mjs          → report + fail if any count rose
//   node tools/design-lint.mjs --update → write the current (lower) counts as the new baseline
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = new URL('../src/', import.meta.url).pathname;
const BASELINE = new URL('./design-baseline.json', import.meta.url).pathname;
const RULES = {
  hex: /['"]#[0-9a-fA-F]{3,8}['"]/g,          // raw colour literal
  rgba: /rgba?\(\s*\d/g,                       // raw rgba()
  fontSize: /fontSize:\s*\d/g,                 // number instead of type.* token
};
const files = [];
(function walk(d) { for (const f of readdirSync(d)) { const p = join(d, f); statSync(p).isDirectory() ? walk(p) : /\.(tsx?|jsx?)$/.test(f) && !p.endsWith('lib/theme.ts') && !p.endsWith('twin3d/scene.ts') && !p.includes('.generated.') && files.push(p); } })(ROOT);

const counts = Object.fromEntries(Object.keys(RULES).map((k) => [k, 0]));
const worst = [];
for (const f of files) {
  const s = readFileSync(f, 'utf8'); let n = 0;
  for (const [k, re] of Object.entries(RULES)) { const m = s.match(re)?.length ?? 0; counts[k] += m; n += m; }
  if (n) worst.push([n, f.replace(ROOT, '')]);
}
let base = {}; try { base = JSON.parse(readFileSync(BASELINE, 'utf8')); } catch {}
if (process.argv.includes('--update') || !Object.keys(base).length) { writeFileSync(BASELINE, JSON.stringify(counts, null, 2) + '\n'); console.log('baseline written', counts); process.exit(0); }
let fail = false;
for (const k of Object.keys(RULES)) {
  const d = counts[k] - (base[k] ?? 0);
  console.log(`${k.padEnd(9)} ${String(counts[k]).padStart(4)}  (baseline ${base[k] ?? 0}${d ? `, ${d > 0 ? '+' : ''}${d}` : ''})`);
  if (d > 0) fail = true;
}
console.log('most debt:', worst.sort((a, b) => b[0] - a[0]).slice(0, 5).map(([n, f]) => `${f} ${n}`).join(' · '));
if (fail) { console.error('\n✗ New hardcoded design values. Use tokens from src/lib/theme.ts (palette, data, type, space, radius, motion).'); process.exit(1); }
console.log('✓ no new hardcoded design values');
