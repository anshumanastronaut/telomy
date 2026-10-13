// Live ECG monitor for the KY-E-B1 band: pairing, live ECG sweep, HR, HRV, signal quality, ECG strips, 24-h recording.
import { router, Stack } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';
import { api, fmtDate, useApi } from '@/lib/api';
import { acquireStream, Band, bandAvailable, clearDevices, ecg, useBand, type BandMetrics } from '@/lib/band';
import { space, usePalette } from '@/lib/theme';
import { Button, Card, Chip, Empty, Icon, ListRow, Row, Screen, Section, Segmented, Stat, T, useToast } from '@/ui/core';
import { BeatHeart, EcgMonitor, HrTrend, Tachogram } from '@/ui/ecg';

const QUALITY: Record<string, { label: string; tone: 'success' | 'warn' | 'danger' | 'muted'; hint: string }> = {
  good: { label: 'Signal good', tone: 'success', hint: 'Clean ECG. Heart rate and HRV are reliable.' },
  acceptable: { label: 'Signal fair', tone: 'warn', hint: 'Usable. Sit still for the cleanest HRV.' },
  poor: { label: 'Signal noisy', tone: 'danger', hint: 'Movement or loose contact. HRV is hidden until the signal settles.' },
  no_contact: { label: 'No skin contact', tone: 'danger', hint: 'Press the patch or strap firmly against the skin (left chest).' },
  warming_up: { label: 'Learning your signal', tone: 'muted', hint: 'Analysing the first 10 seconds…' },
};

const RHYTHM: Record<string, { label: string; tone: 'danger' | 'warn' | 'muted' }> = {
  af_pattern: { label: 'Irregular rhythm pattern (possible AF)', tone: 'danger' },
  pause: { label: 'Pause between beats over 2 s', tone: 'danger' },
  very_high_hr: { label: 'Very fast heart rate', tone: 'danger' },
  bradycardia: { label: 'Slow heart rate', tone: 'warn' },
  tachycardia_rest: { label: 'Fast heart rate at rest', tone: 'warn' },
  bigeminy: { label: 'Early beat every second beat', tone: 'warn' },
  trigeminy: { label: 'Early beat every third beat', tone: 'warn' },
  early_beats: { label: 'Frequent early beats', tone: 'warn' },
  poor_signal: { label: 'Long stretch of poor signal', tone: 'muted' },
};
const HRV_STATE: Record<string, string> = {
  settling: 'HRV appears after about 30 clean beats.',
  noisy: 'HRV paused: too much movement or noise. It resumes when you are still.',
  active: 'You are active, so HRV is lower than at rest. Compare HRV only at rest.',
  irregular: 'HRV paused: irregular rhythm detected, so HRV would be misleading.',
};
const ACTIVITY: Record<string, string> = { rest: 'At rest', light: 'Light activity', active: 'Active', moving: 'Moving', unknown: '' };

function fmt(v: number | undefined, d = 0) {
  return v == null ? '–' : v.toFixed(d);
}

