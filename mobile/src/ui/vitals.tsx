// "Telomy is watching" — the heart of Home. Row 1 is the heart: the live ECG waveform (or your recent heart-rate
// trend) with the current heart rate. Below, an ADAPTIVE grid: only signals that have a real value are shown —
// live first, otherwise the latest reading with when it was taken — chosen from a priority list and always in full
// rows of three, so the screen never shows an empty "Connect" slot. Connect more devices and better signals fill in.
import { router } from 'expo-router';
import { SFSymbol } from 'expo-symbols';
import React from 'react';
import { Pressable, View } from 'react-native';
import { Band, bandAvailable, useBand } from '@/lib/band';
import { useDevices, type SourceId } from '@/lib/devices';
import { useHealth } from '@/lib/health';
import { useRingHistory } from '@/lib/ringhistory';
import { data, radius, space, type, usePalette } from '@/lib/theme';
import { fmtDur, useWellness } from '@/lib/wellness';
import { BeatHeart, EcgMonitor, HrTrend } from '@/ui/ecg';
import { Icon, Row, T } from '@/ui/core';

type Reading = { v: number | null; src?: string; live: boolean };
type Tile = { key: string; icon: SFSymbol; label: string; value: string | null; unit?: string; color: string; source?: string; live: boolean; to: string };
const SHORT: Record<SourceId, string> = { patch: 'Patch', ring: 'Ring', health: 'Health' };
const fmt = (v: number | null | undefined, d = 0) => (v == null ? null : d ? v.toFixed(d) : Math.round(v).toLocaleString('en-IN'));
/** "now", "12 min ago", "3h ago", "yesterday", "Tue" — when a fallback reading was taken. */
export function ago(tSec: number) {
  const m = (Date.now() / 1000 - tSec) / 60;
  if (m < 2) return 'now'; if (m < 60) return `${Math.round(m)} min ago`; if (m < 24 * 60) return `${Math.round(m / 60)}h ago`;
  if (m < 48 * 60) return 'yesterday';
  return new Date(tSec * 1000).toLocaleDateString('en-GB', { weekday: 'short' });
}

