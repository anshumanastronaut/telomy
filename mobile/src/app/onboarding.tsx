// Member onboarding — captures the maximum useful data up front (identity, body, phenotype, routine, medical
// history, medications/supplements, reports, devices, goals) so the engines and the care graph are rich from
// day one. Chunked into short, skippable steps (research-backed) and stored into the profile; meds/supplements
// also POST to their Vault endpoints. Voice-assisted routine is offered where typing is heavy.
import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, Switch, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { HEALTH_AVAILABLE, connectHealth } from '@/lib/health';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, Section, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

const SEX = ['Male', 'Female', 'Intersex'];
const FITZ = [
  { k: 'I', d: 'Very fair — always burns, never tans' },
  { k: 'II', d: 'Fair — burns easily, tans minimally' },
  { k: 'III', d: 'Medium — burns moderately, tans gradually' },
  { k: 'IV', d: 'Olive — burns minimally, tans easily' },
  { k: 'V', d: 'Brown — rarely burns, tans darkly' },
  { k: 'VI', d: 'Deep brown/black — never burns' },
];
const BODY = [
  { k: 'ectomorph', d: 'Lean, slim, hard to gain' },
  { k: 'mesomorph', d: 'Athletic, muscular, gains easily' },
  { k: 'endomorph', d: 'Softer, rounder, stores fat easily' },
];
const ACTIVITY = ['Sedentary', 'Lightly active', 'Moderately active', 'Very active'];
const DIET = ['Vegetarian', 'Non-vegetarian', 'Eggetarian', 'Vegan'];
const SMOKE = ['Never', 'Ex-smoker', 'Current'];
const ALCOHOL = ['None', 'Occasional', 'Regular'];
const CONDITIONS = ['Type 2 diabetes', 'Prediabetes', 'Hypertension', 'High cholesterol', 'Thyroid', 'PCOS', 'Heart disease', 'Kidney disease', 'Fatty liver', 'Asthma', 'Depression/anxiety'];
const GOALS = ['Live longer & healthier', 'Reverse prediabetes', 'Lose weight', 'Protect my heart', 'Sleep better', 'More energy', 'Build strength', 'Fertility'];

const STEPS = 8;

