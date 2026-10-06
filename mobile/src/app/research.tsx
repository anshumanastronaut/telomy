import { router } from 'expo-router';
import React from 'react';

import { useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, T } from '@/ui/core';

export default function Research() {
  const p = usePalette();
  const { data } = useApi<any>('/research');
  if (!data) return <Screen edges={[]}><Loading what="Loading…" /></Screen>;
  return (
    <Screen edges={[]}>
      <Card tone={data.enrolled ? 'teal' : 'copper'}>
        <T v="h3">{data.enrolled ? 'You contribute de-identified data to approved studies.' : 'Research consent is off.'}</T>
        <T v="small">Only de-identified data, only IRB-approved studies, and you can stop at any time.</T>
        {!data.enrolled ? <Button kind="secondary" title="Review in Consent centre" onPress={() => router.push('/consent')} /> : null}
      </Card>
      {data.studies.map((s: any) => (
        <Card key={s.title}>
          <T v="h3">{s.title}</T>
          <Row><Chip label={s.status} fg={p.teal} bg={p.tealSoft} /><T v="small">n = {s.n.toLocaleString()} participants</T></Row>
          <T v="small">Uses: {s.your_data}</T>
          {s.preprint ? <T v="small">{s.preprint}</T> : null}
        </Card>
      ))}
    </Screen>
  );
}
