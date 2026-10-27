import { SymbolView, SFSymbol } from 'expo-symbols';
import { Ionicons } from '@expo/vector-icons';
import { Redirect } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { GlassView } from 'expo-glass-effect';
import React from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { ROLE_HOME, Role, useRole } from '@/lib/role';
import { fonts, usePalette, useScheme } from '@/lib/theme';

const IOS = Platform.OS === 'ios';

// Not every SF Symbol has a `.fill` variant (e.g. `calendar`, `sparkles`), and SymbolView renders BLANK for a name
// that doesn't exist — which looked like the icon "disappearing" when a tab became active. So the focused icon is the
// base symbol unless an explicit filled `selected` is passed; selection is still signalled by the active tint.
const HAS_FILL = new Set<string>([
  'sun.max', 'person.2', 'tray', 'person.crop.circle', 'chart.bar', 'waveform.path.ecg.rectangle', 'archivebox',
  'bubble.left.and.text.bubble.right', 'figure.stand',
]);

/** Tab icon. iOS renders the SF Symbol (Liquid Glass look); Android/others render the matching Ionicon
 *  (SF Symbols are iOS-only and render blank elsewhere). `ion` is the Ionicons base name; the outline
 *  variant is used when unfocused. `selected` overrides the symbol shown when the tab is active. */
export const tabIcon = (name: SFSymbol, ion: string, selected?: SFSymbol) => {
  const active: SFSymbol = selected ?? (HAS_FILL.has(name) ? (`${name}.fill` as SFSymbol) : name);
  return ({ color, focused }: { color: any; focused: boolean }) =>
    IOS ? (
      <SymbolView name={focused ? active : name} size={22} tintColor={color} />
    ) : (
      <Ionicons name={(focused ? ion : `${ion}-outline`) as any} size={23} color={color} />
    );
};

/** Tabs for one role; redirects to welcome or the right role home when the stored role differs. */
export function RoleTabs({ role, children }: { role: Role; children: React.ReactNode }) {
  const p = usePalette();
  const scheme = useScheme();
  const insets = useSafeAreaInsets();
  const { role: current, ready } = useRole();
  if (!ready) return null;
  if (!current) return <Redirect href={'/welcome' as any} />;
  if (current !== role) return <Redirect href={ROLE_HOME[current] as any} />;
  // Floating bar over the content; screens keep 120 pt of bottom padding for it. On iOS it's Liquid Glass
  // (iOS 26); elsewhere GlassView doesn't render, so we paint a solid opaque surface so content can't show through.
  const bottom = Math.max(18, insets.bottom + (IOS ? 4 : 10));
  return (
    <Tabs screenOptions={{ headerShown: false, tabBarActiveTintColor: p.teal, tabBarInactiveTintColor: p.muted,
      tabBarStyle: { position: 'absolute', marginHorizontal: 16, bottom, height: 64, paddingTop: 6, paddingBottom: 6, borderRadius: 32,
        borderTopWidth: 0, backgroundColor: 'transparent', elevation: IOS ? 0 : 12, shadowColor: '#000', shadowOpacity: scheme === 'dark' ? 0.5 : 0.12, shadowRadius: 18, shadowOffset: { width: 0, height: 8 } },
      tabBarItemStyle: { paddingTop: 2 },
      tabBarBackground: () => (
        <View style={[StyleSheet.absoluteFill, { borderRadius: 32, overflow: 'hidden', borderWidth: StyleSheet.hairlineWidth, borderColor: scheme === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' }]}>
          {IOS ? (
            <GlassView style={StyleSheet.absoluteFill} glassEffectStyle="regular" tintColor={scheme === 'dark' ? 'rgba(18,25,22,0.84)' : 'rgba(255,255,255,0.86)'} />
          ) : (
            <View style={[StyleSheet.absoluteFill, { backgroundColor: p.surface }]} />
          )}
        </View>
      ),
      tabBarLabelStyle: { fontSize: 11, fontFamily: fonts.bold, letterSpacing: 0.2 } }}>
      {children}
    </Tabs>
  );
}