export default function Onboarding() {
  const p = usePalette();
  const [step, setStep] = useState(0);
  // identity
  const [name, setName] = useState(''); const [phone, setPhone] = useState('');
  const [sent, setSent] = useState<string | null>(null); const [code, setCode] = useState(''); const [err, setErr] = useState<string | null>(null);
  // body
  const [dob, setDob] = useState(''); const [sex, setSex] = useState(''); const [city, setCity] = useState('');
  const [height, setHeight] = useState(''); const [weight, setWeight] = useState('');
  const [fitz, setFitz] = useState(''); const [body, setBody] = useState(''); const [activity, setActivity] = useState('');
  // routine
  const [wake, setWake] = useState(''); const [sleep, setSleep] = useState(''); const [work, setWork] = useState('');
  const [diet, setDiet] = useState(''); const [smoke, setSmoke] = useState(''); const [alcohol, setAlcohol] = useState('');
  // medical
  const [conds, setConds] = useState<Record<string, boolean>>({}); const [allergies, setAllergies] = useState(''); const [family, setFamily] = useState('');
  // meds/supp
  const [meds, setMeds] = useState(''); const [supps, setSupps] = useState('');
  // goal + consent
  const [goal, setGoal] = useState<string | null>(null);
  const consents = useApi<any[]>(step === 7 ? '/consents' : null, [step]);
  const [granted, setGranted] = useState<Record<string, boolean>>({});
  const [healthOk, setHealthOk] = useState(false);

  const next = () => { setErr(null); setStep((s) => Math.min(s + 1, STEPS)); };
  const skip = next;

  async function sendOtp() { const r = await api('/auth/otp/send', { body: { phone } }); setSent(r.dev_hint || 'Code sent'); }
  async function verify() { try { await api('/auth/otp/verify', { body: { phone, code } }); next(); } catch (e: any) { setErr(e.message); } }

  async function finish() {
    const prof: any = { onboarded: true, first_name: name, goal };
    if (dob) prof.dob = dob; if (sex) prof.sex = sex.toLowerCase(); if (city) prof.city = city;
    if (height) prof.height_cm = Number(height); if (weight) prof.weight_kg = Number(weight);
    if (fitz) prof.fitzpatrick = fitz; if (body) prof.body_type = body; if (activity) prof.activity_level = activity;
    const routine: any = {}; if (wake) routine.wake = wake; if (sleep) routine.sleep = sleep; if (work) routine.work = work;
    if (Object.keys(routine).length) prof.routine = routine;
    if (diet) prof.diet = diet; if (smoke) prof.smoker = smoke !== 'Never' ? smoke : false; if (alcohol) prof.alcohol = alcohol;
    const conditions = Object.keys(conds).filter((k) => conds[k]);
    if (conditions.length) prof.conditions = conditions;
    if (allergies.trim()) prof.allergies = allergies.trim(); if (family.trim()) prof.family_history = family.trim();
    await api('/profile', { method: 'PUT', body: prof }).catch(() => {});
    for (const m of meds.split(',').map((x) => x.trim()).filter(Boolean)) await api('/meds', { body: { name: m } }).catch(() => {});
    for (const s of supps.split(',').map((x) => x.trim()).filter(Boolean)) await api('/events', { body: { kind: 'supplement', label: `Started ${s}` }, queue: true }).catch(() => {});
    for (const [k, v] of Object.entries(granted)) await api(`/consents/${k}`, { body: { granted: v } }).catch(() => {});
    router.replace('/(tabs)/sinc');
  }

  const chips = (opts: string[], val: string, set: (v: string) => void) => (
    <Row style={{ flexWrap: 'wrap' }} gap={8}>
      {opts.map((o) => (
        <Pressable key={o} onPress={() => set(val === o ? '' : o)} style={{ paddingHorizontal: 14, paddingVertical: 9, borderRadius: 999, borderWidth: 1, borderColor: val === o ? p.teal : p.border, backgroundColor: val === o ? p.tealSoft : p.surface }}>
          <T v="small" color={val === o ? p.teal : p.text}>{o}</T>
        </Pressable>
      ))}
    </Row>
  );

  return (
    <Screen edges={['top', 'bottom']}>
      <Row>{Array.from({ length: STEPS }).map((_, i) => (
        <View key={i} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: i <= step ? p.teal : p.surfaceAlt, marginHorizontal: 1 }} />
      ))}</Row>
      <Pressable onPress={() => router.back()} hitSlop={10} accessibilityLabel="Close" style={{ alignSelf: 'flex-end' }}><Icon name="xmark" color={p.muted} /></Pressable>

      {step === 0 && (
        <>
          <View style={{ alignItems: 'center', paddingVertical: 12 }}><Logo kind="full" width={220} /></View>
          <T v="body" color={p.muted}>Where human biology becomes intelligent. Start with your name and phone — no password.</T>
          <TextInput value={name} onChangeText={setName} placeholder="First name" placeholderTextColor={p.faint} style={inp(p)} />
          <TextInput value={phone} onChangeText={setPhone} placeholder="Phone number" keyboardType="phone-pad" placeholderTextColor={p.faint} style={inp(p)} />
          {sent ? (<>
            <T v="small">{sent}</T>
            <TextInput value={code} onChangeText={setCode} placeholder="6-digit code" keyboardType="number-pad" placeholderTextColor={p.faint} style={inp(p)} testID="otp" />
            {err ? <T v="small" color={p.danger}>{err}</T> : null}
            <Button title="Verify" disabled={code.length !== 6} onPress={verify} />
          </>) : <Button title="Send code" disabled={!name || phone.length < 8} onPress={sendOtp} />}
        </>
      )}

      {step === 1 && (
        <>
          <T v="h1">About you</T>
          <T v="small" color={p.muted}>This sets your reference ranges and your biological-age clocks.</T>
          <TextInput value={dob} onChangeText={setDob} placeholder="Date of birth (YYYY-MM-DD)" placeholderTextColor={p.faint} style={inp(p)} />
          <T v="label">Sex at birth</T>{chips(SEX, sex, setSex)}
          <Row gap={10}>
            <TextInput value={height} onChangeText={setHeight} placeholder="Height (cm)" keyboardType="numeric" placeholderTextColor={p.faint} style={[inp(p), { flex: 1 }]} />
            <TextInput value={weight} onChangeText={setWeight} placeholder="Weight (kg)" keyboardType="numeric" placeholderTextColor={p.faint} style={[inp(p), { flex: 1 }]} />
          </Row>
          <TextInput value={city} onChangeText={setCity} placeholder="City" placeholderTextColor={p.faint} style={inp(p)} />
          <Button title="Continue" onPress={next} />
          <Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 2 && (
        <>
          <T v="h1">Your body</T>
          <T v="label">Skin type (how you react to sun)</T>
          <View style={{ gap: space[1] }}>{FITZ.map((f) => (
            <Pressable key={f.k} onPress={() => setFitz(f.k)} style={{ padding: 12, borderRadius: radius.md, borderWidth: 1, borderColor: fitz === f.k ? p.teal : p.border, backgroundColor: fitz === f.k ? p.tealSoft : p.surface }}>
              <T v="small" color={fitz === f.k ? p.teal : p.text}>Type {f.k} — {f.d}</T>
            </Pressable>
          ))}</View>
          <T v="label">Body type</T>
          <View style={{ gap: space[1] }}>{BODY.map((b) => (
            <Pressable key={b.k} onPress={() => setBody(b.k)} style={{ padding: 12, borderRadius: radius.md, borderWidth: 1, borderColor: body === b.k ? p.teal : p.border, backgroundColor: body === b.k ? p.tealSoft : p.surface }}>
              <T v="small" color={body === b.k ? p.teal : p.text} style={{ textTransform: 'capitalize' }}>{b.k} — {b.d}</T>
            </Pressable>
          ))}</View>
          <T v="label">Activity level</T>{chips(ACTIVITY, activity, setActivity)}
          <Button title="Continue" onPress={next} /><Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 3 && (
        <>
          <T v="h1">Your routine</T>
          <T v="small" color={p.muted}>Type it, or tap the mic to tell Sinc about your day.</T>
          <Row gap={10}>
            <TextInput value={wake} onChangeText={setWake} placeholder="Wake (e.g. 06:30)" placeholderTextColor={p.faint} style={[inp(p), { flex: 1 }]} />
            <TextInput value={sleep} onChangeText={setSleep} placeholder="Sleep (e.g. 23:00)" placeholderTextColor={p.faint} style={[inp(p), { flex: 1 }]} />
          </Row>
          <TextInput value={work} onChangeText={setWork} placeholder="Work pattern (desk / shift / field)" placeholderTextColor={p.faint} style={inp(p)} />
          <Button kind="secondary" title="Describe my day by voice" icon="mic.fill" onPress={() => router.push('/voice')} />
          <T v="label">Diet</T>{chips(DIET, diet, setDiet)}
          <T v="label">Smoking</T>{chips(SMOKE, smoke, setSmoke)}
          <T v="label">Alcohol</T>{chips(ALCOHOL, alcohol, setAlcohol)}
          <Button title="Continue" onPress={next} /><Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 4 && (
        <>
          <T v="h1">Medical history</T>
          <T v="label">Existing conditions</T>
          <Row style={{ flexWrap: 'wrap' }} gap={8}>{CONDITIONS.map((c) => (
            <Pressable key={c} onPress={() => setConds({ ...conds, [c]: !conds[c] })} style={{ paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: conds[c] ? p.teal : p.border, backgroundColor: conds[c] ? p.tealSoft : p.surface }}>
              <T v="small" color={conds[c] ? p.teal : p.text}>{c}</T>
            </Pressable>
          ))}</Row>
          <TextInput value={allergies} onChangeText={setAllergies} placeholder="Allergies (drugs, food…)" placeholderTextColor={p.faint} style={inp(p)} />
          <TextInput value={family} onChangeText={setFamily} placeholder="Family history (e.g. father — heart disease)" placeholderTextColor={p.faint} style={[inp(p), { height: 70 }]} multiline />
          <Button title="Continue" onPress={next} /><Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 5 && (
        <>
          <T v="h1">Medications & supplements</T>
          <T v="small" color={p.muted}>Comma-separated — these go into your Vault and interaction checks.</T>
          <TextInput value={meds} onChangeText={setMeds} placeholder="Medications (e.g. Metformin 500mg, Telmisartan 40mg)" placeholderTextColor={p.faint} style={[inp(p), { height: 70 }]} multiline />
          <TextInput value={supps} onChangeText={setSupps} placeholder="Supplements (e.g. Vitamin D3, Omega-3, Creatine)" placeholderTextColor={p.faint} style={[inp(p), { height: 70 }]} multiline />
          <Button title="Continue" onPress={next} /><Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 6 && (
        <>
          <T v="h1">Reports & devices</T>
          <Section title="Existing reports">
            <Card onPress={() => router.push('/upload')}><Row><Icon name="doc.badge.plus" color={p.teal} /><View style={{ flex: 1 }}><T v="body">Upload labs, imaging, genetics</T><T v="small">PDF or photo — Sinc reads them into your Vault</T></View></Row></Card>
          </Section>
          <Section title="Wearables">
            {[...(HEALTH_AVAILABLE ? [{ t: 'Apple Health', d: 'Steps, workouts, Apple Watch sleep & vitals', icon: 'heart.fill' as const, go: async () => { const r = await connectHealth(); setHealthOk(r.ok); } }] : []),
              { t: 'Telomy patch & ring', d: 'ECG, HRV and sleep', icon: 'waveform.path.ecg' as const, go: () => router.push('/devices') },
              { t: 'WHOOP (via NOOP)', d: 'All-day heart rate and motion', icon: 'figure.run' as const, go: () => router.push('/devices') },
            ].map((w) => (
              <Card key={w.t} onPress={w.go}><Row><Icon name={w.icon} color={p.teal} /><View style={{ flex: 1 }}><T v="body">{w.t}</T><T v="small">{w.d}</T></View><T v="small" color={p.teal}>{w.t === 'Apple Health' && healthOk ? 'Connected' : 'Connect'}</T></Row></Card>
            ))}
          </Section>
          <Button title="Continue" onPress={next} /><Button kind="ghost" title="Skip" onPress={skip} />
        </>
      )}

      {step === 7 && (
        <>
          <T v="h1">Your goal</T>
          <Row style={{ flexWrap: 'wrap' }} gap={8}>{GOALS.map((g) => (
            <Pressable key={g} onPress={() => setGoal(g)} style={{ paddingHorizontal: 14, paddingVertical: 10, borderRadius: 999, borderWidth: 1, borderColor: goal === g ? p.teal : p.border, backgroundColor: goal === g ? p.tealSoft : p.surface }}>
              <T v="small" color={goal === g ? p.teal : p.text}>{g}</T>
            </Pressable>
          ))}</Row>
          <T v="label" style={{ marginTop: space[3] }}>What may Telomy do? (change anytime)</T>
          {(consents.data ?? []).map((c) => (
            <Card key={c.purpose}><Row><T v="body" style={{ flex: 1 }}>{c.title}</T><Switch value={granted[c.purpose] ?? false} onValueChange={(v) => setGranted({ ...granted, [c.purpose]: v })} trackColor={{ true: p.teal }} /></Row><T v="small">{c.what}</T></Card>
          ))}
          <Button title="Finish — meet Sinc" disabled={!goal} onPress={finish} />
        </>
      )}
    </Screen>
  );
}

function inp(p: any) {
  return { borderRadius: radius.md, padding: 14, fontSize: 16, color: p.text, fontFamily: 'HankenGrotesk_400Regular', backgroundColor: p.surface } as const;
}
