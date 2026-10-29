// Morning sleep check-in, opened from the "How did you sleep?" notification. The same prompt also lives inline
// under the sleep dial (wellness/sleep). Answering routes back.
import { router, Stack } from 'expo-router';
import React from 'react';

import { usePalette } from '@/lib/theme';
import { Button, Screen, T } from '@/ui/core';
import { SleepFeeling } from '@/ui/sleepfeeling';

export default function SleepFeelingScreen() {
  const p = usePalette();
  return (
    <Screen edges={['top']}>
      <Stack.Screen options={{ title: 'Your sleep' }} />
      <T v="h1">How did you sleep?</T>
      <T v="small" color={p.muted}>Your morning feeling, next to last night's numbers — where the two disagree is where we learn what restorative sleep looks like for you.</T>
      <SleepFeeling onDone={() => setTimeout(() => router.back(), 700)} />
      <Button kind="ghost" title="See my sleep" icon="moon.stars" onPress={() => router.replace('/wellness/sleep')} />
    </Screen>
  );
}
