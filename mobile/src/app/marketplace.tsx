import React from 'react';

import { api, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, T, useToast } from '@/ui/core';
import { View } from 'react-native';

export default function Marketplace() {
  const p = usePalette();
  const { data, reload } = useApi<any[]>('/protocols');
  const { toast, show } = useToast();
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <T v="body" color={p.muted}>Protocols written by Telomy clinicians, each with targets, evidence grade and a review cadence. Your clinician confirms before one starts.</T>
        {!data ? <Loading what="Loading protocols…" /> : null}
        {data?.map((pr) => (
          <Card key={pr.id}>
            <Row>
              <T v="h3" style={{ flex: 1 }}>{pr.title}</T>
              <Chip label={`Evidence ${pr.evidence}`} fg={p.teal} bg={p.tealSoft} />
            </Row>
            <T v="small">{pr.author} · {pr.phase} · reviewed {pr.review}</T>
            <Row style={{ flexWrap: 'wrap' }}>{pr.targets.map((t: string) => <Chip key={t} label={t} />)}</Row>
            <T v="small">{Object.values(pr.pillars).flat().length} actions across {Object.keys(pr.pillars).filter((k) => pr.pillars[k].length).join(', ')}</T>
            {pr.active ? (
              <Chip label="Active" fg={p.success} bg={p.successSoft} />
            ) : (
              <Button kind="secondary" title="Request this protocol" onPress={async () => { const r = await api(`/protocols/${pr.id}/activate`, { method: 'POST' }); show(r.message, 'success'); reload(); }} />
            )}
          </Card>
        ))}
      </Screen>
      {toast}
    </View>
  );
}
