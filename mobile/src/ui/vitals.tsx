// "Telomy is watching": every signal Telomy tracks, as one calm grid. Each tile = value in its data colour, the device
// it came from (small), and a live/paused dot; tapping goes one level deeper. Shared by Home and the Twin tab, so the
// two can never disagree. Values come from the multi-device fusion (best source wins, others kept for comparison).
import { router } from 'expo-router';
import { SFSymbol } from 'expo-symbols';
import React from 'react';
import { Pressable, View } from 'react-native';
import { useBand } from '@/lib/band';
import { useDevices, type SourceId } from '@/lib/devices';
import { useHealth } from '@/lib/health';
import { useRingHistory } from '@/lib/ringhistory';
import { Band, bandAvailable } from '@/lib/band';
import { data, radius, space, type, usePalette } from '@/lib/theme';
import { BeatHeart } from '@/ui/ecg';
import { Icon, Row, T } from '@/ui/core';

type Tile = { key: string; icon: SFSymbol; label: string; value: string | null; unit?: string; color: string; source?: string; live: boolean; to: string; soon?: boolean };
const SHORT: Record<SourceId, string> = { patch: 'Patch', ring: 'Ring', health: 'Health' };
const fmt = (v: number | null | undefined, d = 0) => (v == null ? null : d ? v.toFixed(d) : Math.round(v).toLocaleString('en-IN'));
/** "now", "12 min ago", "3h ago", "yesterday", "Tue" — when a fallback reading was taken. */
function ago(tSec: number) {
  const m = (Date.now() / 1000 - tSec) / 60;
  if (m < 2) return 'now'; if (m < 60) return `${Math.round(m)} min ago`; if (m < 24 * 60) return `${Math.round(m / 60)}h ago`;
  if (m < 48 * 60) return 'yesterday';
  return new Date(tSec * 1000).toLocaleDateString('en-GB', { weekday: 'short' });
}