export default function Monitor() {
  const p = usePalette();
  const b = useBand();
  const { toast, show } = useToast();
  const [gain, setGain] = useState<'1' | '2'>('1');
  const strips = useApi<any[]>('/band/strips', [b.frames > 0 ? Math.floor(b.frames / 200) : 0]);
  const s = b.status;
  const m: BandMetrics | null = b.metrics;
  const connected = s?.state === 'connected' || s?.state === 'streaming';

  // Stream live ECG while this screen is open; the band keeps recording on its own if 24-h mode is on.
  useEffect(() => {
    if (!bandAvailable) return;
    return acquireStream();
  }, []);

  if (!bandAvailable) {
    return (
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Live ECG' }} />
        <Empty title="ECG band needs the Telomy app" body="Live ECG uses Bluetooth through Telomy's native app. It isn't available in Expo Go or on the web." />
      </Screen>
    );
  }

  const tone = (t: string) => (t === 'success' ? [p.success, p.successSoft] : t === 'warn' ? [p.warn, p.warnSoft] : t === 'danger' ? [p.danger, p.dangerSoft] : [p.muted, p.surfaceAlt]);
  const q = QUALITY[m?.quality ?? (s?.leadOn === false ? 'no_contact' : 'warming_up')];
  const [qfg, qbg] = tone(q.tone);

  async function saveStrip() {
    const n = Math.min(ecg.end, 30 * 100);
    if (n < 1000) return show('Wear the band for at least 10 seconds first.', 'alert');
    const samples = Array.from({ length: n }, (_, k) => Math.round(ecg.at(ecg.end - n + k) * 10) / 10);
    try {
      await api('/band/strips', { body: { fs: 100, samples, hr: m?.hr, rmssd: m?.hrvReliable ? m.rmssd60 : undefined, quality: m?.quality, ts: new Date().toISOString().slice(0, 19) } });
      show(`Saved a ${Math.round(n / 100)}-second ECG.`, 'success');
      strips.reload();
    } catch (e: any) {
      show(e.message, 'alert');
    }
  }

  // ----- not paired yet / not connected
  if (!connected) {
    const remembered = s?.rememberedId;
    return (
      <View style={{ flex: 1 }}>
        <Screen edges={[]}>
          <Stack.Screen options={{ title: 'Live ECG' }} />
          <T v="h1">{remembered ? 'Reconnecting…' : 'Connect your ECG band'}</T>
          {remembered ? (
            <Card tone="teal">
              <Row><Icon name="antenna.radiowaves.left.and.right" color={p.teal} /><T v="h3" style={{ flex: 1 }}>{s?.rememberedName}</T><Chip label={s?.state === 'connecting' ? 'Looking for band' : s?.state ?? '…'} /></Row>
              <T v="body">Put the band on. It switches on when the electrodes touch your skin, and Telomy connects automatically.</T>
              <Row><Button kind="ghost" title="Use a different band" onPress={() => { Band.forget(); clearDevices(); }} /></Row>
            </Card>
          ) : (
            <>
              <Card>
                <T v="body">1. Snap the sensor into the chest strap or onto a fresh electrode patch.</T>
                <T v="body">2. Place it on the left side of your chest, below the chest muscle. It switches on by itself.</T>
                <T v="body">3. Tap Find band. Telomy remembers it and reconnects on its own from then on.</T>
              </Card>
              <Button title={s?.state === 'scanning' ? 'Searching…' : 'Find band'} icon="magnifyingglass" loading={s?.state === 'scanning'} onPress={() => { clearDevices(); Band.startScan(); }} />
              {b.devices.length ? (
                <Section title="Bands nearby">
                  <Card style={{ paddingVertical: 4 }}>
                    {b.devices.map((d) => (
                      <ListRow key={d.id} title={d.name} subtitle={`Signal ${d.rssi} dBm`} icon="waveform.path.ecg" onPress={() => Band.connect(d.id)} />
                    ))}
                  </Card>
                </Section>
              ) : null}
            </>
          )}
          {s?.state === 'off' ? <Card tone="copper"><T v="body">Bluetooth is off. Turn it on in Control Centre.</T></Card> : null}
          {s?.state === 'unauthorized' ? <Card tone="copper"><T v="body">Telomy doesn't have Bluetooth permission. Allow it in Settings → Telomy.</T></Card> : null}
          {s?.error ? <T v="small" color={p.danger}>{s.error}</T> : null}
        </Screen>
        {toast}
      </View>
    );
  }

  const rec = b.recording;
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'Live ECG' }} />
        <Row style={{ flexWrap: 'wrap' }}>
          <Chip label={s?.deviceName ?? 'ECG band'} icon="waveform.path.ecg" fg={p.teal} bg={p.tealSoft} />
          {s?.battery != null ? <Chip label={`Battery ${s.battery}`} icon="battery.50percent" /> : null}
          <Chip label={q.label} fg={qfg} bg={qbg} />
        </Row>

        <Card>
          <Row style={{ alignItems: 'flex-end' }}>
            <BeatHeart lastBeatAt={b.lastBeatAt} size={30} />
            <T v="numLg" color={m?.hrConfidence === 'low' ? p.muted : undefined} accessibilityLabel={`Heart rate ${fmt(m?.hr)} beats per minute`}>{fmt(m?.hr)}</T>
            <View style={{ marginBottom: 10 }}>
              <T v="body" color={p.muted}>bpm</T>
              {m?.hrSd != null ? <T v="small">± {Math.max(1, Math.round(m.hrSd))}</T> : null}
            </View>
            <View style={{ flex: 1 }} />
            <View style={{ alignItems: 'flex-end', marginBottom: 6 }}>
              <T v="label">HRV · RMSSD</T>
              <T v="num">{m?.rmssdSmooth != null && (m.hrvState === 'ok' || m.hrvState === 'active') ? fmt(m.rmssdSmooth) : '–'} <T v="small">ms</T></T>
            </View>
          </Row>
          <Row style={{ flexWrap: 'wrap' }}>
            {m?.activity && ACTIVITY[m.activity] ? <Chip label={ACTIVITY[m.activity]} icon="figure.walk" /> : null}
            {m?.sleep === 'asleep' ? <Chip label="Asleep (estimated)" icon="moon.zzz" /> : null}
            {m?.signal && m.signal !== 'clean' ? <Chip label={m.signal === 'motion' ? 'Movement in signal' : m.signal === 'noisy' ? 'Noisy signal' : m.signal.replace('_', ' ')} fg={p.warn} bg={p.warnSoft} /> : null}
            {m?.restingHr ? <Chip label={`Your resting ≈ ${Math.round(m.restingHr)} bpm`} /> : null}
          </Row>
          <T v="small">{m?.hrConfidence === 'low' ? 'Holding the last reliable value while the signal is noisy.' : q.hint}</T>
        </Card>

        <Card style={{ gap: space[2] }}>
          <Row>
            <T v="label" style={{ flex: 1 }}>Live ECG · lead I-like · 100 Hz</T>
            <Segmented options={[{ key: '1', label: '×1' }, { key: '2', label: '×2' }]} value={gain} onChange={setGain} />
          </Row>
          <EcgMonitor live gain={Number(gain)} />
          <Row>
            <Button kind="secondary" icon="square.and.arrow.down" title="Save 30-s ECG" onPress={saveStrip} style={{ flex: 1 }} />
          </Row>
        </Card>

        <Section title="Heart rate variability">
          <Card>
            <Row>
              <Stat label="RMSSD · 1 min" value={m?.hrvReliable ? fmt(m.rmssd60) : '–'} unit="ms" />
              <Stat label="RMSSD · 5 min" value={fmt(m?.rmssd300)} unit="ms" />
              <Stat label="SDNN · 1 min" value={m?.hrvReliable ? fmt(m.sdnn60) : '–'} unit="ms" />
            </Row>
            <Row>
              <Stat label="pNN50" value={m?.hrvReliable ? fmt(m.pnn50) : '–'} unit="%" />
              <Stat label="Mean RR" value={fmt(m?.meanNN60)} unit="ms" />
              <Stat label="Corrected beats" value={fmt(m?.artefactPercent, 1)} unit="%" sub={m?.irregularBeats60 ? `${m.irregularBeats60} early beats` : undefined} />
            </Row>
            {m?.hrvState && HRV_STATE[m.hrvState] ? <T v="small">{HRV_STATE[m.hrvState]}</T> : null}
            {m?.rmssdSmooth != null && m.hrvState === 'ok' ? <T v="small">Smoothed HRV (shown at the top) {fmt(m.rmssdSmooth)} ms tracks the 1-min value with a ~30 s time constant.</T> : null}
          </Card>
        </Section>

        <Button title="Record a therapy session" icon="record.circle" kind="copper" onPress={() => router.push('/capture')} />

        <Section title="Rhythm check">
          <Card style={{ gap: 6 }}>
            {b.rhythm.length ? b.rhythm.slice().reverse().slice(0, 8).map((e) => {
              const r = RHYTHM[e.type] ?? { label: e.type, tone: 'muted' as const };
              const [fg, bg] = tone(r.tone === 'danger' ? 'danger' : r.tone === 'warn' ? 'warn' : 'muted');
              return (
                <Row key={e.type + e.start}>
                  <Chip label={r.label} fg={fg} bg={bg} />
                  <T v="small" style={{ flex: 1, textAlign: 'right' }}>{new Date(e.start * 1000).toLocaleTimeString()}{e.end - e.start > 1 ? ` · ${Math.round((e.end - e.start) / 60) || '<1'} min` : ''}</T>
                </Row>
              );
            }) : <T v="body">No rhythm flags this session.</T>}
            <T v="small">Early beats {fmt(m?.earlyBeatsPerMin, 1)}/min · irregular-pattern time {Math.round((m?.afBurden60 ?? 0) * 100)} % of the last hour.</T>
            <T v="small" color={p.muted}>Screening for wellness, not a diagnosis. A single-lead wearable can't confirm atrial fibrillation or other conditions; repeated flags are worth a 12-lead ECG with your doctor.</T>
          </Card>
        </Section>

        <Section title="Beat to beat">
          <Card><Tachogram rr={b.rr} /><T v="small">Each dot is one heartbeat interval. A slow wave that rises as you breathe out is healthy respiratory sinus arrhythmia.</T></Card>
        </Section>

        <Section title="Heart rate · last 30 min">
          <Card><HrTrend hr={b.hr} /></Card>
        </Section>

        <Section title="24-hour recording">
          <Card style={{ gap: space[2] }}>
            <T v="body">The band can record by itself (up to 24 h) without your phone nearby. Sync to bring it into Telomy.</T>
            <T v="small">Band: {s?.holterState ?? 'unknown'}{s?.holterStart ? ` · started ${new Date(s.holterStart * 1000).toLocaleTimeString()}` : ''}</T>
            <Row style={{ flexWrap: 'wrap' }}>
              <Button kind="secondary" title="Start" icon="record.circle" onPress={() => { Band.startRecording(); show('Recording on the band.', 'success'); }} />
              <Button kind="secondary" title="Stop" icon="stop.circle" onPress={() => Band.stopRecording()} />
              <Button kind="primary" title="Sync" icon="arrow.down.circle" onPress={() => Band.syncRecording()} />
            </Row>
            {rec ? (
              <T v="small">
                {rec.phase === 'started' ? `Syncing ${rec.total} frames…` : rec.phase === 'progress' ? `Syncing ${Math.round((100 * rec.received) / Math.max(1, rec.total))} %` : rec.phase === 'failed' ? `Sync failed: ${rec.message}` : rec.phase === 'analysing' ? `Analysing ${Math.round(rec.frames * 0.87 / 60)} min of ECG…` :
                  `Synced ${Math.round((rec.durationSec ?? 0) / 60)} min · ${rec.beats ?? 0} beats · mean ${fmt(rec.meanHr)} bpm · RMSSD ${fmt(rec.rmssd)} ms`}
              </T>
            ) : null}
            {rec?.phase === 'completed' && rec.sleep ? (
              <T v="body">Night (band backup): slept {Math.floor(rec.sleep.totalSleepMin / 60)} h {Math.round(rec.sleep.totalSleepMin % 60)} min · efficiency {Math.round(rec.sleep.efficiency * 100)}% · {rec.sleep.awakenings} awakenings{rec.sleep.sleepHr ? ` · sleeping HR ${Math.round(rec.sleep.sleepHr)}` : ''}{rec.sleep.sleepRmssd ? ` · HRV ${Math.round(rec.sleep.sleepRmssd)} ms` : ''}. Estimate from heart rhythm, not a sleep study.{rec.captureId ? ' Added to your Overnight sleep session (Saved sessions → Share).' : ''}</T>
            ) : null}
          </Card>
        </Section>

        {strips.data?.length ? (
          <Section title="Saved ECGs">
            <Card style={{ paddingVertical: 4 }}>
              {strips.data.slice(0, 8).map((x) => (
                <ListRow key={x.id} title={`${fmtDate(x.ts)} · ${x.ts.slice(11, 16)}`} subtitle={`${Math.round(x.duration_s)} s · ${x.hr ? `${Math.round(x.hr)} bpm` : '–'} · ${QUALITY[x.quality]?.label ?? ''}`}
                  icon="waveform.path.ecg" onPress={() => router.push(`/ecg/${x.id}`)} />
              ))}
            </Card>
          </Section>
        ) : null}

        <Section title="How Telomy reads your ECG">
          <Card>
            <T v="small">Filtering: 200 + 600 ms median baseline removal, 40 Hz low-pass (AHA monitoring band; also removes 50 Hz mains at 100 Hz sampling).</T>
            <T v="small">Beats: Pan–Tompkins QRS detection with search-back and T-wave rejection; R peak refined by parabolic interpolation (Task Force 1996).</T>
            <T v="small">Quality: two independent detectors must agree (bSQI {fmt(m?.sqi?.bSQI, 2)}), kurtosis {fmt(m?.sqi?.kSQI, 1)}, QRS power {fmt(m?.sqi?.pSQI, 2)}, baseline {fmt(m?.sqi?.basSQI, 2)}.</T>
            <T v="small">HRV: Lipponen–Tarvainen artefact correction, then time-domain HRV only (100 Hz is too coarse for frequency-domain HRV).</T>
            <T v="small">Band {s?.hardware} · firmware {s?.firmware} · {s?.sampleRate} Hz · {s?.droppedFrames ?? 0} frames lost</T>
          </Card>
          <T v="small" color={p.muted}>Wellness reading, not a diagnosis. This band is a single-lead monitor: if you feel chest pain, faintness or a racing heart, seek medical care.</T>
          <Row><Button kind="ghost" title="Disconnect band" onPress={() => Band.disconnect()} /><Button kind="ghost" title="Forget band" onPress={() => Band.forget()} /></Row>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
