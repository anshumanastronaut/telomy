import { useLocalSearchParams } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React, { useState } from 'react';
import { Pressable } from 'react-native';

import { API, useApi } from '@/lib/api';
import { usePalette } from '@/lib/theme';
import { Button, Card, Chip, Loading, Row, Screen, T } from '@/ui/core';

export default function Brief() {
  const p = usePalette();
  const params = useLocalSearchParams<{ specialty?: string }>();
  const list = useApi<any[]>('/brief');
  const [sp, setSp] = useState(params.specialty ?? 'cardiology');
  const fhir = useApi<any>(`/brief/${sp}.json`, [sp]);
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>A one-page brief for a specialist: the labs they care about with every previous value and date, your wearable trends, Sinc's patterns marked as reviewed or not, and your supplements. Also exported as FHIR for clinic systems.</T>
      <Row style={{ flexWrap: 'wrap' }}>
        {(list.data ?? []).map((s) => <Pressable key={s.id} onPress={() => setSp(s.id)}><Chip label={s.title} fg={sp === s.id ? '#fff' : p.text} bg={sp === s.id ? p.teal : p.surfaceAlt} /></Pressable>)}
      </Row>
      <Card>
        {!fhir.data ? <Loading what="Assembling…" /> : (
          <>
            <T v="h3">FHIR bundle · {fhir.data.entry.length} resources</T>
            {fhir.data.meta?.tag ? <Chip label="Tagged as test data" fg={p.copper} bg={p.copperSoft} /> : null}
            {fhir.data.entry.slice(1, 9).map((e: any, i: number) => (
              <Row key={i}><T v="small" style={{ flex: 1 }}>{e.resource.code.text}</T><T v="small">{e.resource.valueQuantity ? `${e.resource.valueQuantity.value} ${e.resource.valueQuantity.unit ?? ''}` : e.resource.valueString}</T></Row>
            ))}
          </>
        )}
      </Card>
      <Button icon="doc.richtext" title="Open PDF brief" onPress={() => WebBrowser.openBrowserAsync(`${API}/brief/${sp}.pdf`)} testID="open-brief" />
    </Screen>
  );
}
