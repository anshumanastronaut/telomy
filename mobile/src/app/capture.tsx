// Therapy Capture: record a therapy session with the ECG band, fully on the phone (no server needed).
// Raw ECG, beats, HR/HRV, quality and rhythm events are saved locally and can be shared with the research team.
import { router, Stack } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { AppState, Pressable, TextInput, View } from 'react-native';
import { acquireStream, Band, bandAvailable, useBand } from '@/lib/band';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Empty, Row, Screen, Section, T, useToast } from '@/ui/core';
import { BeatHeart, EcgMonitor, HrTrend } from '@/ui/ecg';

type Field = { key: string; label: string; unit: string };
type Therapy = { id: string; name: string; fields: Field[]; caution?: string; blocked?: string };

const TEMP: Field = { key: 'temperature_c', label: 'Temperature', unit: '°C' };
const DUR: Field = { key: 'planned_min', label: 'Planned time', unit: 'min' };
const THERAPIES: Therapy[] = [
  { id: 'cryo', name: 'Whole-body cryotherapy', fields: [TEMP, { key: 'planned_sec', label: 'Planned time', unit: 's' }],
    caution: 'Cold and wet electrodes can cause frostbite at −110 °C and below. Use the band only if the centre allows it, keep electrodes dry, and remove it if skin hurts.' },
  { id: 'local_cryo', name: 'Local cryotherapy', fields: [TEMP, DUR, { key: 'area', label: 'Body area', unit: '' }] },
  { id: 'cold_plunge', name: 'Cold plunge', fields: [TEMP, DUR], caution: 'The band is not waterproof. Keep the sensor above water or use a waterproof cover.' },
  { id: 'sauna', name: 'Finnish sauna', fields: [TEMP, DUR, { key: 'humidity_pct', label: 'Humidity', unit: '%' }], caution: 'Above 80 °C the snaps can get hot. Stop if the skin under the strap burns.' },
  { id: 'ir_sauna', name: 'Infrared sauna', fields: [TEMP, DUR] },
  { id: 'contrast', name: 'Contrast (hot ↔ cold)', fields: [{ key: 'hot_c', label: 'Hot', unit: '°C' }, { key: 'cold_c', label: 'Cold', unit: '°C' }, { key: 'rounds', label: 'Rounds', unit: '' }] },
  { id: 'red_light', name: 'Red / near-infrared light', fields: [DUR, { key: 'wavelength_nm', label: 'Wavelength', unit: 'nm' }, { key: 'irradiance_mw_cm2', label: 'Irradiance', unit: 'mW/cm²' }] },
  { id: 'pemf', name: 'PEMF', fields: [DUR, { key: 'frequency_hz', label: 'Frequency', unit: 'Hz' }, { key: 'intensity', label: 'Intensity', unit: '' }] },
  { id: 'compression', name: 'Compression boots', fields: [DUR, { key: 'pressure_mmhg', label: 'Pressure', unit: 'mmHg' }] },
  { id: 'vibroacoustic', name: 'Vibroacoustic therapy', fields: [DUR, { key: 'frequency_hz', label: 'Frequency', unit: 'Hz' }] },
  { id: 'hydrogen', name: 'Molecular hydrogen inhalation', fields: [DUR, { key: 'flow_ml_min', label: 'Flow', unit: 'mL/min' }] },
  { id: 'iv', name: 'IV drip', fields: [DUR, { key: 'formula', label: 'Formula', unit: '' }, { key: 'volume_ml', label: 'Volume', unit: 'mL' }] },
  { id: 'float', name: 'Flotation', fields: [DUR], caution: 'Keep the sensor out of the salt water.' },
  { id: 'sleep', name: 'Overnight sleep', fields: [{ key: 'bedtime_note', label: 'Anything unusual today', unit: '' }],
    caution: 'Wet the electrodes, charge the band, and plug in the phone. Keep the phone within ~3 m of the bed with Bluetooth on. You can lock the phone; the app keeps recording.' },
  { id: 'hbot', name: 'Hyperbaric oxygen (HBOT)', fields: [], blocked: "Don't wear this band in a hyperbaric chamber. Its manual forbids use in oxygen-rich or pressurised environments (fire risk; rated only to 1060 hPa)." },
  { id: 'breathwork', name: 'Breathwork', fields: [DUR, { key: 'pattern', label: 'Pattern', unit: '' }] },
  { id: 'exercise', name: 'Exercise', fields: [DUR, { key: 'type', label: 'Type', unit: '' }] },
  { id: 'other', name: 'Other', fields: [DUR, { key: 'description', label: 'What', unit: '' }] },
];
const PHASES = [
  { key: 'baseline', label: 'Baseline', hint: 'Sit still 3–5 min before' },
  { key: 'therapy', label: 'In therapy', hint: 'Entering the machine' },
  { key: 'recovery', label: 'Recovery', hint: 'Out of the machine' },
];
const SLEEP_PHASES = [
  { key: 'baseline', label: 'In bed', hint: 'Reading, winding down' },
  { key: 'therapy', label: 'Lights out', hint: 'Trying to sleep' },
  { key: 'recovery', label: 'Awake', hint: 'Up for the day' },
];
const RATINGS = ['energy', 'calm', 'pain', 'sleepiness'] as const;

