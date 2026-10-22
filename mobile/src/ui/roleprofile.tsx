import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useRole } from '@/lib/role';
import { staffLogout, staffSync } from '@/lib/staff';
import { usePalette } from '@/lib/theme';

import { Button, Card, Chip, Row, Screen, Section, T } from './core';
import { Logo } from './logo';

/** Profile for doctor / centre staff: who you are (real staff account), your org, and sign out. */
export function RoleProfile({ kind }: { kind: 'doctor' | 'centre' }) {
  const p = usePalette();
  const { setRole } = useRole();
  const me = staffSync();
  const signOut = async () => { await staffLogout(); await setRole(null); router.replace('/welcome' as any); };
  return (
    <Screen>
      <View style={{ alignItems: 'center', paddingVertical: 8 }}><Logo kind="full" width={130} /></View>
      <Card>
        <T v="h2">{me?.name ?? '—'}</T>
        <Row style={{ alignItems: 'center', gap: 8, marginTop: 2 }}>
          <Chip label={me?.label ?? (kind === 'doctor' ? 'Doctor' : 'Centre')} fg={p.teal} bg={p.tealSoft} />
          <T v="small">{me?.org}</T>
        </Row>
      </Card>
      <Section title="Account">
        <Card>
          <Row><T v="body" style={{ flex: 1 }}>Workspace</T><T v="body">{me?.workspace ?? kind}</T></Row>
          <Row><T v="body" style={{ flex: 1 }}>Organisation</T><T v="body">{me?.org ?? '—'}</T></Row>
          <T v="small">You're signed in to the Telomy {kind === 'doctor' ? 'doctor' : 'centre'} console. The full platform — onboarding, billing, staff and reports — is on the web console.</T>
        </Card>
      </Section>
      <Button kind="secondary" title="Sign out" icon="arrow.left.arrow.right" testID="switch-role" onPress={signOut} />
    </Screen>
  );
}
