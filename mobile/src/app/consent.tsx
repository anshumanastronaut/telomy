import React from 'react';
import { Switch, View } from 'react-native';

import { api, fmtDate, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Card, Divider, Loading, Row, Screen, Section, T, useToast } from '@/ui/core';

export default function Consent() {
  const p = usePalette();
  const { data, setData } = useApi<any[]>('/consents');
  const hist = useApi<any[]>('/consents/history');
  const { toast, show } = useToast();
  async function set(purpose: string, granted: boolean) {
    const r = await api(`/consents/${purpose}`, { body: { granted } });
    setData((d) => d!.map((x) => (x.purpose === purpose ? { ...x, granted } : x)));
    hist.reload();
    show(r.message, granted ? 'success' : 'neutral');
  }
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <T v="body" color={p.muted}>Each purpose is off until you turn it on. Revoking takes effect immediately; copies held for that purpose are deleted within 24 hours.</T>
        {!data ? <Loading what="Loading consents…" /> : null}
        {data?.map((c) => (
          <Card key={c.purpose}>
            <Row>
              <T v="h3" style={{ flex: 1 }}>{c.title}</T>
              <Switch value={c.granted} onValueChange={(v) => set(c.purpose, v)} trackColor={{ true: p.teal }} accessibilityLabel={`${c.title} consent`} />
            </Row>
            <T v="small">What: {c.what}</T>
            <T v="small">Who sees it: {c.who}</T>
            <T v="small">How long: {c.retention}</T>
          </Card>
        ))}
        <Section title="History">
          <Card style={{ paddingVertical: 4 }}>
            {(hist.data ?? []).slice(0, 20).map((h, i) => (
              <View key={h.id}>
                {i ? <Divider /> : null}
                <Row style={{ paddingVertical: 8 }}>
                  <T v="body" style={{ flex: 1 }}>{h.title}</T>
                  <T v="small" color={h.granted ? p.success : p.danger}>{h.granted ? 'Granted' : 'Revoked'}</T>
                  <T v="small">{fmtDate(h.ts)} {h.ts.slice(11, 16)}</T>
                </Row>
              </View>
            ))}
          </Card>
        </Section>
      </Screen>
      {toast}
    </View>
  );
}
