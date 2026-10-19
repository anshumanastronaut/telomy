// On-device Sinc: a small open model running on the iPhone through Cactus. The question and answer stay on the
// phone; the only network call is to the user's own Telomy server for the facts.
//
// Model: Qwen3-1.7B (Apache-2.0, int4, ~1.1 GB). It reads a compact, line-per-fact context from GET /sinc/context
// (labs, 30-day signals, targets, engine findings). The grounding guard: every number in the answer must appear in
// those facts or in the question. If one doesn't, the answer is discarded and Sinc answers through /sinc/ask (the
// grounded composer on the server). Telemetry is off and cloud hand-off is never used.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useState } from 'react';
import { Platform } from 'react-native';

import { api } from '@/lib/api';

export const SLM_MODEL = 'qwen3-1.7b';
export const SLM_INFO = { label: 'Qwen3 1.7B', mb: 1100, note: 'Apache-2.0 · int4 · runs on this iPhone' };
const KEY_ON = 'telomy.slm.on';
const OPTS = { telemetryEnabled: false, temperature: 0.3, topP: 0.9, maxTokens: 380, enableThinking: false } as const;

let Cactus: any = null;
function cactus() {
  if (Cactus === null) { try { Cactus = Platform.OS === 'web' ? false : require('cactus-react-native'); } catch { Cactus = false; } }
  return Cactus || null;
}
export const slmAvailable = () => !!cactus()?.CactusLM;

let lm: any = null;
function model() {
  const C = cactus();
  if (!C?.CactusLM) return null;
  lm ??= new C.CactusLM({ model: SLM_MODEL, options: { quantization: 'int4' } });
  return lm;
}

let fs: any = null;
export async function slmDownloaded(): Promise<boolean> {
  const m = model();
  if (!m) return false;
  try {
    fs ??= require('react-native-nitro-modules').NitroModules.createHybridObject('CactusFileSystem');
    return await fs.modelExists(m.getModelName());
  } catch { return false; }
}

/** Numbers in a text, normalised (232.0 → 232, 1,433 → 1433). */
function numbers(s: string): number[] {
  return (s.replace(/(\d),(\d{3})/g, '$1$2').match(/\d+(?:\.\d+)?/g) ?? []).map(Number);
}

/** Every number the model wrote must be in the facts or the question. Small counts (≤ 10) without a unit pass —
 *  "two things", "1." — but a small number followed by a unit (2 mg, 5 g) must be grounded like any other. */
export function ungrounded(answer: string, facts: string, question: string): number[] {
  const known = new Set([...numbers(facts), ...numbers(question)].map((n) => +n.toFixed(2)));
  const bad: number[] = [];
  const re = /(\d+(?:\.\d+)?)(\s*(?:mg|g|mcg|µg|iu|ml|%|kg|kcal|tablets?|capsules?|units?)\b)?/gi;
  for (const m of answer.replace(/(\d),(\d{3})/g, '$1$2').matchAll(re)) {
    const n = +Number(m[1]).toFixed(2);
    if (known.has(n)) continue;
    if (Number.isInteger(n) && n <= 10 && !m[2]) continue;
    bad.push(n);
  }
  return bad;
}

const clean = (s: string) => s.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/<\|[^|]*\|>/g, '').trim();

export type SlmAnswer = { answer: string; model: string; ms: number; tps?: number } | { fallback: string };

/** Ask the on-device model. Returns { fallback } when the model isn't ready, fails, or its answer isn't grounded. */
export async function askOnDevice(question: string, onToken?: (t: string) => void): Promise<SlmAnswer> {
  const m = model();
  if (!m || !(await slmDownloaded())) return { fallback: 'model not downloaded' };
  const ctx = await api<{ system: string; facts: string }>(`/sinc/context?q=${encodeURIComponent(question.slice(0, 300))}`);
  try {
    const r = await m.complete({
      messages: [
        { role: 'system', content: `${ctx.system}\n\nFACTS:\n${ctx.facts}` },
        { role: 'user', content: question },
      ],
      options: OPTS,
      onToken,
    });
    const answer = clean(String(r?.response ?? ''));
    if (!answer) return { fallback: 'empty answer' };
    const bad = ungrounded(answer, ctx.facts, question);
    if (bad.length) return { fallback: `the on-device answer used numbers not in your data (${bad.slice(0, 3).join(', ')})` };
    return { answer, model: `${SLM_INFO.label} on this iPhone`, ms: r.totalTimeMs, tps: r.decodeTps };
  } catch (e: any) {
    return { fallback: e?.message ?? 'on-device model failed' };
  }
}

/** On/off, download state and progress for the Sinc screen. */
export function useSlm() {
  const [on, setOnS] = useState(false);
  const [ready, setReady] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => setReady(await slmDownloaded()), []);
  useEffect(() => {
    AsyncStorage.getItem(KEY_ON).then((v) => setOnS(v === '1')).catch(() => {});
    refresh();
  }, [refresh]);
  const download = useCallback(async () => {
    const m = model();
    if (!m) { setError('On-device Sinc needs the iPhone app.'); return; }
    setError(null); setProgress(0);
    try { await m.download({ onProgress: (p: number) => setProgress(p) }); await refresh(); }
    catch (e: any) { setError(e?.message ?? 'Download failed — check your connection and try again.'); }
    finally { setProgress(null); }
  }, [refresh]);
  return {
    available: slmAvailable(), on: on && ready, ready, progress, error, download,
    setOn: (v: boolean) => { setOnS(v); AsyncStorage.setItem(KEY_ON, v ? '1' : '0').catch(() => {}); },
  };
}
