import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Ring } from '@/ui/charts';
import { Card, Divider, Icon, Loading, Row, Screen, T } from '@/ui/core';

export default function Completeness() {
  const p = usePalette();
  const { data } = useApi<any>('/completeness');
  if (!data) return <Screen edges={[]}><Loading what="Checking your Vault…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Row><Ring value={data.score} size={72} stroke={7} /><T v="body" style={{ flex: 1 }}>The more complete your Vault, the more Sinc can see — and the higher its confidence.</T></Row>
      <Card style={{ paddingVertical: 4 }}>
        {data.items.map((i: any, k: number) => (
          <View key={i.label}>
            {k ? <Divider /> : null}
            <Row style={{ paddingVertical: 10 }}>
              <Icon name={i.done ? 'checkmark.circle.fill' : 'circle'} color={i.done ? p.success : p.faint} />
              <View style={{ flex: 1 }}><T v="body">{i.label}</T>{!i.done ? <T v="small">{i.action}</T> : null}</View>
            </Row>
          </View>
        ))}
      </Card>
      <T v="small" color={p.teal} onPress={() => router.push('/upload')}>Upload a report</T>
    </Screen>
  );
}
