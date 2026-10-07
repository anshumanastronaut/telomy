import { router, Stack } from 'expo-router';
import { RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder } from 'expo-audio';
import * as Speech from 'expo-speech';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Pressable, TextInput, View } from 'react-native';

import { API, api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Icon, Row, Screen, Section, T, useToast } from '@/ui/core';

const EXAMPLES = [
  'Had 2 boiled eggs and dal for lunch, then a cigarette',
  'आज मैंने दो अंडे और दाल खाई, थोड़ा तनाव है',
  'Bowled 6 overs at nets, fastest 134 kmph, 2 wickets',
  'Starting my cryo session now',
  'Black coffee at 4, feeling tired',
  'Why is my HRV low this week?',
];

export default function Voice() {
  const p = usePalette();
  const rec = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState('');
  const [speak, setSpeak] = useState(true);
  const [history, setHistory] = useState<any[]>([]);
  const stress = useApi<any>('/voice/stress');
  const design = useApi<any>('/voice/design');
  const pulse = useRef(new Animated.Value(1)).current;
  const { toast, show } = useToast();

  useEffect(() => {
    if (!recording) return;
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: 1.15, duration: 500, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 500, useNativeDriver: true })]));
    a.start();
    return () => a.stop();
  }, [recording]);

  function done(r: any) {
    setHistory((h) => [r, ...h].slice(0, 8));
    stress.reload();
    const say = r.actions?.map((a: any) => a.message).filter(Boolean).join(' ');
    if (speak && say) Speech.speak(say.slice(0, 400), { language: r.language === 'hi' ? 'hi-IN' : 'en-IN', rate: 1.0 });
  }

  async function toggle() {
    if (busy) return;
    if (!recording) {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) { show('Microphone permission is off — enable it in Settings, or type below.', 'alert'); return; }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await rec.prepareToRecordAsync();
      rec.record();
      setRecording(true);
      return;
    }
    setRecording(false);
    setBusy(true);
    try {
      await rec.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const uri = rec.uri;
      if (!uri) throw new Error('No audio captured.');
      const form = new FormData();
      form.append('file', { uri, name: 'sinc.m4a', type: 'audio/m4a' } as any);
      const res = await fetch(`${API}/voice/audio`, { method: 'POST', body: form });
      const j = await res.json();
      if (!res.ok) throw new Error(j.detail || 'Could not understand the recording.');
      done(j);
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  async function send(t?: string) {
    const q = (t ?? text).trim();
    if (!q) return;
    setBusy(true);
    try { done(await api('/voice/command', { body: { text: q } })); setText(''); } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Talk to Sinc' }} />
        <T v="h1">Talk to Sinc</T>
        <T v="small">Say anything, in any language — meals, drinks, cigarettes, coffee, how you feel, a workout, a therapy, a question, or your whole routine. Sinc logs it and answers.</T>
        <View style={{ alignItems: 'center', paddingVertical: 12, gap: 10 }}>
          <Animated.View style={{ transform: [{ scale: pulse }] }}>
            <Pressable onPress={toggle} accessibilityRole="button" accessibilityLabel={recording ? 'Stop and send' : 'Start talking'} testID="mic"
              style={{ width: 112, height: 112, borderRadius: 56, alignItems: 'center', justifyContent: 'center', backgroundColor: recording ? p.copper : p.teal, opacity: busy ? 0.5 : 1 }}>
              <Icon name={recording ? 'stop.fill' : 'mic.fill'} size={40} color="#fff" />
            </Pressable>
          </Animated.View>
          <T v="small">{busy ? 'Listening back… transcribing on your Telomy server' : recording ? 'Listening — tap to send' : 'Tap to talk'}</T>
          <Row>
            <Chip label="Whisper · 99 languages" fg={p.teal} bg={p.tealSoft} />
            <Pressable onPress={() => setSpeak(!speak)} accessibilityRole="switch" accessibilityState={{ checked: speak }}>
              <Chip label={speak ? 'Sinc speaks replies' : 'Silent replies'} />
            </Pressable>
          </Row>
        </View>
        <Row>
          <TextInput value={text} onChangeText={setText} placeholder="…or type it" placeholderTextColor={p.faint} onSubmitEditing={() => send()} returnKeyType="send" testID="voice-text"
            style={{ flex: 1, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' }} />
          <Button title="Send" onPress={() => send()} disabled={!text.trim() || busy} />
        </Row>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
          {EXAMPLES.map((e) => (
            <Pressable key={e} onPress={() => send(e)} accessibilityRole="button">
              <Chip label={e.length > 34 ? e.slice(0, 33) + '…' : e} />
            </Pressable>
          ))}
        </View>

        {history.map((h, i) => (
          <Card key={i} tone={i === 0 ? 'teal' : undefined}>
            <Row><T v="label" style={{ flex: 1 }}>{h.transcription ? `Heard (${h.language})` : 'Typed'}</T>{h.stress?.score != null ? <Chip label={`Voice stress ${h.stress.score}`} fg={h.stress.score >= 55 ? p.copper : p.teal} bg={p.surface} /> : null}</Row>
            <T v="body">“{h.text}”</T>
            {(h.actions ?? []).map((a: any, k: number) => (
              <Row key={k} style={{ alignItems: 'flex-start' }}>
                <Icon name="checkmark.circle.fill" size={16} color={p.success} />
                <T v="small" style={{ flex: 1 }}>{a.message}</T>
              </Row>
            ))}
            {h.actions?.some((a: any) => a.routine) ? <Button kind="secondary" title="Review routine" onPress={() => router.push('/routine')} /> : null}
            {h.actions?.some((a: any) => a.session_id && a.intent === 'therapy_start') ? <Button kind="secondary" title="Open live session" onPress={() => router.push(`/session/${h.actions.find((a: any) => a.session_id).session_id}?live=1`)} /> : null}
            {h.features?.f0_mean ? <T v="small" color={p.muted}>Pitch {h.features.f0_mean} Hz (±{h.features.f0_sd}) · jitter {h.features.jitter_pct}% · HNR {h.features.hnr_db} dB · rate {h.features.rate_per_s}/s</T> : null}
          </Card>
        ))}

        <Section title="Voice stress">
          <Card>
            <T v="body">{stress.data?.n ?? 0} voice samples. {stress.data?.baseline_ready ? 'Your personal baseline is ready.' : 'Telomy learns your normal voice from your first 5 samples.'}</T>
            <T v="small">{stress.data?.how}</T>
          </Card>
        </Section>
        {design.data ? (
          <Section title="Always-on mode (how it will work)">
            <Card>
              {design.data.always_on.map((x: string) => <T key={x} v="small">• {x}</T>)}
              {design.data.privacy.map((x: string) => <T key={x} v="small" color={p.teal}>• {x}</T>)}
              <T v="small">{design.data.languages}</T>
            </Card>
          </Section>
        ) : null}
        <View style={{ height: space[2] }} />
      </Screen>
      {toast}
    </View>
  );
}
