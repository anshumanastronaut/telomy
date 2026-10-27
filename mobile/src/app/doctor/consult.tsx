// Consult scribe — record or type the visit, generate a SOAP note + patient recap + action drafts, then sign
// (prescribe / order test / book follow-up / add task). Nothing is applied until the clinician taps apply.
import { Stack, useLocalSearchParams } from 'expo-router';
import { AudioQuality, IOSOutputFormat, requestRecordingPermissionsAsync, setAudioModeAsync, useAudioRecorder, type RecordingOptions } from 'expo-audio';
import React, { useState } from 'react';
import { TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { transcribeOnDevice, useSpeech } from '@/lib/speech';
import { space, usePalette } from '@/lib/theme';
import { BackButton, Button, Card, Chip, Row, Screen, Section, T, useToast } from '@/ui/core';

const WAV16: RecordingOptions = {
  extension: '.wav', sampleRate: 16000, numberOfChannels: 1, bitRate: 256000,
  android: { outputFormat: 'default', audioEncoder: 'default' },
  ios: { outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.MAX, linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  web: { mimeType: 'audio/webm', bitsPerSecond: 128000 },
};

type Action = { type: string; ref: string | null; label: string; detail: string; selected: boolean };

export default function Consult() {
  const { pid, name } = useLocalSearchParams<{ pid: string; name?: string }>();
  const p = usePalette();
  const { toast, show } = useToast();
  const sp = useSpeech();
  const rec = useAudioRecorder(WAV16);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [note, setNote] = useState<any>(null);
  const [sel, setSel] = useState<Record<number, boolean>>({});
  const [applied, setApplied] = useState<any[] | null>(null);

  async function toggleRec() {
    if (busy) return;
    if (!recording) {
      const perm = await requestRecordingPermissionsAsync();
      if (!perm.granted) { show('Microphone is off — enable it in Settings, or type below.', 'alert'); return; }
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await rec.prepareToRecordAsync(); rec.record(); setRecording(true); return;
    }
    setRecording(false); setBusy(true);
    try {
      await rec.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const uri = rec.uri; if (!uri) throw new Error('No audio captured.');
      const local = await transcribeOnDevice(uri, sp.model, sp.lang).catch(() => null);
      let text = local?.text ?? '';
      if (!text) {
        const form = new FormData(); form.append('file', { uri, name: 'consult.wav', type: 'audio/wav' } as any);
        const j = await api<any>('/voice/audio', { form }); text = j?.transcription?.text ?? j?.text ?? '';
      }
      if (!text) throw new Error("Didn't catch any words — try again closer to the mic, or type below.");
      setTranscript((t) => (t ? t + ' ' : '') + text);
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  async function generate() {
    if (transcript.trim().length < 20) { show('Record or type the visit first.', 'alert'); return; }
    setBusy(true); setApplied(null);
    try {
      const r = await api<any>(`/mgmt/clinic/patients/${pid}/consult`, { body: { transcript } });
      setNote(r);
      const init: Record<number, boolean> = {};
      (r.actions ?? []).forEach((a: Action, i: number) => { init[i] = !!a.selected; });
      setSel(init);
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  async function apply() {
    const indices = Object.keys(sel).filter((k) => sel[+k]).map(Number);
    if (!indices.length) { show('Select at least one item to apply.', 'alert'); return; }
    setBusy(true);
    try {
      const r = await api<any>(`/mgmt/clinic/patients/${pid}/consult/${note.id}/apply`, { body: { indices } });
      setApplied(r.applied ?? []);
      show(`Applied ${r.applied?.filter((x: any) => x.ok).length ?? 0} item(s).`, 'success');
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusy(false); }
  }

  const soap = note?.soap;
  const actions: Action[] = note?.actions ?? [];
  const tone = (t: string) => t === 'medication' ? { fg: p.teal, bg: p.tealSoft } : t === 'test' ? { fg: p.copper, bg: p.copperSoft } : t === 'followup' ? { fg: p.warn, bg: p.warnSoft } : { fg: p.muted, bg: p.surfaceAlt };

  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: '' }} />
      <BackButton fallback={`/doctor/patient/${pid}`} />
      <T v="h1">Consult scribe</T>
      <T v="small" color={p.muted}>{name ? `${name} · ` : ''}Record or type the visit. Sinc drafts a note, a patient recap and the actions — you review and sign.</T>

      <Card style={{ gap: space[2] }}>
        <Button kind={recording ? 'primary' : 'secondary'} icon={recording ? 'stop.fill' : 'waveform'}
          title={recording ? 'Stop & transcribe' : busy ? 'Working…' : 'Record the visit'} disabled={busy} onPress={toggleRec} />
        {sp.error ? <T v="small" color={p.danger}>{sp.error}</T> : null}
        <TextInput value={transcript} onChangeText={setTranscript} multiline placeholder="…or type / dictate the visit transcript here"
          placeholderTextColor={p.faint} style={{ borderWidth: 1, borderColor: p.border, borderRadius: 10, padding: 10, minHeight: 120, color: p.text, fontFamily: 'Geist_400Regular', textAlignVertical: 'top' }} />
        <Button kind="primary" title={busy && !note ? 'Generating…' : 'Generate note'} disabled={busy} onPress={generate} />
      </Card>

      {note ? (
        <>
          <Section title="SOAP note · Sinc draft">
            <Card style={{ gap: space[2] }}>
              {soap?.narrative ? <T v="body">{soap.narrative}</T> : (['subjective', 'objective', 'assessment', 'plan'] as const).map((k) => (
                <View key={k}>
                  <T v="label" color={p.muted}>{k[0].toUpperCase() + k.slice(1)}</T>
                  {(soap?.[k] ?? []).map((line: string, i: number) => <T key={i} v="small">• {line}</T>)}
                </View>
              ))}
            </Card>
          </Section>

          <Section title="Patient recap">
            <Card><T v="body">{note.recap}</T></Card>
          </Section>

          <Section title="Actions to sign">
            <Card style={{ gap: space[1] }}>
              {actions.length ? actions.map((a, i) => {
                const t = tone(a.type); const on = !!sel[i]; const done = applied?.find((x) => x.label === a.label);
                return (
                  <Row key={i} style={{ alignItems: 'flex-start' }} gap={10}>
                    <View onTouchEnd={() => !applied && setSel((s) => ({ ...s, [i]: !s[i] }))}
                      style={{ width: 20, height: 20, borderRadius: 6, borderWidth: 2, marginTop: 2, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.teal : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
                      {on ? <T v="small" color="#fff">✓</T> : null}
                    </View>
                    <View style={{ flex: 1 }}>
                      <T v="body" style={{ fontWeight: '600' }}>{a.label}</T>
                      {a.detail ? <T v="small" color={p.muted}>{a.detail}</T> : null}
                    </View>
                    {done ? <Chip label={done.ok ? 'applied ✓' : 'failed'} fg={done.ok ? p.teal : p.danger} bg={done.ok ? p.tealSoft : p.dangerSoft} /> : <Chip label={a.type} fg={t.fg} bg={t.bg} />}
                  </Row>
                );
              }) : <T v="small" color={p.muted}>No actions detected — the note and recap are saved to the patient's record.</T>}
              {actions.length && !applied ? <Button kind="primary" title={busy ? 'Applying…' : 'Apply selected · sign'} disabled={busy} onPress={apply} style={{ marginTop: 6 }} /> : null}
              <T v="small" color={p.faint} style={{ marginTop: 4 }}>Medications become a signed Rx, tests are ordered, follow-ups and tasks go to your work queue. Nothing is applied until you sign.</T>
            </Card>
          </Section>
        </>
      ) : null}
      <View style={{ height: space[8] }} />
      {toast}
    </Screen>
  );
}
