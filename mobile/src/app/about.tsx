// About you — the few facts every clinical formula needs (age, sex, height, weight, smoking). Until they are filled
// in, Telomy shows "needs …" instead of assuming (it used to assume male / typical values).
import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { TextInput, View } from 'react-native';
import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Screen, Segmented, T, useToast } from '@/ui/core';

/** Profile fields the engines need; used by the Today prompt too. */
export const missingAbout = (p: any) => ['dob', 'sex', 'height_cm'].filter((k) => !p?.[k]);

export default function About() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/profile');
  const { toast, show } = useToast();
  const [f, setF] = useState({ first_name: '', dob: '', sex: '' as '' | 'female' | 'male', height_cm: '', weight_kg: '', smoker: 'no' as 'no' | 'yes' });
  useEffect(() => {
    if (data) setF({ first_name: data.first_name ?? '', dob: data.dob ?? '', sex: data.sex ?? '', height_cm: data.height_cm ? String(data.height_cm) : '',
      weight_kg: data.weight_kg ? String(data.weight_kg) : '', smoker: data.smoker ? 'yes' : 'no' });
  }, [data]);
  const input = { borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'Inter_400Regular' } as const;
  const dobOk = !f.dob || /^\d{4}-\d{2}-\d{2}$/.test(f.dob);
  async function save() {
    if (!dobOk) { show('Date of birth as YYYY-MM-DD, e.g. 1995-04-21', 'alert'); return; }
    const h = Number(f.height_cm), w = Number(f.weight_kg);
    await api('/profile', { method: 'PUT', body: {
      first_name: f.first_name.trim(), ...(f.dob ? { dob: f.dob } : {}), ...(f.sex ? { sex: f.sex } : {}),
      ...(h >= 100 && h <= 230 ? { height_cm: h } : {}), ...(w >= 30 && w <= 250 ? { weight_kg: w } : {}), smoker: f.smoker === 'yes' } });
    show('Saved', 'success'); reload(); setTimeout(() => router.back(), 600);
  }
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'About you' }} />
        <T v="small">Heart-risk, kidney, body-composition and fitness formulas need these. Telomy never guesses them; until they are here, those results say what is missing.</T>
        <Card style={{ gap: space[2] }}>
          <T v="label">First name</T>
          <TextInput value={f.first_name} onChangeText={(v) => setF({ ...f, first_name: v })} placeholder="First name" placeholderTextColor={p.faint} style={input} />
          <T v="label">Date of birth</T>
          <TextInput value={f.dob} onChangeText={(v) => setF({ ...f, dob: v })} placeholder="YYYY-MM-DD" placeholderTextColor={p.faint} keyboardType="numbers-and-punctuation" style={input} />
          <T v="label">Sex used in medical formulas</T>
          <Segmented options={[{ key: 'female', label: 'Female' }, { key: 'male', label: 'Male' }]} value={f.sex || ('' as any)} onChange={(k) => setF({ ...f, sex: k })} />
          <T v="small">Risk equations are calibrated by sex at birth; tell us here and we use it only for those formulas.</T>
          <T v="label">Height (cm)</T>
          <TextInput value={f.height_cm} onChangeText={(v) => setF({ ...f, height_cm: v })} placeholder="e.g. 175" placeholderTextColor={p.faint} keyboardType="number-pad" style={input} />
          <T v="label">Weight (kg)</T>
          <TextInput value={f.weight_kg} onChangeText={(v) => setF({ ...f, weight_kg: v })} placeholder="e.g. 72" placeholderTextColor={p.faint} keyboardType="decimal-pad" style={input} />
          <T v="label">Do you smoke?</T>
          <Segmented options={[{ key: 'no', label: 'No' }, { key: 'yes', label: 'Yes' }]} value={f.smoker} onChange={(k) => setF({ ...f, smoker: k })} />
        </Card>
        <Button title="Save" onPress={save} />
      </Screen>
      {toast}
    </View>
  );
}
