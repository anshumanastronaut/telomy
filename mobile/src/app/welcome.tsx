import { router } from 'expo-router';
import React, { useState } from 'react';
import { Pressable, View } from 'react-native';

import { ROLE_HOME, Role, useRole } from '@/lib/role';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Icon, Screen, T } from '@/ui/core';
import { Logo } from '@/ui/logo';

const ROLES: { k: Role; title: string; body: string; icon: any }[] = [
  { k: 'user', title: "I'm using Telomy for my health", body: 'Your Vault, Sinc, predictions and your doctor in one place.', icon: 'person' },
  { k: 'doctor', title: "I'm a doctor", body: 'Your patient panel ranked by risk, review queue, monthly reports and consults.', icon: 'stethoscope' },
  { k: 'centre', title: 'I run a wellness centre', body: 'Members, bookings, services, outcomes and revenue.', icon: 'building.2' },
];

export default function Welcome() {
  const p = usePalette();
  const { setRole } = useRole();
  const [sel, setSel] = useState<Role | null>(null);
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
              <Icon name={r.icon} color={on ? '#fff' : p.teal} />
            </View>
            <View style={{ flex: 1, gap: 2 }}>
              <T v="h3">{r.title}</T>
              <T v="small">{r.body}</T>
            </View>
          </Pressable>
        );
      })}
      <Button title="Continue" disabled={!sel} testID="role-continue" onPress={async () => { await setRole(sel!); router.replace(ROLE_HOME[sel!] as any); }} />
      <T v="small" style={{ textAlign: 'center' }}>Test build: each role opens a demo account with dummy data.</T>
    </Screen>
  );
}
