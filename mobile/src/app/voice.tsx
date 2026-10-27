import { router, Stack } from 'expo-router';
import { AudioQuality, IOSOutputFormat, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder, type RecordingOptions } from 'expo-audio';
import * as Speech from 'expo-speech';
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Pressable, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { Band } from '@/lib/band';
import { MODELS, transcribeOnDevice, useSpeech, type SpeechModel } from '@/lib/speech';

// 16 kHz mono 16-bit WAV: what Whisper and the voice-feature extractor both want (no re-encoding on the phone).
const WAV16: RecordingOptions = {
  extension: '.wav', sampleRate: 16000, numberOfChannels: 1, bitRate: 256000,
  android: { outputFormat: 'default', audioEncoder: 'default' },
  ios: { outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.MAX, linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
};
// Read-aloud passage for the voice check-in: the same words every time make pitch, rate and pauses comparable day to day.
const PASSAGE = 'When the sunlight strikes raindrops in the air, they act as a prism and form a rainbow. The rainbow is a division of white light into many beautiful colours.';
import { radius, space, usePalette } from '@/lib/theme';
import { LineChart } from '@/ui/charts';
import { Button, Card, Chip, Icon, Row, Screen, Section, Segmented, T, useToast } from '@/ui/core';
import { TelomyLoader } from '@/ui/loader';

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
  const rec = useAudioRecorder(WAV16);
  const sp = useSpeech();
  const [checkin, setCheckin] = useState<any>(null);
  const [mode, setMode] = useState<'talk' | 'checkin' | null>(null);
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

  async function toggle(m: 'talk' | 'checkin' = 'talk') {
    if (busy) return;
    if (!recording) {
      setMode(m);
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
      if (mode === 'checkin') {
        const features = await Band.voiceFeatures(uri, true);            // computed here, then the audio is deleted
        if (!features.f0_mean) throw new Error('Not enough voice — read the passage aloud at a normal pace.');
        const r = await api('/voice/command', { body: { text: '', features, source: 'checkin' } });
        setCheckin({ ...r, features }); stress.reload();
        return;
      }
      const local = await transcribeOnDevice(uri, sp.model, sp.lang).catch(() => null);
      if (local) {
        const features = await Band.voiceFeatures(uri, true);
        if (!local.text) throw new Error("Didn't catch any words — try again a little closer to the mic.");
        done(await api('/voice/command', { body: { text: local.text, language: local.language, features, source: 'voice-ondevice', model: local.model } }));
      } else {
        // no on-device model yet: Whisper on the Telomy server (audio is processed in memory, never stored)
        const form = new FormData();
        form.append('file', { uri, name: 'sinc.wav', type: 'audio/wav' } as any);
        const j = await api('/voice/audio', { form }).finally(() => Band.voiceFeatures(uri, true).catch(() => {}));
        done(j);
      }
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
        <Stack.Screen options={{ title: '' }} />
        <T v="h1">Talk to Sinc</T>
        <T v="small">Say anything, in any language — meals, drinks, cigarettes, coffee, how you feel, a workout, a therapy, a question, or your whole routine. Sinc logs it and answers.</T>
        <View style={{ alignItems: 'center', paddingVertical: 12, gap: 10 }}>
          {busy ? (
            <View style={{ height: 112, justifyContent: 'center' }}>
              <TelomyLoader size="hero" />
            </View>
          ) : (
            <Animated.View style={{ transform: [{ scale: pulse }] }}>
              <Pressable onPress={() => toggle('talk')} accessibilityRole="button" accessibilityLabel={recording ? 'Stop and send' : 'Start talking'} testID="mic"
                style={{ width: 112, height: 112, borderRadius: 56, alignItems: 'center', justifyContent: 'center', backgroundColor: recording ? p.copper : p.teal }}>
                <Icon name={recording ? 'stop.fill' : 'mic.fill'} size={40} color={p.onAccent} />
              </Pressable>
            </Animated.View>
          )}
          <T v="small">{busy ? (sp.ready[sp.model] ? 'Transcribing on this iPhone…' : 'Transcribing on your Telomy server…') : recording && mode === 'talk' ? 'Listening — tap to send' : 'Tap to talk'}</T>
          <Row>
            <Chip label={sp.ready[sp.model] ? `${MODELS[sp.model].label} · on this iPhone` : 'Whisper · Telomy server'} fg={p.teal} bg={p.tealSoft} />
            <Pressable onPress={() => setSpeak(!speak)} accessibilityRole="switch" accessibilityState={{ checked: speak }}>
              <Chip label={speak ? 'Sinc speaks replies' : 'Silent replies'} />
            </Pressable>
          </Row>
        </View>
        <Row>
          <TextInput value={text} onChangeText={setText} placeholder="…or type it" placeholderTextColor={p.faint} onSubmitEditing={() => send()} returnKeyType="send" testID="voice-text"
            style={{ flex: 1, borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'HankenGrotesk_400Regular' }} />
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

        <Section title="Voice check-in">
          <Card style={{ gap: space[2] }}>
            <T v="small">Read this aloud at your normal pace (about 15 seconds). Telomy measures pitch, steadiness, breathiness, speed and pauses on this iPhone, compares them with your own normal and fuses that with your HRV. The recording is deleted straight after.</T>
            <T v="body" style={{ fontStyle: 'italic' }}>“{PASSAGE}”</T>
            <Button title={recording && mode === 'checkin' ? 'Done reading' : 'Start check-in'} icon={recording && mode === 'checkin' ? 'stop.fill' : 'waveform'}
              onPress={() => toggle('checkin')} disabled={busy || (recording && mode !== 'checkin')} />
            {checkin?.stress?.score != null ? (
              <View style={{ gap: 4 }}>
                <Row><T v="label" style={{ flex: 1 }}>Voice stress</T><Chip label={`${checkin.stress.score} · ${checkin.stress.label}`} fg={checkin.stress.score >= 55 ? p.copper : p.teal} bg={p.surface} /></Row>
                <T v="small">{checkin.stress.basis}</T>
                <T v="small" color={p.muted}>Pitch {checkin.features.f0_mean} Hz · jitter {checkin.features.jitter_pct}% · HNR {checkin.features.hnr_db} dB · {checkin.features.rate_per_s} syllable bursts/s · pauses {Math.round((checkin.features.pause_ratio ?? 0) * 100)}%</T>
                <T v="small" color={p.faint}>{checkin.stress.note}</T>
              </View>
            ) : null}
          </Card>
        </Section>

        <Section title="On-device speech">
          <Card style={{ gap: space[2] }}>
            <T v="small">{sp.available ? 'Transcribe on this iPhone with Whisper (Cactus engine): works offline, nothing you say leaves the phone. Download a model once.' : 'On-device speech needs the iPhone app; using the Telomy server.'}</T>
            {sp.available ? (
              <>
                {(Object.keys(MODELS) as SpeechModel[]).map((m) => (
                  <Row key={m}>
                    <Pressable style={{ flex: 1 }} onPress={() => sp.setModel(m)} accessibilityRole="radio" accessibilityState={{ checked: sp.model === m }}>
                      <T v="h3" color={sp.model === m ? p.teal : p.text}>{sp.model === m ? '● ' : '○ '}{MODELS[m].label}</T>
                      <T v="small">{MODELS[m].note} · {MODELS[m].mb} MB</T>
                    </Pressable>
                    {sp.ready[m] ? <Chip label="Ready" fg={p.success} bg={p.surface} />
                      : <Button kind="secondary" title={sp.progress != null ? `${Math.round(sp.progress * 100)}%` : 'Download'} disabled={sp.progress != null} onPress={() => sp.download(m)} />}
                  </Row>
                ))}
                <Segmented options={[{ key: 'auto', label: 'Any language' }, { key: 'en', label: 'English' }, { key: 'hi', label: 'हिंदी' }]} value={sp.lang} onChange={sp.setLang} />
                {sp.error ? <T v="small" color={p.danger}>{sp.error}</T> : null}
              </>
            ) : null}
          </Card>
        </Section>

        <Section title="Voice tone over time">
          <Card>
            {(() => {
              const samples = (stress.data?.samples ?? []).filter((s: any) => s.stress != null);
              const latest = samples.length ? samples[samples.length - 1].stress : null;
              return (
                <>
                  <Row style={{ alignItems: 'center' }}>
                    <T v="body" style={{ flex: 1 }}>{stress.data?.n ?? 0} voice samples{stress.data?.baseline_ready ? '' : ' · baseline after 5'}</T>
                    {latest != null ? <Chip label={`latest ${latest}`} fg={latest >= 55 ? p.copper : p.teal} bg={latest >= 55 ? p.copperSoft : p.tealSoft} /> : null}
                  </Row>
                  {samples.length >= 2 ? (
                    <LineChart points={samples.map((s: any) => ({ x: s.ts, y: s.stress }))} height={130} unit="/100" band={[0, 55]} dots />
                  ) : <T v="small" color={p.muted} style={{ marginTop: 6 }}>Talk to Sinc or do a read-aloud check-in a few times and your voice-tone trend appears here.</T>}
                  <T v="small" color={p.muted} style={{ marginTop: 6 }}>{stress.data?.how}</T>
                </>
              );
            })()}
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