export function VitalsGrid({ title = 'Telomy is watching' }: { title?: string }) {
  const p = usePalette();
  const d = useDevices();
  const b = useBand();
  const h = useHealth(2);
  const streaming = b.status?.state === 'streaming';
  const rh = useRingHistory();
  // latest value from history when nothing is live: ring flash log, last patch recording, last Apple Health day
  const ringLast = (k: 'hr' | 'hrv' | 'spo2' | 'temp') => { const x = [...rh.last24h].reverse().find((r) => r[k] != null); return x ? { v: x[k] as number, t: x.t / 1000 } : null; };
  const healthLast = (k: string) => { const days = [...(h.data ?? [])].reverse(); const dd: any = days.find((x: any) => x[k] != null); return dd ? { v: dd[k] as number, t: new Date(dd.date + 'T12:00:00').getTime() / 1000 } : null; };
  const caps = bandAvailable ? (Band.listCaptures() as any[]).filter((c) => c.summary).sort((a, b) => b.startedAt - a.startedAt) : [];
  const capLast = (k: string) => { const c = caps.find((x) => x.summary?.[k] != null); return c ? { v: c.summary[k] as number, t: (c.endedAt ?? c.startedAt) as number } : null; };
  const lastEcg = caps[0] ? (caps[0].endedAt ?? caps[0].startedAt) as number : null;
  /** live value if present, else the most recent reading with when it was taken */
  const pick = (live: number | null | undefined, liveSrc: string | undefined, ...fallbacks: [string, { v: number; t: number } | null][]) => {
    if (live != null) return { v: live, src: liveSrc, live: true };
    for (const [name, f] of fallbacks) if (f) return { v: f.v, src: `${name} · ${ago(f.t)}`, live: false };
    return { v: null as number | null, src: undefined, live: false };
  };
  const src = (k: string) => { const s = d.live[k]?.source; return s ? SHORT[s] : undefined; };
  const t = h.today;
  const hr = pick(d.live.hr?.value, src('hr'), ['Ring', ringLast('hr')], ['Patch', capLast('meanHr')], ['Health', healthLast('restingHr')]);
  const hrv = pick(d.live.hrv?.value, src('hrv'), ['Patch', capLast('rmssd')], ['Ring', ringLast('hrv')], ['Health', healthLast('hrvSdnn')]);
  const spo2 = pick(d.live.spo2?.value, src('spo2'), ['Ring', ringLast('spo2')], ['Health', healthLast('spo2')]);
  const temp = pick(d.live.skinTemp?.value, src('skinTemp'), ['Ring', ringLast('temp')]);
  const vo2 = pick(d.live.vo2max?.value, src('vo2max'), ['Health', healthLast('vo2max')]);
  const resp = pick(t?.respRate, t?.respRate != null ? 'Health' : undefined, ['Health', healthLast('respRate')]);
  const steps = pick(d.live.steps?.value, src('steps'), ['Health', healthLast('steps')]);
  const tile = (key: string, icon: SFSymbol, label: string, r: { v: number | null; src?: string; live: boolean }, unit: string, color: string, to: string, dp = 0): Tile =>
    ({ key, icon, label, value: r.v == null ? null : fmt(r.v, dp), unit, color, source: r.src, live: r.live, to });
  const tiles: Tile[] = [
    { key: 'ecg', icon: 'waveform.path.ecg', label: 'ECG', value: streaming ? 'Live' : lastEcg ? ago(lastEcg) : null, color: data.heart, source: streaming ? 'Patch' : lastEcg ? 'Last recording' : undefined, live: streaming, to: '/monitor' },
    tile('hr', 'heart.fill', 'Heart rate', hr, 'bpm', data.heart, '/monitor'),
    tile('hrv', 'bolt.heart', 'HRV', hrv, 'ms', data.hrv, '/wellness/recovery'),
    tile('spo2', 'drop.fill', 'SpO₂', spo2, '%', data.spo2, '/ring'),
    tile('temp', 'thermometer.medium', 'Skin temp', temp, '°C', data.temp, '/ring', 1),
    tile('vo2', 'figure.run', 'VO₂max', vo2, '', data.activity, '/age'),
    tile('resp', 'lungs.fill', 'Breathing', resp, '/min', data.breath, '/wellness/sleep', 1),
    tile('steps', 'figure.walk', 'Steps', steps, '', data.activity, '/activity'),
    { key: 'sleep', icon: 'moon.zzz', label: 'Sleep', value: 'Auto', color: data.sleep, source: 'Detected', live: d.anyConnected, to: '/wellness/sleep' },
    { key: 'glucose', icon: 'drop.circle', label: 'Glucose', value: null, color: data.glucose, source: 'CGM', live: false, to: '/devices', soon: true },
    { key: 'risk', icon: 'shield.lefthalf.filled', label: 'Risk', value: 'View', color: p.teal, source: '5 models', live: true, to: '/predict' },
    { key: 'devices', icon: 'sensor.tag.radiowaves.forward', label: 'Devices', value: `${d.devices.filter((x) => x.connected).length}/${d.devices.length}`, color: p.graphite, source: 'Connected', live: d.anyConnected, to: '/devices' },
  ];
  const active = tiles.filter((x) => x.live && !x.soon).length;
  return (
    <View style={{ gap: space[3], padding: space[4], borderRadius: radius.xl, backgroundColor: p.surface }}>
      <Row>
        <View style={{ flex: 1 }}>
          <T v="h3">{title}</T>
          <T v="small">{active} signal{active === 1 ? '' : 's'} live{streaming ? ' · ECG streaming' : ''}</T>
        </View>
        {streaming ? <BeatHeart lastBeatAt={b.lastBeatAt} size={16} /> : null}
      </Row>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -4 }}>
        {tiles.map((x) => (
          <View key={x.key} style={{ width: '33.333%', padding: 4 }}>
            <Pressable onPress={() => router.push(x.to as any)} accessibilityRole="button" accessibilityLabel={`${x.label} ${x.value ?? 'not available'}`}
              style={({ pressed }) => ({ padding: space[3], gap: 2, borderRadius: radius.lg, backgroundColor: p.surfaceAlt, opacity: pressed ? 0.7 : 1, minHeight: 86 })}>
              <Row gap={5}>
                <Icon name={x.icon} size={12} color={x.value != null ? x.color : p.faint} />
                <T v="small" style={{ fontSize: type.micro, flex: 1 }} numberOfLines={1}>{x.label}</T>
                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: x.soon ? p.faint : x.live ? p.success : p.warn }} />
              </Row>
              <Row gap={2} style={{ alignItems: 'baseline' }}>
                <T v="num" style={{ fontSize: type.title }} color={x.value != null ? p.text : p.teal} numberOfLines={1}>{x.soon ? 'Soon' : x.value ?? 'Connect'}</T>
                {x.value != null && x.unit ? <T v="small" style={{ fontSize: type.micro }}>{x.unit}</T> : null}
              </Row>
              <T v="small" style={{ fontSize: type.micro }} color={p.faint} numberOfLines={1}>{x.source ?? 'Tap to set up'}</T>
            </Pressable>
          </View>
        ))}
      </View>
    </View>
  );
}
