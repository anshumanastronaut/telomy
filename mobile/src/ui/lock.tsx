// Unlock screen for a password-protected Telomy server. Shown over everything the first time a locked server answers;
// the token is kept on the phone afterwards, so it asks only once (or again if the password is changed).
import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, TextInput, View } from 'react-native';
import { unlock } from '@/lib/api';
import { radius, space, type, usePalette } from '@/lib/theme';
import { Button, T } from '@/ui/core';
import { ThinkingOrb } from '@/sinc/ThinkingOrb';

export function LockScreen() {
  const p = usePalette();
  const [pw, setPw] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const go = async () => { if (!pw || busy) return; setBusy(true); setErr(await unlock(pw)); setBusy(false); };
  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: p.bg, justifyContent: 'center', padding: space[6], gap: space[5] }}>
      <View style={{ alignItems: 'center' }}><ThinkingOrb state="shaping" size={64} /></View>
      <View style={{ gap: space[2], alignItems: 'center' }}>
        <T v="h1" style={{ textAlign: 'center' }}>Welcome back</T>
        <T v="small" style={{ textAlign: 'center' }}>Your Telomy is private. Enter your access password.</T>
      </View>
      <TextInput value={pw} onChangeText={setPw} onSubmitEditing={go} secureTextEntry autoFocus placeholder="Access password" placeholderTextColor={p.faint}
        style={{ backgroundColor: p.surfaceAlt, borderRadius: radius.md, padding: space[4], color: p.text, fontSize: type.lead, fontFamily: 'Inter_400Regular' }} />
      {err ? <T v="small" color={p.danger} style={{ textAlign: 'center' }}>{err}</T> : null}
      <Button title="Unlock" icon="lock.open" loading={busy} onPress={go} />
    </KeyboardAvoidingView>
  );
}
