import { router } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { useEffect } from 'react';

import { staffSync } from '@/lib/staff';
import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function CentreLayout() {
  useEffect(() => { if (!staffSync()) router.replace('/welcome' as any); }, []);
  return (
    <RoleTabs role="centre">
      <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: tabIcon('chart.bar', 'stats-chart') }} />
      <Tabs.Screen name="floor" options={{ title: 'Floor', tabBarIcon: tabIcon('waveform.path.ecg.rectangle', 'pulse') }} />
      <Tabs.Screen name="members" options={{ title: 'Members', tabBarIcon: tabIcon('person.2', 'people') }} />
      <Tabs.Screen name="bookings" options={{ title: 'Bookings', tabBarIcon: tabIcon('calendar', 'calendar') }} />
      <Tabs.Screen name="services" options={{ title: 'Services', tabBarIcon: tabIcon('sparkles', 'sparkles') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: tabIcon('person.crop.circle', 'person-circle') }} />
    </RoleTabs>
  );
}
