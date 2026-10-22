import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, ScrollView, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { EVENT_KINDS, kindOf, localIso } from '@/lib/events';
import { radius, space, usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Button, Card, Chip, Icon, Row, Screen, Spacer, Stat, T } from '@/ui/core';

// Everything a person can log, from the single canonical registry (so caffeine, smoking, water, exercise, naps
// and every therapy are all here — no more divergent lists). 'custom' is dropped from the quick picker.
const KINDS = EVENT_KINDS.filter((x) => x.k !== 'custom');

const SUGGEST: Record<string, string[]> = {
  alcohol: ['1 glass red wine', '2 beers', 'Whisky 60 ml'],
  caffeine: ['Espresso', 'Filter coffee', '2 cups chai'],
  smoking: ['1 cigarette', 'Vape', '2 cigarettes'],
  water: ['250 ml', '500 ml', '1 L'],
  supplement: ['Magnesium glycinate 300 mg', 'Creatine 5 g', 'Omega-3 2 g', 'Vitamin D3 2000 IU', 'Glutathione', 'NAC 600 mg'],
  symptom: ['Headache', 'Bloating', 'Fatigue', 'Joint pain'],
  mood: ['Calm', 'Anxious', 'Energetic', 'Low'],
  meal: ['2 rotis, dal and sabzi with salad', 'Masala oats with 2 eggs', 'Chicken biryani and a coke'],
};

