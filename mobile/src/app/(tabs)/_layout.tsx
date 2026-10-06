import { SymbolView, SFSymbol } from 'expo-symbols';
import { Tabs } from 'expo-router/js-tabs';

import { usePalette } from '@/lib/theme';

const icon = (name: SFSymbol) => ({ color, focused }: { color: any; focused: boolean }) => (
  <SymbolView name={focused ? (`${name}.fill` as SFSymbol) : name} size={22} tintColor={color} />
);

export default function TabsLayout() {
  const p = usePalette();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: p.teal,
        tabBarInactiveTintColor: p.muted,
        tabBarStyle: { backgroundColor: p.surface, borderTopColor: p.border },
        tabBarLabelStyle: { fontSize: 11, fontFamily: 'Inter_600SemiBold' },
      }}>
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: icon('house') }} />
      <Tabs.Screen name="vault" options={{ title: 'Vault', tabBarIcon: icon('archivebox') }} />
      <Tabs.Screen name="sinc" options={{ title: 'Sinc', tabBarIcon: icon('bubble.left.and.text.bubble.right') }} />
      <Tabs.Screen name="sessions" options={{ title: 'Sessions', tabBarIcon: icon('circle.hexagongrid') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: icon('person.crop.circle') }} />
    </Tabs>
  );
}
