// Sinc for the clinic & centre consoles — the grounded, propose-don't-act copilot. Ask about a patient (or the
// panel / the centre's operations); Sinc answers from the record and drafts next steps that route to the existing
// approve flows (it never prescribes, signs or orders itself). Thinking state uses the Telomy motion loader.
import { AudioQuality, IOSOutputFormat, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder, type RecordingOptions } from 'expo-audio';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Keyboard, KeyboardAvoidingView, Platform, Pressable, ScrollView, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { transcribeOnDevice, useSpeech } from '@/lib/speech';
import { radius, space, usePalette } from '@/lib/theme';
import { Chip, Icon, Row, T, useToast } from '@/ui/core';
import { TelomyLoader } from '@/ui/loader';

// 16 kHz mono WAV — what the server's Whisper wants, no re-encoding on the phone.
const WAV16: RecordingOptions = {
  extension: '.wav', sampleRate: 16000, numberOfChannels: 1, bitRate: 256000,
  android: { outputFormat: 'default', audioEncoder: 'default' },
  ios: { outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.MAX, linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
};

type Suggestion = { kind: string; label: string; route?: string };
type Msg = { role: 'user' | 'assistant'; content: string; suggestions?: Suggestion[]; confidence?: number; engine?: string; grounded?: boolean; pending?: boolean };

export function Copilot({ role, patientId, patientName }: { role: 'doctor' | 'centre'; patientId?: string; patientName?: string }) {
  const p = usePalette();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [kbd, setKbd] = useState(false);
  const scroll = useRef<ScrollView>(null);
  const rec = useAudioRecorder(WAV16);
  const sp = useSpeech();
  const { show } = useToast();
  const endpoint = role === 'doctor' ? '/mgmt/clinic/copilot' : '/mgmt/centre/copilot';

  useEffect(() => {
    const a = Keyboard.addListener('keyboardWillShow', () => setKbd(true));
    const b = Keyboard.addListener('keyboardWillHide', () => setKbd(false));
    return () => { a.remove(); b.remove(); };
  }, []);

  async function toggleMic() {
    if (busy || transcribing) return;
    if (!recording) {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) { show('Microphone is off — enable it in Settings, or type your question.', 'alert'); return; }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await rec.prepareToRecordAsync();
      rec.record();
      setRecording(true);
      return;
    }
    setRecording(false);
    setTranscribing(true);
    try {
      await rec.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const uri = rec.uri;
      if (!uri) throw new Error('No audio captured.');
      let heard = '';
      const local = await transcribeOnDevice(uri, sp.model, sp.lang).catch(() => null);   // private, on-device when a model is downloaded
      if (local?.text) heard = local.text;
      else {
        const form = new FormData();
        form.append('file', { uri, name: 'sinc.wav', type: 'audio/wav' } as any);
        const j = await api<any>('/mgmt/voice/transcribe', { form });                     // else the Telomy server (nothing stored)
        heard = j.text || '';
      }
      setTranscribing(false);
      if (!heard.trim()) { show("Didn't catch that — try again a little closer to the mic.", 'alert'); return; }
      await send(heard);
    } catch (e: any) {
      setTranscribing(false);
      show(e.message || 'Could not transcribe.', 'alert');
    }
  }

  const starters = role === 'doctor'
    ? (patientId
        ? ['Summarise this patient', 'What should I prioritise?', 'Draft a care plan for them', 'What should we retest, and when?']
        : ['Who needs me most today?', 'Summarise my care queue', 'Any patients trending the wrong way?'])
    : ['How is the centre doing today?', 'What needs attention on the floor?', 'How much is outstanding, and from whom?', 'How busy are we this week?'];

  async function send(q: string) {
    if (!q.trim() || busy) return;
    setText('');
    const history = msgs.filter((m) => !m.pending).map((m) => ({ role: m.role, content: m.content }));
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', pending: true }]);
    setBusy(true);
    try {
      const r = await api<any>(endpoint, { body: { query: q, patient_id: patientId ? Number(patientId) : undefined, history } });
      setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: r.answer, suggestions: r.suggestions, confidence: r.confidence, engine: r.engine, grounded: r.grounded }]);
    } catch (e: any) {
      setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', content: `I couldn't answer just now. ${e.message}` }]);
    } finally {
      setBusy(false);
      setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 120);
    }
  }

  const subtitle = role === 'doctor'
    ? (patientName ? `Grounded in ${patientName}'s record · drafts, you sign` : "Grounded in your patients' records · drafts, you sign")
    : "Grounded in your centre's data · drafts, you decide";

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: p.bg }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }} keyboardVerticalOffset={60}>
        <Row style={{ paddingHorizontal: space[4], paddingVertical: space[2], alignItems: 'center' }}>
          {router.canGoBack() ? (
            <Pressable onPress={() => router.back()} hitSlop={10} accessibilityLabel="Back" style={{ paddingRight: 4 }}>
              <Icon name="chevron.left" color={p.teal} size={18} />
            </Pressable>
          ) : null}
          <View style={{ width: 44, height: 34, alignItems: 'center', justifyContent: 'center' }}>
            <TelomyLoader size="mark" />
          </View>
          <View style={{ flex: 1 }}>
            <T v="h3">Sinc</T>
            <T v="small" numberOfLines={1}>{subtitle}</T>
          </View>
          {msgs.length ? (
            <Pressable onPress={() => setMsgs([])} hitSlop={10} accessibilityLabel="New chat">
              <Icon name="square.and.pencil" color={p.teal} />
            </Pressable>
          ) : null}
        </Row>

        <ScrollView ref={scroll} contentContainerStyle={{ padding: space[4], gap: space[3], paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
          {msgs.length === 0 ? (
            <View style={{ alignItems: 'center', gap: space[5], paddingTop: space[6] }}>
              <TelomyLoader size="hero" />
              <View style={{ alignItems: 'center', gap: space[2] }}>
                <T v="h1" style={{ textAlign: 'center' }}>Ask Sinc.</T>
                <T v="small" color={p.muted} style={{ textAlign: 'center' }}>{subtitle}. Every answer traces to the record, and nothing happens until you approve it.</T>
              </View>
              <View style={{ width: '100%', gap: space[2] }}>
                {starters.map((s) => (
                  <Pressable key={s} onPress={() => send(s)} accessibilityRole="button"
                    style={{ backgroundColor: p.surface, borderRadius: radius.lg, padding: space[3], flexDirection: 'row', alignItems: 'center', gap: space[2] }}>
                    <Icon name="sparkles" size={15} color={p.teal} />
                    <T v="body" style={{ flex: 1 }}>{s}</T>
                    <Icon name="arrow.up.right" size={12} color={p.faint} />
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            msgs.map((m, i) => <Bubble key={i} m={m} />)
          )}
        </ScrollView>

        <Row style={{ marginHorizontal: space[3], marginBottom: kbd ? 8 : 100, padding: 6, paddingLeft: 4, borderRadius: 28, backgroundColor: p.surface }}>
          <TextInput value={text} onChangeText={setText} placeholder={recording ? 'Listening — tap to send' : patientName ? `Ask about ${patientName}` : 'Ask Sinc'} placeholderTextColor={p.faint} multiline
            editable={!recording && !transcribing} onSubmitEditing={() => send(text)} returnKeyType="send" testID="copilot-input"
            style={{ flex: 1, minHeight: 40, maxHeight: 120, color: p.text, fontSize: 15, paddingHorizontal: 12, paddingVertical: 10, fontFamily: 'Geist_400Regular' }} />
          {text.trim() ? (
            <Pressable onPress={() => send(text)} disabled={busy} accessibilityLabel="Send" testID="copilot-send"
              style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: p.teal, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name="arrow.up" size={18} color={p.onAccent} />
            </Pressable>
          ) : (
            <Pressable onPress={toggleMic} disabled={busy || transcribing} accessibilityLabel={recording ? 'Stop and send' : 'Speak to Sinc'} testID="copilot-mic"
              style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: recording ? p.copper : transcribing ? p.surfaceAlt : p.teal, alignItems: 'center', justifyContent: 'center' }}>
              {transcribing ? <ActivityIndicator color={p.teal} /> : <Icon name={recording ? 'stop.fill' : 'mic.fill'} size={18} color={p.onAccent} />}
            </Pressable>
          )}
        </Row>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function Bubble({ m }: { m: Msg }) {
  const p = usePalette();
  if (m.role === 'user')
    return (
      <View style={{ alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: p.teal, borderRadius: radius.lg, padding: space[3] }}>
        <T v="body" color={p.onAccent}>{m.content}</T>
      </View>
    );
  if (m.pending)
    return (
      <Row gap={space[3]} style={{ alignItems: 'center' }}>
        <TelomyLoader size="inline" />
        <T v="small">Reading the record…</T>
      </Row>
    );
  return (
    <View style={{ gap: 8, maxWidth: '98%' }}>
      <Md text={m.content} />
      {m.suggestions?.length ? (
        <View style={{ gap: 6 }}>
          <T v="label">Next steps — you approve</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {m.suggestions.map((s, i) => (
              <Pressable key={i} onPress={() => s.route && router.push(s.route as any)} accessibilityRole="button">
                <Chip label={s.label} fg={p.teal} bg={p.tealSoft} icon="arrow.up.right" />
              </Pressable>
            ))}
          </View>
        </View>
      ) : null}
      {m.confidence != null ? (
        <T v="small" color={p.faint}>{m.engine === 'telomy-composer' ? 'Grounded composer' : `${m.engine}`} · {Math.round((m.confidence ?? 0) * 100)}% · drafts only, not a diagnosis</T>
      ) : null}
    </View>
  );
}

/** Minimal markdown: **bold**, _italic_, "- " bullets. */
function Md({ text }: { text: string }) {
  const p = usePalette();
  return (
    <View style={{ gap: 6 }}>
      {text.split('\n').filter((l) => l.trim()).map((line, i) => {
        const bullet = line.trim().startsWith('- ');
        const body = bullet ? line.trim().slice(2) : line;
        const parts = body.split(/(\*\*[^*]+\*\*|_[^_]+_)/g);
        return (
          <Row key={i} style={{ alignItems: 'flex-start' }} gap={6}>
            {bullet ? <T v="body" color={p.teal}>•</T> : null}
            <T v="body" style={{ flex: 1 }}>
              {parts.map((pt, k) =>
                pt.startsWith('**') ? <T key={k} v="body" style={{ fontWeight: '700' }}>{pt.slice(2, -2)}</T>
                  : pt.startsWith('_') && pt.endsWith('_') ? <T key={k} v="small" color={p.muted}>{pt.slice(1, -1)}</T>
                  : pt,
              )}
            </T>
          </Row>
        );
      })}
    </View>
  );
}
