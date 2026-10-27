import { Stack } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { useApi } from '@/lib/api';
import { useHere } from '@/lib/location';
import { radius, space, usePalette } from '@/lib/theme';
import { LineChart, Ring } from '@/ui/charts';
import { Button, Card, Chip, Icon, Loading, Row, Screen, Section, T } from '@/ui/core';

const CITIES = ['Delhi', 'Bengaluru', 'Mumbai', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Noida', 'Gurugram'];

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  const p = usePalette();
  return <View style={{ minWidth: 76 }}><T v="small" color={p.muted}>{label}</T><T v="body" style={{ fontWeight: '600' }}>{value}</T>{sub ? <T v="small" color={p.faint}>{sub}</T> : null}</View>;
}

/** Live conditions where the member is right now: real-time AQI/UV/weather → an outdoor-activity score + alerts. */
function HereNow() {
  const p = usePalette();
  const { data, status, error, reload } = useHere(true);
  const bandColor = (b?: string) => b === 'Great' ? p.success : b === 'Good' ? p.teal : b === 'Fair' ? p.warn : p.danger;
  const alertColor = (l: string) => l === 'danger' ? p.danger : l === 'warn' ? p.warn : p.teal;

  if (status === 'idle' || status === 'asking' || status === 'loading')
    return <Card><T v="small" color={p.muted}>Reading air, UV & weather where you are…</T></Card>;
  if (status === 'denied')
    return (
      <Card tone="teal">
        <T v="h3">Conditions where you are</T>
        <T v="small" color={p.muted} style={{ marginTop: 4 }}>Turn on location for live air quality, UV and weather, an outdoor-health score, and sun/UV alerts — used only while the app is open, never stored.</T>
        <Button title="Use my location" onPress={reload} style={{ marginTop: 10 }} />
      </Card>
    );
  if (status === 'error' || !data?.ok)
    return <Card><T v="small" color={p.muted}>{error ?? 'Could not load live conditions.'}</T><Button kind="ghost" title="Retry" onPress={reload} /></Card>;

  const c = data.current ?? {};
  return (
    <Card tone="teal" style={{ gap: space[2] }}>
      <Row><T v="label" style={{ flex: 1 }}>{data.place} · now</T>{c.weather ? <Chip label={c.weather} /> : null}</Row>
      <Row gap={space[3]} style={{ alignItems: 'center' }}>
        <Ring value={data.outdoor_score ?? null} size={84} color={bandColor(data.outdoor_band)} />
        <View style={{ flex: 1 }}>
          <T v="h2" color={bandColor(data.outdoor_band)}>{data.outdoor_band}</T>
          <T v="small" color={p.muted}>for outdoor activity right now</T>
        </View>
      </Row>
      <Row style={{ flexWrap: 'wrap' }} gap={10}>
        <Metric label="Air" value={c.aqi_category ?? '—'} sub={c.pm2_5 != null ? `PM2.5 ${c.pm2_5}` : undefined} />
        <Metric label="UV" value={c.uv_index != null ? `${c.uv_index}` : '—'} sub={data.uv_max_today != null ? `peak ${data.uv_max_today}` : undefined} />
        <Metric label="Temp" value={c.temp_c != null ? `${c.temp_c}°` : '—'} sub={c.feels_like_c != null ? `feels ${c.feels_like_c}°` : undefined} />
        <Metric label="Humidity" value={c.humidity != null ? `${c.humidity}%` : '—'} />
      </Row>
      {(data.alerts ?? []).map((al, i) => (
        <Row key={i} gap={8} style={{ alignItems: 'flex-start' }}>
          <Icon name={al.icon as any} size={14} color={alertColor(al.level)} />
          <T v="small" style={{ flex: 1 }} color={al.level === 'ok' ? p.muted : alertColor(al.level)}>{al.text}</T>
        </Row>
      ))}
      <T v="small" color={p.faint}>{data.source}</T>
    </Card>
  );
}

