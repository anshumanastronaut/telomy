import { Tabs } from 'expo-router/js-tabs';

import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function TabsLayout() {
  return (
    <RoleTabs role="user">
      <Tabs.Screen name="index" options={{ title: 'Today', tabBarIcon: tabIcon('sun.max') }} />
      <Tabs.Screen name="vault" options={{ title: 'Vault', tabBarIcon: tabIcon('archivebox') }} />
      <Tabs.Screen name="therapy" options={{ title: 'Therapy', tabBarIcon: tabIcon('bolt.heart') }} />
      <Tabs.Screen name="sessions" options={{ title: 'Plan', href: null }} />
      <Tabs.Screen name="sinc" options={{ title: 'Sinc', tabBarIcon: tabIcon('bubble.left.and.text.bubble.right') }} />
      <Tabs.Screen name="profile" options={{ title: 'You', tabBarIcon: tabIcon('person.crop.circle') }} />
    </RoleTabs>
  );
}