function Scale({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const p = usePalette();
  return (
    <View style={{ gap: 4 }}>
      <T v="small">{label[0].toUpperCase() + label.slice(1)} · {value}/10</T>
      <Row gap={4}>
        {Array.from({ length: 11 }, (_, i) => (
          <Pressable key={i} onPress={() => onChange(i)} accessibilityLabel={`${label} ${i}`}
            style={{ flex: 1, height: 30, borderRadius: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: i === value ? p.teal : p.surfaceAlt }}>
            <T v="small" color={i === value ? p.onAccent : p.text}>{i}</T>
          </Pressable>
        ))}
      </Row>
    </View>
  );
}

export default function Capture() {
  const p = usePalette();
  const b = useBand();
  const { toast, show } = useToast();
  const [therapy, setTherapy] = useState<Therapy | null>(null);
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [pre, setPre] = useState<Record<string, number>>({ energy: 5, calm: 5, pain: 0, sleepiness: 3 });
  const [post, setPost] = useState<Record<string, number>>({ energy: 5, calm: 5, pain: 0, sleepiness: 3 });
  const [notes, setNotes] = useState('');
  const [mark, setMark] = useState('');
  const [phase, setPhase] = useState<string | null>(null);
  const [phaseAt, setPhaseAt] = useState(0);
  const [startedAt, setStartedAt] = useState(0);
  const [running, setRunning] = useState(!!Band.captureId());
  const [, tick] = useState(0);
  const release = useRef<null | (() => void)>(null);
  const phases = therapy?.id === 'sleep' ? SLEEP_PHASES : PHASES;

  // the app may have been relaunched mid-session (e.g. overnight): restore the screen from the native capture
  useEffect(() => {
    const meta = Band.captureMeta();
    if (!meta) return;
    setTherapy(THERAPIES.find((t) => t.id === meta.therapyId) ?? null);
    setSettings(meta.settings ?? {}); setPre(meta.pre ?? pre);
    setStartedAt(meta.startedAt ?? 0);
    const last = [...(meta.phases ?? [])].reverse().find((x: any) => x.phase !== 'marker');
    if (last) { setPhase(last.phase); setPhaseAt(last.t); }
    setRunning(true);
  }, []);

  useEffect(() => {
    if (!bandAvailable) return;
    release.current = acquireStream();
    const h = setInterval(() => { if (AppState.currentState === 'active') tick((x) => x + 1); }, 1000);
    return () => { clearInterval(h); release.current?.(); };
  }, []);

  if (!bandAvailable) return <Screen edges={[]}><Stack.Screen options={{ title: 'Therapy capture' }} /><Empty title="Needs the Telomy app" body="Therapy capture uses the ECG band through Telomy's native app." /></Screen>;

  const m = b.metrics;
  const connected = b.status?.state === 'streaming' || b.status?.state === 'connected';
  const now = Date.now() / 1000;
  const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

  function start() {
    if (!therapy) return;
    const r = Band.startCapture({ therapy: therapy.name, therapyId: therapy.id, settings, pre, firstPhase: 'baseline', tz: Intl.DateTimeFormat().resolvedOptions().timeZone });
    if (r.error) return show(r.error, 'alert');
    // No band-memory backup: firmware B1_1.00.39 stores little or nothing when its memory recording and the live stream
    // are mixed (dry runs 2026-10-12/13). The live stream is the reliable path; the session survives app relaunches.
    setRunning(true); setPhase('baseline'); setPhaseAt(now); setStartedAt(now);
  }
  function setPh(k: string) { Band.markPhase(k); setPhase(k); setPhaseAt(now); }
  function addMark() { if (!mark.trim()) return; Band.markPhase('marker', mark.trim()); show('Marked.', 'success'); setMark(''); }
  function finish() {
    const r = Band.stopCapture({ post, notes, settings });
    setRunning(false);
    if (r.error) return show(r.error, 'alert');
    if (therapy?.id === 'sleep') return router.replace('/wellness/sleep');  // analysed there (on the phone), then shown
    show('Session saved on this phone.', 'success');
    router.replace('/captures');
  }

  // ----- setup
  if (!running) {
    return (
      <View style={{ flex: 1 }}>
        <Screen edges={[]}>
          <Stack.Screen options={{ title: 'Therapy capture' }} />
          <T v="h1">Record a therapy session</T>
          <T v="small">Everything is saved on this phone, so it works without internet at the centre. Share sessions with your team from Saved sessions.</T>
          <Card tone={connected ? 'teal' : 'copper'} onPress={() => router.push('/monitor')}>
            <Row>{connected ? <BeatHeart lastBeatAt={b.lastBeatAt} /> : null}
              <T v="h3" style={{ flex: 1 }}>{connected ? `Band connected · ${m?.hr ? Math.round(m.hr) + ' bpm' : 'reading…'}` : 'Connect the ECG band first'}</T></Row>
            <T v="small">{connected ? `Signal: ${m?.signal ?? '…'} · battery ${b.status?.battery ?? '–'}` : 'Tap to open Live ECG and pair the band.'}</T>
          </Card>
          <Section title="Therapy">
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {THERAPIES.map((t) => (
                <Pressable key={t.id} onPress={() => setTherapy(t)} accessibilityRole="button" accessibilityState={{ selected: therapy?.id === t.id }}>
                  <Chip label={t.name} fg={therapy?.id === t.id ? p.onAccent : p.text} bg={therapy?.id === t.id ? p.teal : p.surfaceAlt} />
                </Pressable>
              ))}
            </View>
          </Section>
          {therapy?.blocked ? <Card tone="copper"><T v="h3">Not with this band</T><T v="body">{therapy.blocked}</T></Card> : null}
          {therapy && !therapy.blocked ? (
            <>
              {therapy.caution ? <Card tone="copper"><T v="body">⚠︎ {therapy.caution}</T></Card> : null}
              <Section title="Machine settings">
                <Card style={{ gap: space[2] }}>
                  {therapy.fields.map((f) => (
                    <Row key={f.key}>
                      <T v="body" style={{ flex: 1 }}>{f.label}</T>
                      <TextInput value={settings[f.key] ?? ''} onChangeText={(v) => setSettings({ ...settings, [f.key]: v })} placeholder={f.unit || 'value'}
                        keyboardType={f.unit ? 'numbers-and-punctuation' : 'default'} placeholderTextColor={p.faint}
                        style={{ minWidth: 120, textAlign: 'right', color: p.text, borderBottomWidth: 1, borderColor: p.border, paddingVertical: 6, fontSize: 16 }} />
                      {f.unit ? <T v="small">{f.unit}</T> : null}
                    </Row>
                  ))}
                </Card>
              </Section>
              <Section title="How do you feel before?">
                <Card style={{ gap: space[3] }}>{RATINGS.map((k) => <Scale key={k} label={k} value={pre[k]} onChange={(v) => setPre({ ...pre, [k]: v })} />)}</Card>
              </Section>
              <Button title="Start recording" icon="record.circle" disabled={!connected} onPress={start} />
              {!connected ? <T v="small">Connect the band to start.</T> : null}
            </>
          ) : null}
          <Button kind="ghost" title="Saved sessions" icon="folder" onPress={() => router.push('/captures')} />
        </Screen>
        {toast}
      </View>
    );
  }

  // ----- live
  const id = Band.captureId();
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: therapy?.name ?? 'Recording' }} />
        <Card tone="teal">
          <Row>
            <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: p.danger }} />
            <T v="h3" style={{ flex: 1 }}>Recording · {startedAt ? mmss(now - startedAt) : '–'}</T>
            <Chip label={id ?? ''} />
          </Row>
          <T v="small">{phase ? `${phases.find((x) => x.key === phase)?.label ?? phase} for ${mmss(now - phaseAt)}` : ''} · keeps recording with the screen locked</T>
        </Card>
        <Card>
          <Row style={{ alignItems: 'flex-end' }}>
            <BeatHeart lastBeatAt={b.lastBeatAt} size={28} />
            <T v="numLg">{m?.hr ? Math.round(m.hr) : '–'}</T>
            <T v="body" color={p.muted} style={{ marginBottom: 10 }}>bpm</T>
            <View style={{ flex: 1 }} />
            <View style={{ alignItems: 'flex-end', marginBottom: 6 }}>
              <T v="label">HRV</T>
              <T v="num">{m?.rmssdSmooth ? Math.round(m.rmssdSmooth) : '–'} <T v="small">ms</T></T>
            </View>
          </Row>
          <T v="small">Signal {m?.signal ?? '–'} · {m?.activity ?? '–'} · confidence {m?.hrConfidence ?? '–'}</T>
        </Card>
        {b.status?.liveBlockedByRecording ? (
          <Card tone="teal">
            <T v="h3">Recording on the band</T>
            <T v="body">The band is saving the full night to its own memory, so the live graph pauses (the band can't do both at once). You can lock the phone or even leave it in another room. In the morning tap Stop: the night syncs to the phone and is analysed.</T>
          </Card>
        ) : <EcgMonitor live height={150} />}
        <Section title="Phase">
          <Row gap={8}>
            {phases.map((ph) => (
              <Pressable key={ph.key} onPress={() => setPh(ph.key)} style={{ flex: 1 }} accessibilityRole="button" accessibilityState={{ selected: phase === ph.key }}>
                <View style={{ padding: 12, borderRadius: radius.md, backgroundColor: phase === ph.key ? p.copper : p.surfaceAlt, alignItems: 'center' }}>
                  <T v="h3" color={phase === ph.key ? p.onAccent : p.text}>{ph.label}</T>
                  <T v="small" color={phase === ph.key ? p.onAccent : p.muted}>{ph.hint}</T>
                </View>
              </Pressable>
            ))}
          </Row>
          <Button kind="secondary" icon="plus.circle" title="Log event · meal, supplement, drink, smoke…" onPress={() => router.push('/event')} />
          <Row>
            <TextInput value={mark} onChangeText={setMark} placeholder="Quick note (e.g. felt dizzy, door opened)" placeholderTextColor={p.faint}
              style={{ flex: 1, color: p.text, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10 }} />
            <Button kind="secondary" title="Mark" onPress={addMark} />
          </Row>
        </Section>
        <Section title="Heart rate this session"><Card><HrTrend hr={b.hr.filter((x) => x.t >= startedAt)} minutes={Math.max(2, Math.ceil((now - startedAt) / 60))} /></Card></Section>
        {b.rhythm.filter((e) => e.start >= startedAt).length ? (
          <Card tone="copper">{b.rhythm.filter((e) => e.start >= startedAt).map((e) => <T key={e.type + e.start} v="small">• {e.type.replace(/_/g, ' ')} at {new Date(e.start * 1000).toLocaleTimeString()}</T>)}</Card>
        ) : null}
        <Section title="How do you feel after?">
          <Card style={{ gap: space[3] }}>{RATINGS.map((k) => <Scale key={k} label={k} value={post[k]} onChange={(v) => setPost({ ...post, [k]: v })} />)}</Card>
          <TextInput value={notes} onChangeText={setNotes} placeholder="Notes for the team" multiline placeholderTextColor={p.faint}
            style={{ minHeight: 70, color: p.text, borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10 }} />
        </Section>
        <Button kind="danger" title={therapy?.id === 'sleep' ? 'Good morning — stop & analyse the night' : 'Stop & save session'} icon="stop.circle" onPress={finish} />
      </Screen>
      {toast}
    </View>
  );
}
