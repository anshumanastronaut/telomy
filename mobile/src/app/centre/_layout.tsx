import { Tabs } from 'expo-router/js-tabs';

import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function CentreLayout() {
  return (
    <RoleTabs role="centre">
      <Tabs.Screen name="index" options={{ title: 'Dashboard', tabBarIcon: tabIcon('chart.bar') }} />
      <Tabs.Screen name="floor" options={{ title: 'Floor', tabBarIcon: tabIcon('waveform.path.ecg.rectangle') }} />
      <Tabs.Screen name="members" options={{ title: 'Members', tabBarIcon: tabIcon('person.2') }} />
      <Tabs.Screen name="bookings" options={{ title: 'Bookings', tabBarIcon: tabIcon('calendar') }} />
      <Tabs.Screen name="services" options={{ title: 'Services', tabBarIcon: tabIcon('sparkles') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: tabIcon('person.crop.circle') }} />
    </RoleTabs>
  );
}