export default function Environment() {
  const p = usePalette();
  const me = useApi<any>('/environment');
  const expo = useApi<any>('/me/environment');
  const [a, setA] = useState('Delhi');
  const [b, setB] = useState('Bengaluru');
  const cmp = useApi<any>(`/environment/compare?a=${a}&b=${b}`, [a, b]);
  const Picker = ({ value, onChange }: { value: string; onChange: (c: string) => void }) => (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
      {CITIES.map((c) => (
        <Pressable key={c} onPress={() => onChange(c)} accessibilityRole="button"
          style={{ paddingHorizontal: 10, paddingVertical: 6, borderRadius: radius.pill, backgroundColor: value === c ? p.teal : p.surface, borderWidth: 1, borderColor: value === c ? p.teal : p.border }}>
          <T v="small" color={value === c ? p.onAccent : p.text}>{c}</T>
        </Pressable>
      ))}
    </View>
  );
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: '' }} />
      <T v="h1">Your environment</T>
      <HereNow />
      <T v="h3" style={{ marginTop: space[1] }}>What your city does to you</T>
      {expo.data?.factors?.length ? (
        <Section title="Your exposome (all factors)">
          {expo.data.factors.map((f: any) => {
            const line = f.factor === 'air_quality' ? `PM2.5 ${f.pm25} µg/m³ · ≈${f.life_years_lost ?? '—'} yr lost (AQLI)`
              : f.factor === 'social_connection' ? `${f.lonely_pct}% loneliness context · isolation ≈ +26% mortality (Holt-Lunstad)`
              : f.factor === 'noise' ? `~${f.lden_db_estimated} dB · +${f.coronary_disease_risk_increase_pct}% coronary risk`
              : f.factor === 'uv' ? `UV max ~${f.uv_mean_max}` : f.factor === 'food_quality' ? 'From your diet log (NOVA), not your postcode' : (f.note ?? '');
            const label = { air_quality: 'Air quality', social_connection: 'Social connection', noise: 'Noise', uv: 'UV', water: 'Water', food_quality: 'Food quality' }[f.factor as string] ?? f.factor;
            return (
              <Card key={f.factor} style={{ paddingVertical: 10 }}>
                <Row><T v="body" style={{ flex: 1, fontWeight: '600' }}>{label}</T>{f.confidence ? <Chip label={f.confidence} /> : null}</Row>
                <T v="small">{line}</T>
              </Card>
            );
          })}
          <T v="small">{expo.data.honesty}</T>
        </Section>
      ) : null}
      {!me.data ? <Loading what="Downloading your air and UV history…" /> : me.data.available ? (
        <>
          <Card tone="teal">
            <T v="label">{me.data.home} · last {me.data.days} days</T>
            <T v="body">You breathed PM2.5 averaging {me.data.pm25_mean} µg/m³ (WHO guideline 5) — like {me.data.cigarette_equivalent_per_day} cigarettes a day. Lifelong at this level ≈ {me.data.aqli_years_if_lifelong} years of life expectancy (AQLI).</T>
            <T v="small">Midday UV maximum averaged {me.data.uv_mean_max}. Water: {me.data.water}</T>
          </Card>
          <Card>
            <T v="label">Daily PM2.5 where you were (µg/m³)</T>
            <LineChart points={me.data.timeline.filter((t: any) => t.pm25 != null).map((t: any) => ({ x: t.day, y: t.pm25 }))} height={140} unit="µg/m³" band={[0, 15]} />
            <T v="label">UV index (daily max)</T>
            <LineChart points={me.data.timeline.filter((t: any) => t.uv != null).map((t: any) => ({ x: t.day, y: t.uv }))} height={110} />
          </Card>
          {me.data.effects.length ? (
            <Section title="In your own data, per +10 µg/m³ PM2.5">
              <Card style={{ paddingVertical: 4 }}>
                {me.data.effects.map((e: any, i: number) => (
                  <Row key={e.metric} style={{ paddingVertical: 8, borderTopWidth: i ? 1 : 0, borderTopColor: p.border }}>
                    <T v="body" style={{ flex: 1 }}>{e.label} next night</T>
                    <T v="small">{e.per_10ug > 0 ? '+' : ''}{e.per_10ug} {e.unit} [{e.ci95[0]}, {e.ci95[1]}] {e.p}</T>
                  </Row>
                ))}
              </Card>
              <T v="small">{me.data.method}</T>
            </Section>
          ) : null}
        </>
      ) : <Card><T v="body">{me.data.message}</T></Card>}

      <Section title="Same person, two cities">
        <Picker value={a} onChange={setA} />
        <T v="small" style={{ textAlign: 'center' }}>vs</T>
        <Picker value={b} onChange={setB} />
        {cmp.data ? (
          <>
            <Row>
              {cmp.data.cities.map((c: any) => (
                <Card key={c.city} style={{ flex: 1 }}>
                  <T v="h3">{c.city}</T>
                  <T v="small">PM2.5 {c.pm25_annual} µg/m³/yr{c.pm25_last_week ? ` · last week ${c.pm25_last_week}` : ''}</T>
                  <T v="small">≈ {c.cigarettes_per_day_equiv} cigarettes/day</T>
                  <T v="small">UV max ≈ {c.uv_mean_max} · {c.altitude_m} m</T>
                  <Chip label={`−${c.aqli_years_lost} y life (AQLI)`} fg={p.danger} bg={p.dangerSoft} />
                </Card>
              ))}
            </Row>
            <Card>{cmp.data.summary.map((s: string) => <T key={s} v="body">• {s}</T>)}</Card>
            <T v="small" color={p.muted}>Sources: {cmp.data.sources.join('; ')}.</T>
          </>
        ) : <Loading what="Comparing…" />}
      </Section>
      <View style={{ height: space[2] }} />
    </Screen>
  );
}
