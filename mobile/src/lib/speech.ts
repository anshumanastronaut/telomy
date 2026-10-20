// On-device speech recognition for Sinc (Cactus engine running Whisper on the iPhone; no audio leaves the phone).
//
// Models (Cactus-Compute on Hugging Face, int4): whisper-base 76 MB — multilingual (99 languages incl. Hindi and
// Hinglish), the default; whisper-small 180 MB — more accurate, slower. Cactus Whistle (17 MB) is English/European-only
// and not in Cactus's app model registry, so it is not offered. Telemetry is off (CACTUS_NO_CLOUD_TELE set natively and
// telemetryEnabled: false per call) and cloud hand-off is disabled. When no model is downloaded, the app falls back to
// Whisper on the Telomy server.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useState } from 'react';
import { Platform } from 'react-native';

export type SpeechModel = 'whisper-base' | 'whisper-small';
export const MODELS: Record<SpeechModel, { label: string; mb: number; note: string }> = {
  'whisper-base': { label: 'Whisper base', mb: 76, note: 'Fast · 99 languages incl. Hindi' },
  'whisper-small': { label: 'Whisper small', mb: 180, note: 'Most accurate · slower' },
};
export type SpeechLang = 'auto' | 'en' | 'hi';
const KEY_MODEL = 'telomy.speech.model', KEY_LANG = 'telomy.speech.lang';
const OPTS = { telemetryEnabled: false, cloudHandoffThreshold: 1e9, useVad: true } as const;

let Cactus: any = null;
function cactus() {
  if (Cactus === null) { try { Cactus = Platform.OS === 'web' ? false : require('cactus-react-native'); } catch { Cactus = false; } }
  return Cactus || null;
}
export const speechAvailable = () => !!cactus()?.CactusSTT;

const instances = new Map<SpeechModel, any>();
function stt(model: SpeechModel) {
  const C = cactus();
  if (!C?.CactusSTT) return null;
  if (!instances.has(model)) instances.set(model, new C.CactusSTT({ model, options: { quantization: 'int4' } }));
  return instances.get(model);
}

let fs: any = null;   // Cactus's own file-system hybrid object (not exported by the package index)
export async function isDownloaded(model: SpeechModel): Promise<boolean> {
  if (!cactus()?.CactusSTT) return false;
  try {
    fs ??= require('react-native-nitro-modules').NitroModules.createHybridObject('CactusFileSystem');
    return await fs.modelExists(stt(model).getModelName());
  } catch { return false; }
}

/** Transcribe a recording on the phone. Returns null when no model is ready (caller falls back to the server). */
export async function transcribeOnDevice(path: string, model: SpeechModel, lang: SpeechLang): Promise<{ text: string; language: string; model: string } | null> {
  const s = stt(model);
  if (!s || !(await isDownloaded(model))) return null;
  const audio = path.replace('file://', '');
  let language: string = lang;
  if (lang === 'auto') {
    try { const d = await s.detectLanguage({ audio, options: { useVad: true } }); language = d?.language || 'en'; } catch { language = 'en'; }
  }
  const r = await s.transcribe({ audio, prompt: `<|startoftranscript|><|${language}|><|transcribe|><|notimestamps|>`, options: OPTS });
  const text = String(r?.response ?? '').replace(/<\|[^|]*\|>/g, '').trim();
  return { text, language, model: `${model} (on this iPhone, Cactus)` };
}

/** Model choice, language and download state for the settings card. */
export function useSpeech() {
  const [model, setModelS] = useState<SpeechModel>('whisper-base');
  const [lang, setLangS] = useState<SpeechLang>('auto');
  const [ready, setReady] = useState<Record<SpeechModel, boolean>>({ 'whisper-base': false, 'whisper-small': false });
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(async () => {
    setReady({ 'whisper-base': await isDownloaded('whisper-base'), 'whisper-small': await isDownloaded('whisper-small') });
  }, []);
  useEffect(() => {
    AsyncStorage.multiGet([KEY_MODEL, KEY_LANG]).then(([[, m], [, l]]) => {
      if (m === 'whisper-base' || m === 'whisper-small') setModelS(m);
      if (l === 'auto' || l === 'en' || l === 'hi') setLangS(l);
    }).catch(() => {});
    refresh();
  }, [refresh]);
  const download = useCallback(async (m: SpeechModel) => {
    const s = stt(m);
    if (!s) { setError('On-device speech needs the iPhone app.'); return; }
    setError(null); setProgress(0);
    try { await s.download({ onProgress: (p: number) => setProgress(p) }); await refresh(); }
    catch (e: any) { setError(e?.message ?? 'Download failed — check your connection and try again.'); }
    finally { setProgress(null); }
  }, [refresh]);
  return {
    available: speechAvailable(), model, lang, ready, progress, error, download,
    setModel: (m: SpeechModel) => { setModelS(m); AsyncStorage.setItem(KEY_MODEL, m).catch(() => {}); },
    setLang: (l: SpeechLang) => { setLangS(l); AsyncStorage.setItem(KEY_LANG, l).catch(() => {}); },
  };
}
