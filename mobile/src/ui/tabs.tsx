import { SymbolView, SFSymbol } from 'expo-symbols';
import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import React from 'react';

import { ROLE_HOME, Role, useRole } from '@/lib/role';
import { fonts, usePalette } from '@/lib/theme';

export const tabIcon = (name: SFSymbol) => ({ color, focused }: { color: any; focused: boolean }) => (
  <SymbolView name={focused ? (`${name}.fill` as SFSymbol) : name} size={22} tintColor={color} />
);

/** Tabs for one role; redirects to welcome or the right role home when the stored role differs. */
export function RoleTabs({ role, children }: { role: Role; children: React.ReactNode }) {
  const p = usePalette();
  const { role: current, ready } = useRole();
  if (!ready) return null;
  if (!current) return <Redirect href={'/welcome' as any} />;
  if (current !== role) return <Redirect href={ROLE_HOME[current] as any} />;
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: p.teal, tabBarInactiveTintColor: p.muted,
      tabBarStyle: { backgroundColor: p.surface, borderTopColor: p.border }, tabBarLabelStyle: { fontSize: 11, fontFamily: fonts.bold } }}>
      {children}
    </Tabs>
  );
}
