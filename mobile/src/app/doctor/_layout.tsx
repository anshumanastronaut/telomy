import { Tabs } from 'expo-router/js-tabs';

import { RoleTabs, tabIcon } from '@/ui/tabs';

export default function DoctorLayout() {
  return (
    <RoleTabs role="doctor">
      <Tabs.Screen name="index" options={{ title: 'Today', tabBarIcon: tabIcon('sun.max') }} />
      <Tabs.Screen name="patients" options={{ title: 'Patients', tabBarIcon: tabIcon('person.2') }} />
      <Tabs.Screen name="work" options={{ title: 'Work queue', tabBarIcon: tabIcon('tray') }} />
      <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: tabIcon('person.crop.circle') }} />
    </RoleTabs>
  );
}
