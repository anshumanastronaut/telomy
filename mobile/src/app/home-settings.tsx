// Customise the Home screen — turn each section on/off and reorder. Stored on this device.
import { Stack } from 'expo-router';
import React from 'react';
import { Pressable, View } from 'react-native';
import { useHomeLayout, WIDGETS, type HomeWidget } from '@/lib/homeprefs';
import { radius, space, usePalette } from '@/lib/theme';
import { Button, Card, Icon, Row, Screen, T } from '@/ui/core';

export default function HomeSettings() {
  const p = usePalette();
  const { layout, toggle, move, reset, loaded } = useHomeLayout();
  if (!loaded) return <Screen edges={[]}><Stack.Screen options={{ title: 'Home layout' }} /></Screen>;
  const label = (k: HomeWidget) => WIDGETS.find((w) => w.key === k)!;
  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Home layout' }} />
      <T v="small">Choose what shows on your Home screen and in what order. Everything you track — vitals, clocks, sleep, longevity, effort, recovery — can be here.</T>
      {layout.order.map((k, i) => {
        const w = label(k); const on = layout.enabled[k];
        return (
          <Card key={k} style={{ opacity: on ? 1 : 0.55 }}>
            <Row>
              <View style={{ flex: 1 }}>
                <T v="h3">{w.label}</T>
                <T v="small" color={p.muted}>{w.desc}</T>
              </View>
              {on ? (
                <Row gap={4}>
                  <Pressable onPress={() => move(k, -1)} disabled={i === 0} hitSlop={8} style={{ opacity: i === 0 ? 0.3 : 1, padding: 6 }}><Icon name="chevron.up" size={16} color={p.muted} /></Pressable>
                  <Pressable onPress={() => move(k, 1)} disabled={i === layout.order.length - 1} hitSlop={8} style={{ opacity: i === layout.order.length - 1 ? 0.3 : 1, padding: 6 }}><Icon name="chevron.down" size={16} color={p.muted} /></Pressable>
                </Row>
              ) : null}
              <Pressable onPress={() => toggle(k)} accessibilityRole="switch" accessibilityState={{ checked: on }} hitSlop={8}
                style={{ marginLeft: space[2], width: 46, height: 28, borderRadius: 14, backgroundColor: on ? p.teal : p.surfaceAlt, justifyContent: 'center', padding: 3 }}>
                <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: p.isDark ? p.bg : '#fff', alignSelf: on ? 'flex-end' : 'flex-start' }} />
              </Pressable>
            </Row>
          </Card>
        );
      })}
      <Button kind="secondary" icon="arrow.counterclockwise" title="Reset to default" onPress={reset} />
      <View style={{ height: 30 }} />
    </Screen>
  );
}
