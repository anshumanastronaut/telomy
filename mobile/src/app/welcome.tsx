import { router } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { ROLE_HOME, Role, useRole } from '@/lib/role';
import { authStatus, login as memberLogin, signup as memberSignup } from '@/lib/api';
import { staffLogin, staffSignup, staffStatus, staffSync } from '@/lib/staff';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Icon, Screen, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

const ROLES: { k: Role; title: string; body: string; icon: any }[] = [
  { k: 'user', title: "I'm using Telomy for my health", body: 'Your Vault, Sinc, predictions and your doctor in one place.', icon: 'person' },
  { k: 'doctor', title: "I'm a doctor", body: 'Your patient panel ranked by risk, review queue, prescriptions and consults.', icon: 'stethoscope' },
  { k: 'centre', title: 'I run a wellness centre', body: 'Members, scheduling, therapies, machines, staff and revenue.', icon: 'building.2' },
];

export default function Welcome() {
  const p = usePalette();
  const { setRole } = useRole();
  const [sel, setSel] = useState<Role | null>(null);
  const [step, setStep] = useState<'pick' | 'staff' | 'member'>('pick');

  if (step === 'staff' && sel && sel !== 'user') return <StaffLogin kind={sel} onBack={() => setStep('pick')} onDone={async (ws) => { await setRole(ws); router.replace(ROLE_HOME[ws] as any); }} />;
  if (step === 'member') return <MemberLogin onBack={() => setStep('pick')} onDone={async () => { await setRole('user'); router.replace(ROLE_HOME.user as any); }} />;

  return (
    <Screen edges={['top', 'bottom']}>
      <View style={{ alignItems: 'center', paddingTop: space[6], paddingBottom: space[4] }}>
        <Logo kind="full" width={190} />
      </View>
      <T v="h1" style={{ textAlign: 'center' }}>Who's signing in?</T>
      <T v="body" color={p.muted} style={{ textAlign: 'center' }}>Telomy adapts to how you use it. You can switch later in Profile.</T>
      {ROLES.map((r) => {
        const on = sel === r.k;
        return (
          <Pressable key={r.k} testID={`role-${r.k}`} onPress={() => setSel(r.k)} accessibilityRole="radio" accessibilityState={{ selected: on }}
            style={{ flexDirection: 'row', gap: space[3], alignItems: 'center', padding: space[4], borderRadius: radius.lg, borderWidth: on ? 2 : 1, borderColor: on ? p.teal : p.border, backgroundColor: on ? p.tealSoft : p.surface }}>
            <View style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: on ? p.teal : p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
              <Icon name={r.icon} color={on ? p.onAccent : p.teal} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <T v="h3">{r.title}</T>
              <T v="small">{r.body}</T>
            </View>
          </Pressable>
        );
      })}
      <Button title="Continue" disabled={!sel} testID="role-continue"
        onPress={async () => {
          if (sel === 'user') {
            let needsLogin = false;
            try { needsLogin = (await authStatus()).accounts_enabled; } catch { needsLogin = false; }
            if (needsLogin) { setStep('member'); return; }
            await setRole('user'); router.replace(ROLE_HOME.user as any);
          } else setStep('staff');
        }} />
      <T v="small" style={{ textAlign: 'center' }}>Your health data runs on your own devices and records. Doctor and centre sign in with their Telomy staff account.</T>
    </Screen>
  );
}

