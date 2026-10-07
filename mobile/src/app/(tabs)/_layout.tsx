import { Tabs } from 'expo-router/js-tabs';

import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function TabsLayout() {
  return (
    <RoleTabs role="user">
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: tabIcon('house') }} />
      <Tabs.Screen name="vault" options={{ title: 'Vault', tabBarIcon: tabIcon('archivebox') }} />
      <Tabs.Screen name="therapy" options={{ title: 'Therapy', tabBarIcon: tabIcon('bolt.heart') }} />
      <Tabs.Screen name="sessions" options={{ title: 'Plan', tabBarIcon: tabIcon('list.bullet.clipboard') }} />
      <Tabs.Screen name="sinc" options={{ title: 'Sinc', tabBarIcon: tabIcon('bubble.left.and.text.bubble.right') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: tabIcon('person.crop.circle') }} />
    </RoleTabs>
  );
}
