import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, Switch, TextInput, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

const GOALS = ['Sleep better', 'Recover from training', 'Track a biomarker', 'Prepare for a specific lab', 'Understand my reports'];

export default function Onboarding() {
  const p = usePalette();
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [sent, setSent] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [goal, setGoal] = useState<string | null>(null);
  const consents = useApi<any[]>(step === 2 ? '/consents' : null, [step]);
  const [granted, setGranted] = useState<Record<string, boolean>>({});

  const next = () => { setErr(null); setStep(step + 1); };

  async function sendOtp() {
    const r = await api('/auth/otp/send', { body: { phone } });
    setSent(r.dev_hint);
  }
  async function verify() {
    try {
      await api('/auth/otp/verify', { body: { phone, code } });
      next();
    } catch (e: any) {
      setErr(e.message);
    }
  }
  async function saveConsents() {
    for (const [k, v] of Object.entries(granted)) await api(`/consents/${k}`, { body: { granted: v } });
    next();
  }
  async function finish() {
    await api('/profile', { method: 'PUT', body: { goal, onboarded: true, ...(name ? { first_name: name } : {}) } });
    router.replace('/(tabs)/sinc');
  }

  return (
    <Screen edges={['top', 'bottom']}>
      <Row>
        {[0, 1, 2, 3, 4].map((i) => (
          <View key={i} style={{ flex: 1, height: 3, borderRadius: 2, backgroundColor: i <= step ? p.teal : p.surfaceAlt }} />
        ))}
      </Row>
      <Pressable onPress={() => router.back()} hitSlop={10} accessibilityLabel="Close onboarding" style={{ alignSelf: 'flex-end' }}>
        <Icon name="xmark" color={p.muted} />
      </Pressable>

      {step === 0 && (
        <>
          <View style={{ alignItems: 'center', paddingVertical: 12 }}>
            <Logo kind="full" width={220} />
          </View>
          <T v="body" color={p.muted}>Where human biology becomes intelligent. Let's start with your name and phone — no password.</T>
          <TextInput value={name} onChangeText={setName} placeholder="First name" placeholderTextColor={p.faint} style={inp(p)} />
          <TextInput value={phone} onChangeText={setPhone} placeholder="Phone number" keyboardType="phone-pad" placeholderTextColor={p.faint} style={inp(p)} />
          {sent ? (
            <>
              <T v="small">{sent}</T>
              <TextInput value={code} onChangeText={setCode} placeholder="6-digit code" keyboardType="number-pad" placeholderTextColor={p.faint} style={inp(p)} testID="otp" />
              {err ? <T v="small" color={p.danger}>{err}</T> : null}
              <Button title="Verify" disabled={code.length !== 6} onPress={verify} />
            </>
          ) : (
            <Button title="Send code" disabled={!name || phone.length < 8} onPress={sendOtp} />
          )}
        </>
      )}

      {step === 1 && (
        <>
          <T v="h1">Connect a wearable</T>
          <T v="body" color={p.muted}>Heart rate, HRV, sleep and activity make Sinc's reads much sharper. You can skip and connect later.</T>
          {['Apple Health', 'Google Health Connect', 'Telomy Band', 'Oura / WHOOP / Ultrahuman (via Terra)'].map((w) => (
            <Card key={w}>
              <Row>
                <Icon name="applewatch" color={p.teal} />
                <T v="body" style={{ flex: 1 }}>{w}</T>
                <T v="small" color={p.teal}>Connect</T>
              </Row>
            </Card>
          ))}
          <T v="small">Device connections need the full app build; this test build uses the dummy wearable data.</T>
          <Button title="Continue" onPress={next} />
          <Button kind="ghost" title="Skip for now" onPress={next} />
        </>
      )}

      {step === 2 && (
        <>
          <T v="h1">What may Telomy do?</T>
          <T v="body" color={p.muted}>Everything is off until you turn it on. Each switch says exactly what it enables. You can change any of them later in Profile.</T>
          {(consents.data ?? []).map((c) => (
            <Card key={c.purpose}>
              <Row>
                <T v="h3" style={{ flex: 1 }}>{c.title}</T>
                <Switch value={granted[c.purpose] ?? false} onValueChange={(v) => setGranted({ ...granted, [c.purpose]: v })} trackColor={{ true: p.teal }} accessibilityLabel={c.title} />
              </Row>
              <T v="small">{c.what}</T>
            </Card>
          ))}
          <Button title="Save and continue" onPress={saveConsents} />
        </>
      )}

      {step === 3 && (
        <>
          <T v="h1">Where should we start?</T>
          {GOALS.map((g) => (
            <Pressable key={g} onPress={() => setGoal(g)} style={{ padding: space[4], borderRadius: radius.lg, borderWidth: 1, borderColor: goal === g ? p.teal : p.border, backgroundColor: goal === g ? p.tealSoft : p.surface }}>
              <T v="body" color={goal === g ? p.teal : p.text}>{g}</T>
            </Pressable>
          ))}
          <Button title="Continue" disabled={!goal} onPress={next} />
        </>
      )}

      {step === 4 && (
        <>
          <View style={{ width: 56, height: 56, borderRadius: 28, backgroundColor: p.teal, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="sparkle" color="#fff" size={24} />
          </View>
          <T v="h1">I'm Sinc.</T>
          <T v="body">
            I read everything in your Vault — labs, scans, wearables and what you log — and I'll always show you the evidence behind what I say. When something is medical, I draft it for your clinician rather than deciding for you.
          </T>
          <T v="body">Two questions to start: what made you want to look closer at your health now, and is there a test result you're already wondering about?</T>
          <Button title="Talk to Sinc" onPress={finish} />
        </>
      )}
    </Screen>
  );
}

function inp(p: any) {
  return { borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 14, fontSize: 16, color: p.text, fontFamily: 'Inter_400Regular', backgroundColor: p.surface };
}
