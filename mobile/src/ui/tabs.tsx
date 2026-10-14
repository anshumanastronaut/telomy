import { SymbolView, SFSymbol } from 'expo-symbols';
import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { GlassView } from 'expo-glass-effect';
import React from 'react';
import { StyleSheet, View } from 'react-native';

import { ROLE_HOME, Role, useRole } from '@/lib/role';
import { fonts, usePalette, useScheme } from '@/lib/theme';

export const tabIcon = (name: SFSymbol) => ({ color, focused }: { color: any; focused: boolean }) => (
  <SymbolView name={focused ? (`${name}.fill` as SFSymbol) : name} size={22} tintColor={color} />
);

/** Tabs for one role; redirects to welcome or the right role home when the stored role differs. */
export function RoleTabs({ role, children }: { role: Role; children: React.ReactNode }) {
  const p = usePalette();
  const scheme = useScheme();
  const { role: current, ready } = useRole();
  if (!ready) return null;
  if (!current) return <Redirect href={'/welcome' as any} />;
  if (current !== role) return <Redirect href={ROLE_HOME[current] as any} />;
  return (
    // Floating Liquid Glass bar (iOS 26) over the content; screens keep 120 pt of bottom padding for it.
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: p.teal, tabBarInactiveTintColor: p.muted,
      tabBarStyle: { position: 'absolute', marginHorizontal: 16, bottom: 22, height: 64, paddingTop: 6, paddingBottom: 6, borderRadius: 32,
        borderTopWidth: 0, backgroundColor: 'transparent', elevation: 0, shadowColor: '#000', shadowOpacity: scheme === 'dark' ? 0.5 : 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
      tabBarItemStyle: { paddingTop: 2 },
      tabBarBackground: () => (
        <View style={[StyleSheet.absoluteFill, { borderRadius: 32, overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth, borderColor: scheme === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' }]}>
          <GlassView style={StyleSheet.absoluteFill} glassEffectStyle="regular" tintColor={scheme === 'dark' ? 'rgba(18,25,22,0.84)' : 'rgba(255,255,255,0.86)'} />{/* glass, but text underneath must not compete with labels */}
        </View>
      ),
      tabBarLabelStyle: { fontSize: 11, fontFamily: fonts.bold, letterSpacing: 0.2 } }}>
      {children}
    </Tabs>
  );
}