export function VitalsGrid({ title = 'Telomy is watching' }: { title?: string }) {
  const p = usePalette();
  const d = useDevices();
  const b = useBand();
  const h = useHealth(7);
  const w = useWellness(null);
  const rh = useRingHistory();
  const streaming = b.status?.state === 'streaming';

  // ---- latest-value resolvers: live first, then history with "when"
  const src = (k: string) => { const s = d.live[k]?.source; return s ? SHORT[s] : undefined; };
  const ringLast = (k: 'hr' | 'hrv' | 'spo2' | 'temp') => { const x = [...rh.last24h].reverse().find((r) => r[k] != null); return x ? { v: x[k] as number, t: x.t / 1000 } : null; };
  const healthLast = (k: string) => { const dd: any = [...(h.data ?? [])].reverse().find((x: any) => x[k] != null); return dd ? { v: dd[k] as number, t: new Date(dd.date + 'T12:00:00').getTime() / 1000 } : null; };
  const caps = bandAvailable ? (Band.listCaptures() as any[]).filter((c) => c.summary).sort((a, z) => z.startedAt - a.startedAt) : [];
  const capLast = (k: string) => { const c = caps.find((x) => x.summary?.[k] != null); return c ? { v: c.summary[k] as number, t: (c.endedAt ?? c.startedAt) as number } : null; };
  const ringNow = (v?: number) => (v != null && v > 0 ? { v, t: Date.now() / 1000 } : null);   // last value the ring sent this session
  const pick = (live: number | null | undefined, liveSrc: string | undefined, ...fb: [string, { v: number; t: number } | null][]): Reading => {
    if (live != null) return { v: live, src: liveSrc, live: true };
    for (const [name, f] of fb) if (f) return { v: f.v, src: `${name} · ${ago(f.t)}`, live: false };
    return { v: null, live: false };
  };
  const nightEnd = w.last?.end;
  const fromNight = (v?: number | null) => (v != null && nightEnd ? { v, t: nightEnd } : null);

  const hr = pick(d.live.hr?.value, src('hr'), ['Ring', ringLast('hr')], ['Patch', capLast('meanHr')], ['Health', healthLast('restingHr')]);
  const hrv = pick(d.live.hrv?.value, src('hrv'), ['Patch', capLast('rmssd')], ['Ring', ringLast('hrv')], ['Health', healthLast('hrvSdnn')]);
  const spo2 = pick(d.live.spo2?.value, src('spo2'), ['Ring', ringLast('spo2')], ['Ring', ringNow(d.ring?.spo2)], ['Health', healthLast('spo2')]);
  const temp = pick(d.live.skinTemp?.value, src('skinTemp'), ['Ring', ringLast('temp')], ['Ring', ringNow(d.ring?.temp)]);
  const vo2h = pick(d.live.vo2max?.value, src('vo2max'), ['Health', healthLast('vo2max')]);
  const vo2: Reading = vo2h.v != null ? vo2h : w.vo2 ? { v: w.vo2, src: 'Estimated from resting HR', live: false } : vo2h;
  const resp = pick(null, undefined, ['Patch', fromNight(w.last?.respRate)], ['Health', healthLast('respRate')]);
  const steps = pick(d.live.steps?.value, src('steps'), ['Health', healthLast('steps')]);
  const rest: Reading = w.restingHr ? { v: w.restingHr, src: 'Patch · your baseline', live: false } : pick(null, undefined, ['Health', healthLast('restingHr')]);
  const lowest = pick(null, undefined, ['Patch', fromNight(w.last?.lowestHr)]);

  const T_ = (key: string, icon: SFSymbol, label: string, r: Reading, unit: string, color: string, to: string, dp = 0): Tile =>
    ({ key, icon, label, value: r.v == null ? null : fmt(r.v, dp), unit, color, source: r.src, live: r.live, to });
  // priority order — the grid takes the first nine that have a value
  const candidates: Tile[] = [
    T_('hrv', 'bolt.heart', 'HRV', hrv, 'ms', data.hrv, '/wellness/recovery'),
    { key: 'sleep', icon: 'moon.zzz', label: 'Sleep', value: w.last ? fmtDur(w.last.tstMin) : null, color: data.sleep, source: w.last ? `Last night · ${ago(w.last.end)}` : undefined, live: false, to: '/wellness/sleep' },
    T_('spo2', 'drop.fill', 'SpO₂', spo2, '%', data.spo2, '/ring'),
    T_('vo2', 'figure.run', 'VO₂max', vo2, '', data.activity, '/age'),
    T_('resp', 'lungs.fill', 'Breathing', resp, '/min', data.breath, '/wellness/sleep', 1),
    T_('temp', 'thermometer.medium', 'Skin temp', temp, '°C', data.temp, '/ring', 1),
    T_('steps', 'figure.walk', 'Steps', steps, '', data.activity, '/activity'),
    { key: 'recovery', icon: 'arrow.triangle.2.circlepath', label: 'Recovery', value: w.recovery.score != null ? `${w.recovery.score}` : null, unit: '%', color: data.recovery, source: w.recovery.label, live: false, to: '/wellness/recovery' },
    { key: 'strain', icon: 'flame.fill', label: 'Strain', value: w.today.worn >= 10 ? (Math.round(w.today.strain * 10) / 10).toFixed(1) : null, color: data.heart, source: `${w.today.activeMin} active min`, live: false, to: '/wellness/strain' },
    { key: 'stress', icon: 'waveform.path', label: 'Stress', value: w.today.stress.score != null ? `${w.today.stress.score}` : null, color: data.stress, source: 'Today', live: false, to: '/wellness/stress' },
    T_('rest', 'heart.text.square', 'Resting HR', rest, 'bpm', data.heart, '/wellness/recovery'),
    T_('lowest', 'arrow.down.heart', 'Night low HR', lowest, 'bpm', data.heart, '/wellness/sleep'),
    { key: 'risk', icon: 'shield.lefthalf.filled', label: 'Risk', value: 'View', color: p.teal, source: '5 disease models', live: false, to: '/predict' },
    { key: 'devices', icon: 'sensor.tag.radiowaves.forward', label: 'Devices', value: `${d.devices.filter((x) => x.connected).length}/${d.devices.length}`, color: p.graphite, source: 'Connected', live: d.anyConnected, to: '/devices' },
  ];
  const withValue = candidates.filter((x) => x.value != null);
  const shown = withValue.slice(0, Math.max(3, Math.min(9, Math.floor(withValue.length / 3) * 3)));
  const live = shown.filter((x) => x.live).length + (streaming ? 1 : 0);

  // ---- heart row: live ECG, else recent heart-rate trend (this session, then the last day of band minutes)
  const trend = b.hr.length >= 5 ? b.hr : w.today.minutes.filter((m) => m.hr).slice(-180).map((m) => ({ t: new Date(m.ts).getTime() / 1000, hr: m.hr }));
  const lastEcg = caps[0] ? (caps[0].endedAt ?? caps[0].startedAt) as number : null;

  return (
    <View style={{ gap: space[3], padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface }}>
      <View>
        <T v="h3">{title}</T>
        <T v="small">{live ? `${live} signal${live === 1 ? '' : 's'} live · the rest are your latest readings` : 'Your latest readings, kept up to date'}</T>
      </View>

      <Pressable onPress={() => router.push('/monitor')} accessibilityRole="button" accessibilityLabel={`Heart, ${hr.v != null ? Math.round(hr.v) : 'no reading'} beats per minute`}
        style={({ pressed }) => ({ padding: space[4], gap: space[2], borderRadius: radius.lg, backgroundColor: p.surfaceAlt, opacity: pressed ? 0.85 : 1 })}>
        <Row>
          <Icon name="waveform.path.ecg" size={14} color={data.heart} />
          <T v="label" style={{ flex: 1 }}>{streaming ? 'ECG · live' : 'Heart'}</T>
          {streaming ? <BeatHeart lastBeatAt={b.lastBeatAt} size={14} /> : null}
          <Row gap={4} style={{ alignItems: 'baseline' }}>
            <T v="num" style={{ fontSize: type.h1 }}>{hr.v != null ? Math.round(hr.v) : '—'}</T>
            <T v="small">bpm</T>
          </Row>
        </Row>
        {streaming ? <EcgMonitor live seconds={4} height={70} /> : trend.length >= 5 ? <HrTrend hr={trend} height={60} minutes={180} /> : null}
        <T v="small" style={{ fontSize: type.micro }} color={p.faint}>
          {streaming ? 'Patch · streaming now — tap for the full ECG' : `${hr.src ?? 'Wear the patch for a live ECG'}${lastEcg ? ` · last ECG ${ago(lastEcg)}` : ''}`}
        </T>
      </Pressable>

      <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -4 }}>
        {shown.map((x) => (
          <View key={x.key} style={{ width: '33.333%', padding: 4 }}>
            <Pressable onPress={() => router.push(x.to as any)} accessibilityRole="button" accessibilityLabel={`${x.label} ${x.value}`}
              style={({ pressed }) => ({ padding: space[3], gap: 3, borderRadius: radius.lg, backgroundColor: p.surfaceAlt, opacity: pressed ? 0.7 : 1, minHeight: 88 })}>
              <Row gap={5}>
                <Icon name={x.icon} size={12} color={x.color} />
                <T v="small" style={{ fontSize: type.micro, flex: 1 }} numberOfLines={1}>{x.label}</T>
                {x.live ? <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: p.success }} /> : null}
              </Row>
              <Row gap={2} style={{ alignItems: 'baseline' }}>
                <T v="num" style={{ fontSize: type.title }} numberOfLines={1} adjustsFontSizeToFit>{x.value}</T>
                {x.unit ? <T v="small" style={{ fontSize: type.micro }}>{x.unit}</T> : null}
              </Row>
              <T v="small" style={{ fontSize: type.micro }} color={p.faint} numberOfLines={1}>{x.source ?? ''}</T>
            </Pressable>
          </View>
        ))}
      </View>
    </View>
  );
}
