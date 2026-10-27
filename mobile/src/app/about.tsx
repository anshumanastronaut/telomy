// About you — the few facts every clinical formula needs (age, sex, height, weight, smoking), plus a profile photo
// and Fitzpatrick skin type. Skin type isn't cosmetic: it calibrates optical SpO₂/PPG and personalises the UV score.
// Until the core facts are filled in, Telomy shows "needs …" instead of assuming.
import * as ImagePicker from 'expo-image-picker';
import { router, Stack } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, TextInput, View } from 'react-native';
import { api, useApi } from '@/lib/api';
import { FITZPATRICK } from '@/lib/skin';
import { radius, space, usePalette } from '@/lib/theme';
import { Avatar, Button, Card, Icon, Row, Screen, Segmented, T, useToast } from '@/ui/core';

/** Profile fields the engines need; used by the Today prompt too. */
export const missingAbout = (p: any) => ['dob', 'sex', 'height_cm'].filter((k) => !p?.[k]);

export default function About() {
  const p = usePalette();
  const { data, reload } = useApi<any>('/profile');
  const photo = useApi<any>('/profile/photo');
  const { toast, show } = useToast();
  const [busyPhoto, setBusyPhoto] = useState(false);
  const [f, setF] = useState({ first_name: '', dob: '', sex: '' as '' | 'female' | 'male', height_cm: '', weight_kg: '', smoker: 'no' as 'no' | 'yes', skin_type: 0 as number });
  useEffect(() => {
    if (data) setF({ first_name: data.first_name ?? '', dob: data.dob ?? '', sex: data.sex ?? '', height_cm: data.height_cm ? String(data.height_cm) : '',
      weight_kg: data.weight_kg ? String(data.weight_kg) : '', smoker: data.smoker ? 'yes' : 'no',
      skin_type: data.skin_type ?? ({ I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6 } as Record<string, number>)[data.fitzpatrick] ?? 0 });
  }, [data]);
  const input = { borderRadius: radius.md, padding: 12, color: p.text, backgroundColor: p.surface, fontFamily: 'HankenGrotesk_400Regular' } as const;
  const dobOk = !f.dob || /^\d{4}-\d{2}-\d{2}$/.test(f.dob);

  async function pickPhoto() {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { show('Allow photo access in Settings to add a picture.', 'alert'); return; }
    const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsEditing: true, aspect: [1, 1], quality: 0.6, base64: true });
    if (res.canceled || !res.assets?.[0]?.base64) return;
    setBusyPhoto(true);
    try {
      await api('/profile/photo', { method: 'PUT', body: { photo: `data:image/jpeg;base64,${res.assets[0].base64}` } });
      await photo.reload(); show('Photo updated', 'success');
    } catch (e: any) { show(e.message, 'alert'); } finally { setBusyPhoto(false); }
  }
  async function removePhoto() {
    setBusyPhoto(true);
    try { await api('/profile/photo', { method: 'DELETE' }); await photo.reload(); } catch { /* ignore */ } finally { setBusyPhoto(false); }
  }

  async function save() {
    if (!dobOk) { show('Date of birth as YYYY-MM-DD, e.g. 1995-04-21', 'alert'); return; }
    const h = Number(f.height_cm), w = Number(f.weight_kg);
    await api('/profile', { method: 'PUT', body: {
      first_name: f.first_name.trim(), ...(f.dob ? { dob: f.dob } : {}), ...(f.sex ? { sex: f.sex } : {}),
      ...(h >= 100 && h <= 230 ? { height_cm: h } : {}), ...(w >= 30 && w <= 250 ? { weight_kg: w } : {}),
      smoker: f.smoker === 'yes', ...(f.skin_type ? { skin_type: f.skin_type } : {}) } });
    show('Saved', 'success'); reload(); setTimeout(() => router.back(), 600);
  }
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <Stack.Screen options={{ title: 'About you' }} />

        {/* Photo */}
        <Card style={{ alignItems: 'center', gap: space[2] }}>
          <Pressable onPress={pickPhoto} accessibilityRole="button" accessibilityLabel="Change profile photo" style={{ alignItems: 'center' }}>
            <View>
              <Avatar uri={photo.data?.photo} name={f.first_name || data?.name} size={96} />
              <View style={{ position: 'absolute', right: -2, bottom: -2, width: 30, height: 30, borderRadius: 15, backgroundColor: p.teal, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: p.bg }}>
                {busyPhoto ? <ActivityIndicator size="small" color={p.onAccent} /> : <Icon name="camera.fill" size={13} color={p.onAccent} />}
              </View>
            </View>
          </Pressable>
          <T v="small" color={p.muted}>{photo.data?.photo ? 'Tap to change your photo' : 'Add a profile photo — your doctor sees it too'}</T>
          {photo.data?.photo ? <Pressable onPress={removePhoto} hitSlop={8}><T v="small" color={p.danger}>Remove photo</T></Pressable> : null}
        </Card>

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

        {/* Skin type */}
        <Card style={{ gap: space[2] }}>
          <T v="label">Skin tone (Fitzpatrick type)</T>
          <T v="small">Calibrates your oxygen (SpO₂) and pulse reads, and personalises your UV and vitamin-D guidance. Pick the closest.</T>
          <Row style={{ justifyContent: 'space-between', marginTop: 4 }}>
            {FITZPATRICK.map((s) => {
              const on = f.skin_type === s.type;
              return (
                <Pressable key={s.type} onPress={() => setF({ ...f, skin_type: on ? 0 : s.type })} accessibilityRole="button" accessibilityState={{ selected: on }}
                  style={{ alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: s.swatch, borderWidth: on ? 3 : 1, borderColor: on ? p.teal : p.border }} />
                  <T v="small" style={{ fontSize: 11 }} color={on ? p.teal : p.muted}>{s.roman}</T>
                </Pressable>
              );
            })}
          </Row>
          {f.skin_type ? <T v="small" color={p.muted}>{FITZPATRICK.find((x) => x.type === f.skin_type)?.desc}</T> : null}
        </Card>

        <Button title="Save" onPress={save} />
      </Screen>
      {toast}
    </View>
  );
}
