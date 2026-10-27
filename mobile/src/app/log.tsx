import { router, useLocalSearchParams } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, ScrollView, TextInput, View } from 'react-native';

import { api } from '@/lib/api';
import { EVENT_KINDS, kindOf, localIso } from '@/lib/events';
import { radius, space, usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Button, Card, Chip, Icon, Row, Screen, Spacer, Stat, T } from '@/ui/core';

// Everything a person can log, from the single canonical registry (so caffeine, smoking, water, exercise, naps
// and every therapy are all here — no more divergent lists), Custom included for anything that doesn't fit.
const KINDS = EVENT_KINDS;

// When something happened — anything in the last 24 h. Offsets are minutes before now.
const WHEN: { label: string; min: number }[] = [
  { label: 'Now', min: 0 }, { label: '15 min', min: 15 }, { label: '30 min', min: 30 },
  { label: '1 h', min: 60 }, { label: '2 h', min: 120 }, { label: '3 h', min: 180 },
  { label: '6 h', min: 360 }, { label: '12 h', min: 720 }, { label: '24 h', min: 1440 },
];
const clockAt = (min: number) =>
  new Date(Date.now() - min * 60_000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

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
  // Multi-select: a person can tick several things that happened and log them in one go.
  const [selected, setSelected] = useState<Set<string>>(new Set([params.kind ?? 'meal']));
  const [note, setNote] = useState('');
  const [sev, setSev] = useState(3);
  const [whenMin, setWhenMin] = useState(0);
  const [busy, setBusy] = useState(false);
  const [meal, setMeal] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const kinds = [...selected];
  const onlyMeal = kinds.length === 1 && kinds[0] === 'meal';
  const hasRating = kinds.some((k) => k === 'symptom' || k === 'mood');

  function toggle(k: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(k)) next.delete(k); else next.add(k);
      return next;
    });
    setMeal(null);
  }

  async function analyze() {
    setBusy(true);
    setErr(null);
    try {
      setMeal(await api('/meals/analyze', { body: { text: note } }));
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
      const ts = localIso(Date.now() / 1000 - whenMin * 60);
      if (onlyMeal) {
        const r = await api('/meals/analyze', { body: { text: note, save: true, ts }, queue: true });
        setResult({ message: r?.queued ? 'Saved on your phone. It will sync when the Telomy server is reachable.' : 'Saved. Sinc will look at it tonight.' });
      } else {
        let last: any = null;
        for (const k of kinds) {
          last = await api('/events', { body: { kind: k, label: note || kindOf(k).label, severity: (k === 'symptom' || k === 'mood') ? sev : null, ts }, queue: true });
        }
        if (kinds.length > 1) setResult({ message: `Logged ${kinds.length} things${whenMin ? ` at ${clockAt(whenMin)}` : ''}.` });
        else setResult(last?.queued ? { message: 'Saved on your phone. It will sync when the Telomy server is reachable.' } : last);
      }
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setResult(null); setNote(''); setMeal(null); setWhenMin(0);
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
          <Button kind="secondary" title="Log something else" onPress={reset} />
          <Button kind="ghost" title="Done" onPress={() => router.back()} />
        </Card>
      ) : (
        <>
          <T v="small" color={p.muted}>Tap everything that applies — log one thing or several at once.</T>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
            {KINDS.map((x) => {
              const on = selected.has(x.k);
              return (
                <Pressable key={x.k} onPress={() => toggle(x.k)} accessibilityRole="checkbox" accessibilityState={{ checked: on }}
                  style={{ alignItems: 'center', justifyContent: 'center', gap: 6, width: 76, height: 78, paddingHorizontal: 4, borderRadius: radius.lg, borderWidth: 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.tealSoft : p.surface }}>
                  <Icon name={x.icon as any} color={on ? p.teal : p.muted} />
                  <T v="small" numberOfLines={2} style={{ fontSize: 11, lineHeight: 13, textAlign: 'center' }} color={on ? p.teal : p.muted}>{x.label}</T>
                </Pressable>
              );
            })}
          </View>

          {/* When — anything in the last 24 hours */}
          <View style={{ gap: 6 }}>
            <Row>
              <T v="label" style={{ flex: 1 }}>When</T>
              <T v="small" color={p.muted}>{whenMin === 0 ? 'Now' : `${clockAt(whenMin)} · ${WHEN.find((w) => w.min === whenMin)?.label} ago`}</T>
            </Row>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
              {WHEN.map((w) => (
                <Pressable key={w.min} onPress={() => setWhenMin(w.min)} accessibilityRole="button" accessibilityState={{ selected: whenMin === w.min }}
                  style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.pill, borderWidth: 1, borderColor: whenMin === w.min ? p.teal : p.border, backgroundColor: whenMin === w.min ? p.tealSoft : p.surface }}>
                  <T v="small" color={whenMin === w.min ? p.teal : p.muted}>{w.min === 0 ? 'Now' : `${w.label} ago`}</T>
                </Pressable>
              ))}
            </ScrollView>
          </View>

          <TextInput
            value={note}
            onChangeText={setNote}
            placeholder={onlyMeal ? 'e.g. 2 rotis, dal, salad' : kinds.length > 1 ? 'Optional note — applies to all selected' : 'Details (optional)'}
            placeholderTextColor={p.faint}
            multiline
            testID="log-input"
            style={{ minHeight: 70, borderRadius: radius.md, padding: 12, color: p.text, fontSize: 16, backgroundColor: p.surface }}
          />
          {kinds.length === 1 && SUGGEST[kinds[0]] ? (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
              {SUGGEST[kinds[0]].map((s) => (
                <Pressable key={s} onPress={() => setNote(s)}>
                  <Chip label={s} />
                </Pressable>
              ))}
            </View>
          ) : null}
          {hasRating ? (
            <View style={{ gap: 6 }}>
              <T v="label">{kinds.includes('mood') && !kinds.includes('symptom') ? 'How good (1–5)' : 'Severity (1–5)'}</T>
              <Row>
                {[1, 2, 3, 4, 5].map((n) => (
                  <Pressable key={n} onPress={() => setSev(n)} style={{ flex: 1, alignItems: 'center', paddingVertical: 12, borderRadius: radius.md, borderWidth: 1, borderColor: sev === n ? p.teal : p.border, backgroundColor: sev === n ? p.tealSoft : p.surface }}>
                    <T v="h3" color={sev === n ? p.teal : p.text}>{n}</T>
                  </Pressable>
                ))}
              </Row>
            </View>
          ) : null}

          {onlyMeal && meal ? <MealCard a={meal} /> : null}
          {err ? <T v="small" color={p.danger}>{err}</T> : null}
          {onlyMeal && !meal ? (
            <Button title="Analyse meal" icon="sparkle" disabled={!note.trim()} loading={busy} onPress={analyze} testID="analyze-meal" />
          ) : (
            <Button title={kinds.length > 1 ? `Save ${kinds.length} entries` : 'Save'} loading={busy} disabled={kinds.length === 0} onPress={save} testID="save-log" />
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
