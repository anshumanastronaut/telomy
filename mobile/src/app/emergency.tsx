import React, { useEffect, useState } from 'react';
import { TextInput } from 'react-native';

import { api, useApi } from '@/lib/api';
import { radius, usePalette } from '@/lib/theme';
import { Button, Card, Screen, T, useToast } from '@/ui/core';
import { View } from 'react-native';

const FIELDS = [['blood_type', 'Blood type'], ['allergies', 'Allergies'], ['conditions', 'Conditions'], ['medications', 'Medications'], ['contact', 'Emergency contact']];

export default function Emergency() {
  const p = usePalette();
  const { data } = useApi<any>('/profile');
  const [e, setE] = useState<any>({});
  const { toast, show } = useToast();
  useEffect(() => { if (data) setE(data.emergency ?? {}); }, [data]);
  return (
    <View style={{ flex: 1 }}>
      <Screen edges={[]}>
        <T v="body" color={p.muted}>What a first responder needs. Kept short on purpose.</T>
        <Card>
          {FIELDS.map(([k, l]) => (
            <View key={k} style={{ gap: 4 }}>
              <T v="label">{l}</T>
              <TextInput value={e[k] ?? ''} onChangeText={(v) => setE({ ...e, [k]: v })} style={{ borderWidth: 1, borderColor: p.border, borderRadius: radius.md, padding: 10, color: p.text, fontFamily: 'Inter_400Regular' }} />
            </View>
          ))}
        </Card>
        <Button title="Save" onPress={async () => { await api('/profile', { method: 'PUT', body: { emergency: e } }); show('Saved.', 'success'); }} />
      </Screen>
      {toast}
    </View>
  );
}
