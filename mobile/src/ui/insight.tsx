import { router } from 'expo-router';
import React from 'react';
import { View } from 'react-native';

import { usePalette } from '@/lib/theme';

import { Card, Chip, ConfBar, Icon, Row, Spacer, StatusChip, T } from './core';

export type Insight = {
  id: string;
  kind: string;
  title: string;
  body: string;
  confidence: number;
  review_state: string;
  medical: number;
  evidence: any[];
  receipts: any;
  thread?: any[];
};

const KIND: Record<string, string> = {
  cross_panel: 'Across your reports',
  event_effect: 'From your log',
  signal_correlation: 'From your wearable',
  lab_trend: 'Lab trend',
  lab_wearable: 'Lab × wearable',
  sinc_draft: 'Sinc draft',
};

export function confLabel(c: number) {
  return c >= 0.75 ? 'Strong' : c >= 0.5 ? 'Moderate' : c >= 0.25 ? 'Emerging' : 'Weak';
}

export function InsightCard({ i, compact = false }: { i: Insight; compact?: boolean }) {
  const p = usePalette();
  const dir = i.receipts?.direction;
  return (
    <Card onPress={() => router.push(`/insight/${i.id}`)} testID={`insight-${i.id}`} accessibilityLabel={i.title}>
      <Row>
        <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: p.tealSoft, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name="sparkle" size={12} color={p.teal} />
        </View>
        <T v="label">{KIND[i.kind] ?? i.kind}</T>
        <Spacer />
        {i.medical ? <StatusChip status={i.review_state} /> : dir === 'harmful' ? <Chip label="Watch" fg={p.danger} bg={p.dangerSoft} /> : dir === 'helpful' ? <Chip label="Helping" fg={p.success} bg={p.successSoft} /> : null}
      </Row>
      <T v="h3">{i.title}</T>
      {!compact ? (
        <T v="small" numberOfLines={3}>
          {i.body}
        </T>
      ) : null}
      <Row>
        <ConfBar value={i.confidence} />
        <T v="small">
          {confLabel(i.confidence)} · {Math.round(i.confidence * 100)}%
          {i.receipts?.n ? ` · n = ${i.receipts.n}` : ''}
        </T>
        <Spacer />
        <T v="small" color={p.teal} style={{ fontWeight: '600' }}>
          Receipts
        </T>
      </Row>
    </Card>
  );
}