function StaffLogin({ kind, onBack, onDone }: { kind: 'doctor' | 'centre'; onBack: () => void; onDone: (ws: Role) => void }) {
  const p = usePalette();
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [name, setName] = useState('');
  const [org, setOrg] = useState('');
  const [role, setRoleSel] = useState(kind === 'doctor' ? 'clinic_admin' : 'centre_admin');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [first, setFirst] = useState(false);

  useEffect(() => { staffStatus().then((s) => setFirst(!s.has_staff)).catch(() => {}); }, []);

  const input = { borderWidth: 1, borderColor: p.border, borderRadius: radius.md, backgroundColor: p.surface, padding: 12, color: p.text, fontFamily: 'Inter_400Regular' } as const;

  const go = async () => {
    setErr(null); setBusy(true);
    try {
      if (mode === 'up') {
        const e1 = await staffSignup({ org: org || undefined, role, name: name || email, email, password: pw });
        if (e1) { setErr(e1); return; }
      }
      const e2 = await staffLogin(email, pw);
      if (e2) { setErr(e2); return; }
      const { staffSync } = await import('@/lib/staff');
      const ws = staffSync()?.workspace;
      if (ws === 'doctor' || ws === 'centre') onDone(ws);
      else if (ws === 'platform') onDone('centre');            // super-admin → use the centre console on mobile for now
      else setErr('This account has no mobile workspace.');
    } finally { setBusy(false); }
  };

  return (
    <Screen edges={['top', 'bottom']}>
      <View style={{ alignItems: 'center', paddingTop: space[6], paddingBottom: space[2] }}><Logo kind="full" width={170} /></View>
      <T v="h2" style={{ textAlign: 'center' }}>{kind === 'doctor' ? 'Doctor sign in' : 'Wellness centre sign in'}</T>
      <T v="small" color={p.muted} style={{ textAlign: 'center', marginBottom: space[3] }}>
        {mode === 'up' ? (first ? 'Create the first admin account for your organisation.' : 'Create a staff account.') : 'Sign in with your Telomy staff account.'}
      </T>
      <View style={{ gap: space[3] }}>
        {mode === 'up' && <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={p.faint} style={input} autoCapitalize="words" />}
        {mode === 'up' && kind === 'centre' && <TextInput value={org} onChangeText={setOrg} placeholder="Centre name / id (optional)" placeholderTextColor={p.faint} style={input} autoCapitalize="none" />}
        <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor={p.faint} style={input} autoCapitalize="none" keyboardType="email-address" autoCorrect={false} testID="staff-email" />
        <TextInput value={pw} onChangeText={setPw} placeholder={mode === 'up' ? 'Create a password (8+ characters)' : 'Password'} placeholderTextColor={p.faint} style={input} secureTextEntry onSubmitEditing={go} testID="staff-pw" />
        {err && <T v="small" color={p.danger}>{err}</T>}
        <Button title={busy ? 'Please wait…' : mode === 'up' ? 'Create account' : 'Sign in'} disabled={busy || !email || !pw} onPress={go} testID="staff-go" />
        <Pressable onPress={() => { setMode(mode === 'in' ? 'up' : 'in'); setErr(null); }} style={{ alignItems: 'center', paddingVertical: space[2] }}>
          <T v="small" color={p.teal}>{mode === 'in' ? (first ? 'First time? Create the first admin account' : 'Create a staff account') : 'Have an account? Sign in'}</T>
        </Pressable>
        <Pressable onPress={onBack} style={{ alignItems: 'center' }}><T v="small" color={p.muted}>← Back</T></Pressable>
      </View>
    </Screen>
  );
}

function MemberLogin({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const p = usePalette();
  const [mode, setMode] = useState<'in' | 'up'>('in');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [name, setName] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const input = { borderWidth: 1, borderColor: p.border, borderRadius: radius.md, backgroundColor: p.surface, padding: 12, color: p.text, fontFamily: 'Inter_400Regular' } as const;

  const go = async () => {
    setErr(null); setBusy(true);
    try {
      if (mode === 'up') {
        const tok = await memberSignup(email, pw, name || email);
        if (!tok) { setErr('Could not create your account. That email may already be registered.'); return; }
      } else {
        const tok = await memberLogin(email, pw);
        if (!tok) { setErr('Wrong email or password.'); return; }
      }
      onDone();
    } catch {
      setErr('Something went wrong. Check your connection and try again.');
    } finally { setBusy(false); }
  };

  return (
    <Screen edges={['top', 'bottom']}>
      <View style={{ alignItems: 'center', paddingTop: space[6], paddingBottom: space[2] }}><Logo kind="full" width={170} /></View>
      <T v="h2" style={{ textAlign: 'center' }}>{mode === 'up' ? 'Create your account' : 'Welcome back'}</T>
      <T v="small" color={p.muted} style={{ textAlign: 'center', marginBottom: space[3] }}>
        {mode === 'up' ? 'Your health data stays private to your account.' : 'Sign in to your Telomy account.'}
      </T>
      <View style={{ gap: space[3] }}>
        {mode === 'up' && <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={p.faint} style={input} autoCapitalize="words" testID="member-name" />}
        <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor={p.faint} style={input} autoCapitalize="none" keyboardType="email-address" autoCorrect={false} testID="member-email" />
        <TextInput value={pw} onChangeText={setPw} placeholder={mode === 'up' ? 'Create a password (8+ characters)' : 'Password'} placeholderTextColor={p.faint} style={input} secureTextEntry onSubmitEditing={go} testID="member-pw" />
        {err && <T v="small" color={p.danger}>{err}</T>}
        <Button title={busy ? 'Please wait…' : mode === 'up' ? 'Create account' : 'Sign in'} disabled={busy || !email || !pw} onPress={go} testID="member-go" />
        <Pressable onPress={() => { setMode(mode === 'in' ? 'up' : 'in'); setErr(null); }} style={{ alignItems: 'center', paddingVertical: space[2] }}>
          <T v="small" color={p.teal}>{mode === 'in' ? 'New to Telomy? Create an account' : 'Have an account? Sign in'}</T>
        </Pressable>
        <Pressable onPress={onBack} style={{ alignItems: 'center' }}><T v="small" color={p.muted}>← Back</T></Pressable>
      </View>
    </Screen>
  );
}
