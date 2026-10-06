import { router } from 'expo-router';
import React, { useEffect, useState } from 'react';
import { Switch, View } from 'react-native';

import { api, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Divider, Row, Screen, T } from '@/ui/core';

export default function Pins() {
  const p = usePalette();
  const sig = useApi<any[]>('/signals');
  const cur = useApi<string[]>('/pins');
  const [sel, setSel] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { if (cur.data) setSel(cur.data); }, [cur.data]);
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Choose up to 6 signals to keep at the top of Home.</T>
      <Card style={{ paddingVertical: 2 }}>
        {(sig.data ?? []).filter((s) => s.value != null).map((s, i) => (
          <View key={s.id}>
            {i ? <Divider /> : null}
            <Row style={{ paddingVertical: 10 }}>
              <T v="body" style={{ flex: 1 }}>{s.label}</T>
              <Switch value={sel.includes(s.id)} trackColor={{ true: p.teal }} accessibilityLabel={`Pin ${s.label}`}
                onValueChange={(v) => setSel(v ? [...sel, s.id].slice(0, 6) : sel.filter((x) => x !== s.id))} />
            </Row>
          </View>
        ))}
      </Card>
      {err ? <T v="small" color={p.danger}>{err}</T> : null}
      <Button title={`Save · ${sel.length} pinned`} disabled={!sel.length} onPress={async () => {
        try { await api('/pins', { method: 'PUT', body: sel }); router.back(); } catch (e: any) { setErr(e.message); }
      }} />
    </Screen>
  );
}
