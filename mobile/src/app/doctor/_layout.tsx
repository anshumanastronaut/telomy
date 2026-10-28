import { router } from 'expo-router';
import { Tabs } from 'expo-router/js-tabs';
import { useEffect } from 'react';

import { staffSync } from '@/lib/staff';
import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function DoctorLayout() {
  // Require a signed-in staff session for the doctor console; otherwise send them to sign in.
  useEffect(() => { if (!staffSync()) router.replace('/welcome' as any); }, []);
  return (
    <RoleTabs role="doctor">
      <Tabs.Screen name="index" options={{ title: 'Today', tabBarIcon: tabIcon('sun.max', 'sunny') }} />
      <Tabs.Screen name="patients" options={{ title: 'Patients', tabBarIcon: tabIcon('person.2', 'people') }} />
      <Tabs.Screen name="copilot" options={{ title: 'Sinc', tabBarIcon: tabIcon('sparkles', 'sparkles') }} />
      <Tabs.Screen name="work" options={{ title: 'Work queue', tabBarIcon: tabIcon('tray', 'file-tray') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: tabIcon('person.crop.circle', 'person-circle') }} />
      <Tabs.Screen name="patient/[id]" options={{ href: null }} />
      <Tabs.Screen name="templates" options={{ href: null }} />
      <Tabs.Screen name="consult" options={{ href: null }} />
      <Tabs.Screen name="evidence" options={{ href: null }} />
    </RoleTabs>
  );
}
