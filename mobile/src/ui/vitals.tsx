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
import { data, radius, space, type, usePalette } from '@/lib/theme';
import { BeatHeart } from '@/ui/ecg';
import { Icon, Row, T } from '@/ui/core';

type Tile = { key: string; icon: SFSymbol; label: string; value: string | null; unit?: string; color: string; source?: string; live: boolean; to: string; soon?: boolean };
const SHORT: Record<SourceId, string> = { patch: 'Patch', ring: 'Ring', health: 'Health' };
const fmt = (v: number | null | undefined, d = 0) => (v == null ? null : d ? v.toFixed(d) : Math.round(v).toLocaleString('en-IN'));

export function VitalsGrid({ title = 'Telomy is watching' }: { title?: string }) {
  const p = usePalette();
  const d = useDevices();
  const b = useBand();
  const h = useHealth(2);
  const streaming = b.status?.state === 'streaming';
  const src = (k: string) => { const s = d.live[k]?.source; return s ? SHORT[s] : undefined; };
  const t = h.today;
  const tiles: Tile[] = [
    { key: 'ecg', icon: 'waveform.path.ecg', label: 'ECG', value: streaming ? 'Live' : null, color: data.heart, source: 'Patch', live: streaming, to: '/monitor' },
    { key: 'hr', icon: 'heart.fill', label: 'Heart rate', value: fmt(d.live.hr?.value), unit: 'bpm', color: data.heart, source: src('hr'), live: d.live.hr?.value != null, to: '/monitor' },
    { key: 'hrv', icon: 'bolt.heart', label: 'HRV', value: fmt(d.live.hrv?.value), unit: 'ms', color: data.hrv, source: src('hrv'), live: d.live.hrv?.value != null, to: '/wellness/recovery' },
    { key: 'spo2', icon: 'drop.fill', label: 'SpO₂', value: fmt(d.live.spo2?.value), unit: '%', color: data.spo2, source: src('spo2'), live: d.live.spo2?.value != null, to: '/ring' },
    { key: 'temp', icon: 'thermometer.medium', label: 'Skin temp', value: fmt(d.live.skinTemp?.value, 1), unit: '°C', color: data.temp, source: src('skinTemp'), live: d.live.skinTemp?.value != null, to: '/ring' },
    { key: 'vo2', icon: 'figure.run', label: 'VO₂max', value: fmt(d.live.vo2max?.value), unit: '', color: data.activity, source: src('vo2max'), live: d.live.vo2max?.value != null, to: '/age' },
    { key: 'resp', icon: 'lungs.fill', label: 'Breathing', value: fmt(t?.respRate, 1), unit: '/min', color: data.breath, source: t?.respRate != null ? 'Health' : undefined, live: t?.respRate != null, to: '/wellness/sleep' },
    { key: 'steps', icon: 'figure.walk', label: 'Steps', value: fmt(d.live.steps?.value), unit: '', color: data.activity, source: src('steps'), live: d.live.steps?.value != null, to: '/activity' },
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
                <T v="num" style={{ fontSize: type.title }} color={x.value != null ? p.text : p.faint} numberOfLines={1}>{x.soon ? 'Soon' : x.value ?? '—'}</T>
                {x.value != null && x.unit ? <T v="small" style={{ fontSize: type.micro }}>{x.unit}</T> : null}
              </Row>
              <T v="small" style={{ fontSize: type.micro }} color={p.faint} numberOfLines={1}>{x.source ?? 'Not connected'}</T>
            </Pressable>
          </View>
        ))}
      </View>
    </View>
  );
}
