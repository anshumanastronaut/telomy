// Auth gate for a hosted Telomy server. Multi-user: sign up or log in with email + password (the token is kept on the
// phone, so it asks only once). A server still in single-user mode shows the access-password field instead; creating an
// account on it turns on multi-user and the first account inherits the existing Vault.
import React, { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, TextInput, View } from 'react-native';
import { authStatus, login, signup, unlock } from '@/lib/api';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Button, T } from '@/ui/core';
import { ThinkingOrb } from '@/sinc/ThinkingOrb';

type Mode = 'login' | 'signup' | 'password';

export function LockScreen() {
  const p = usePalette();
  const [mode, setMode] = useState<Mode>('login');
  const [accountsEnabled, setAccountsEnabled] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [pw, setPw] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    authStatus().then((s) => {
      setAccountsEnabled(s.accounts_enabled);
      // multi-user server → login; single-user with a password → password; fresh server → let people sign up
      setMode(s.accounts_enabled ? 'login' : s.password_required ? 'password' : 'signup');
    }).catch(() => {});
  }, []);

  const go = async () => {
    if (busy) return;
    setBusy(true); setErr(null);
    let e: string | null = null;
    if (mode === 'password') e = await unlock(pw);
    else if (mode === 'signup') e = email && pw ? await signup(email.trim(), pw, name.trim()) : 'Enter your email and a password.';
    else e = email && pw ? await login(email.trim(), pw) : 'Enter your email and password.';
    setErr(e); setBusy(false);
  };

  const input = { backgroundColor: p.surfaceAlt, borderRadius: radius.md, padding: space[4], color: p.text, fontSize: type.lead, fontFamily: 'Inter_400Regular' } as const;
  const title = mode === 'password' ? 'Welcome back' : mode === 'signup' ? 'Create your Telomy' : 'Welcome back';
  const sub = mode === 'password' ? 'Your Telomy is private. Enter your access password.'
    : mode === 'signup' ? 'Your own private Vault — labs, wearables and Sinc, all yours.'
    : 'Sign in to your Telomy.';

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: p.bg, justifyContent: 'center', padding: space[6], gap: space[4] }}>
      <View style={{ alignItems: 'center' }}><ThinkingOrb state="shaping" size={64} /></View>
      <View style={{ gap: space[2], alignItems: 'center' }}>
        <T v="h1" style={{ textAlign: 'center' }}>{title}</T>
        <T v="small" style={{ textAlign: 'center' }}>{sub}</T>
      </View>

      {mode === 'password' ? (
        <TextInput value={pw} onChangeText={setPw} onSubmitEditing={go} secureTextEntry autoFocus placeholder="Access password"
          placeholderTextColor={p.faint} style={input} />
      ) : (
        <View style={{ gap: space[3] }}>
          {mode === 'signup' ? (
            <TextInput value={name} onChangeText={setName} placeholder="Your name (optional)" placeholderTextColor={p.faint} style={input} autoCapitalize="words" />
          ) : null}
          <TextInput value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor={p.faint} style={input}
            keyboardType="email-address" autoCapitalize="none" autoCorrect={false} autoFocus />
          <TextInput value={pw} onChangeText={setPw} onSubmitEditing={go} secureTextEntry placeholder={mode === 'signup' ? 'Create a password (8+ characters)' : 'Password'}
            placeholderTextColor={p.faint} style={input} />
        </View>
      )}

      {err ? <T v="small" color={p.danger} style={{ textAlign: 'center' }}>{err}</T> : null}
      <Button title={mode === 'password' ? 'Unlock' : mode === 'signup' ? 'Create account' : 'Sign in'} icon={mode === 'password' ? 'lock.open' : 'arrow.right'} loading={busy} onPress={go} />

      {mode !== 'password' ? (
        <Pressable onPress={() => { setErr(null); setMode(mode === 'login' ? 'signup' : 'login'); }} accessibilityRole="button">
          <T v="small" color={p.teal} style={{ textAlign: 'center' }}>
            {mode === 'login' ? "New here? Create an account" : 'Already have an account? Sign in'}
          </T>
        </Pressable>
      ) : null}
      {mode === 'password' && !accountsEnabled ? (
        <Pressable onPress={() => { setErr(null); setMode('signup'); }} accessibilityRole="button">
          <T v="small" color={p.teal} style={{ textAlign: 'center' }}>Set up accounts instead (keeps your current data)</T>
        </Pressable>
      ) : null}
    </KeyboardAvoidingView>
  );
}