export default function Log() {
  const p = usePalette();
  const params = useLocalSearchParams<{ kind?: string }>();
  const [kind, setKind] = useState<string>(params.kind ?? 'meal');
  const [label, setLabel] = useState('');
  const [sev, setSev] = useState(3);
  const [busy, setBusy] = useState(false);
  const [meal, setMeal] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  async function analyze() {
    setBusy(true);
    setErr(null);
    try {
      setMeal(await api('/meals/analyze', { body: { text: label } }));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      if (kind === 'meal') {
        const r = await api('/meals/analyze', { body: { text: label, save: true }, queue: true });
        setResult({ message: r?.queued ? 'Saved on your phone. It will sync when the Telomy server is reachable.' : 'Saved. Sinc will look at it tonight.' });
      } else {
        const r = await api('/events', { body: { kind, label: label || kindOf(kind).label, severity: ['symptom', 'mood'].includes(kind) ? sev : null, ts: localIso() }, queue: true });
        setResult(r?.queued ? { message: 'Saved on your phone. It will sync when the Telomy server is reachable.' } : r);
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen edges={['top']}>
      <Row>
        <T v="h1">Log</T>
        <Spacer />
        <Pressable onPress={() => router.back()} hitSlop={10} accessibilityLabel="Close">
          <Icon name="xmark" color={p.muted} />
        </Pressable>
      </Row>
      {result ? (
        <Card tone="teal">
          <T v="h3">{result.message}</T>
          {result.suggest ? (
            <>
              <T v="body">{result.suggest.text}</T>
              <Button title="Set up the study" icon="flask" onPress={() => router.replace(`/studies?intervention=${encodeURIComponent(result.suggest.intervention)}`)} />
            </>
          ) : null}
          <Button kind="secondary" title="Log something else" onPress={() => { setResult(null); setLabel(''); setMeal(null); }} />
          <Button kind="ghost" title="Done" onPress={() => router.back()} />
        </Card>
      ) : (
        <>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
            {KINDS.map((x) => (
              <Pressable key={x.k} onPress={() => { setKind(x.k); setMeal(null); setLabel(''); }} accessibilityRole="tab" accessibilityState={{ selected: kind === x.k }} style={{ alignItems: 'center', gap: 4, width: 76, paddingVertical: 10, borderRadius: radius.lg, borderWidth: 1, borderColor: kind === x.k ? p.teal : p.border, backgroundColor: kind === x.k ? p.tealSoft : p.surface }}>
                <Icon name={x.icon as any} color={kind === x.k ? p.teal : p.muted} />
                <T v="small" style={{ fontSize: 11, textAlign: 'center' }} color={kind === x.k ? p.teal : p.muted}>{x.label}</T>
              </Pressable>
            ))}
          </ScrollView>
          <TextInput
            value={label}
            onChangeText={setLabel}
            placeholder={kind === 'meal' ? 'e.g. 2 rotis, dal, salad' : 'Details (optional)'}
            placeholderTextColor={p.faint}
            multiline
            testID="log-input"
            style={{ minHeight: 70, borderRadius: radius.md, padding: 12, color: p.text, fontSize: 16, backgroundColor: p.surface }}
          />
          {SUGGEST[kind] ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {SUGGEST[kind].map((s) => (
                <Pressable key={s} onPress={() => setLabel(s)}>
                  <Chip label={s} />
                </Pressable>
              ))}
            </View>
          ) : null}
          {['symptom', 'mood'].includes(kind) ? (
            <View style={{ gap: 6 }}>
              <T v="label">{kind === 'mood' ? 'How good (1–5)' : 'Severity (1–5)'}</T>
              <Row>
                {[1, 2, 3, 4, 5].map((n) => (
                  <Pressable key={n} onPress={() => setSev(n)} style={{ flex: 1, alignItems: 'center', paddingVertical: 12, borderRadius: radius.md, borderWidth: 1, borderColor: sev === n ? p.teal : p.border, backgroundColor: sev === n ? p.tealSoft : p.surface }}>
                    <T v="h3" color={sev === n ? p.teal : p.text}>{n}</T>
                  </Pressable>
                ))}
              </Row>
            </View>
          ) : null}

          {kind === 'meal' && meal ? <MealCard a={meal} /> : null}
          {err ? <T v="small" color={p.danger}>{err}</T> : null}
          {kind === 'meal' && !meal ? (
            <Button title="Analyse meal" icon="sparkle" disabled={!label.trim()} loading={busy} onPress={analyze} testID="analyze-meal" />
          ) : (
            <Button title="Save" loading={busy} disabled={kind === 'meal' && !meal?.items?.length} onPress={save} testID="save-log" />
          )}
          <T v="small">Saved events appear on your Vault timeline and in Sinc's correlation engine.</T>
        </>
      )}
    </Screen>
  );
}

function MealCard({ a }: { a: any }) {
  const p = usePalette();
  if (!a.items?.length) return <Card tone="copper"><T v="body">{a.message}</T></Card>;
  return (
    <Card>
      <Row>
        <Ring value={a.score} size={60} color={a.score >= 70 ? p.success : a.score >= 45 ? p.warn : p.danger} />
        <View style={{ flex: 1 }}>
          <T v="h3">{Math.round(a.kcal)} kcal · {a.processing}</T>
          <T v="small">Glucose: {a.glucose_response} · {a.circadian}</T>
          <T v="small">{Math.round(a.confidence * 100)}% confidence · {a.items.length} item{a.items.length === 1 ? '' : 's'} recognised</T>
        </View>
      </Row>
      <Row>
        <Stat label="Protein" value={Math.round(a.protein)} unit="g" />
        <Stat label="Carbs" value={Math.round(a.carbs)} unit="g" />
        <Stat label="Fat" value={Math.round(a.fat)} unit="g" />
        <Stat label="Fibre" value={Math.round(a.fibre)} unit="g" />
      </Row>
      <Row>
        <Stat label="Sugar" value={Math.round(a.sugar ?? 0)} unit="g" />
        <Stat label="Added sugar" value={Math.round(a.added_sugar ?? 0)} unit="g" sub={a.pct_daily ? `${a.pct_daily.added_sugar}% of daily limit` : undefined} />
        <Stat label="Sat. fat" value={Math.round(a.sat_fat ?? 0)} unit="g" sub={a.pct_daily ? `${a.pct_daily.sat_fat}% of daily` : undefined} />
      </Row>
      {a.tips.map((t: string) => (
        <Row key={t} style={{ alignItems: 'flex-start' }}>
          <Icon name="lightbulb" size={13} color={p.copper} />
          <T v="small" style={{ flex: 1 }}>{t}</T>
        </Row>
      ))}
      {a.unmatched?.length ? <T v="small">Didn't recognise: {a.unmatched.join(', ')}</T> : null}
      <T v="small">{a.method}</T>
    </Card>
  );
}
