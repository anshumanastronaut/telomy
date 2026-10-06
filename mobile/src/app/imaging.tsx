import React, { useState } from 'react';
import { View } from 'react-native';
import Svg, { Circle, Ellipse, Line, Rect } from 'react-native-svg';

import { fmtDate, useApi } from '@/lib/api';
import { statusColor, usePalette } from '@/lib/theme';
import { Card, Chip, Loading, Row, Screen, StatusChip, T } from '@/ui/core';
import Slider from '@/ui/slider';

export default function Imaging() {
  const p = usePalette();
  const { data } = useApi<any[]>('/imaging');
  const [slice, setSlice] = useState<Record<number, number>>({});
  if (!data) return <Screen edges={[]}><Loading what="Loading studies…" /></Screen>;
  return (
    <Screen edges={[]}>
      <T v="body" color={p.muted}>Imaging studies with the radiologist's structured findings. Scrub through slices; findings link to your biomarkers.</T>
      {data.map((s) => {
        const k = slice[s.id] ?? Math.floor(s.images / 2);
        return (
          <Card key={s.id}>
            <Row><T v="h3" style={{ flex: 1 }}>{s.title}</T><Chip label={s.modality} /></Row>
            <T v="small">{fmtDate(s.day, true)} · {s.series} series · {s.images} images{s.is_test_data ? ' · test data' : ''}</T>
            <View style={{ backgroundColor: '#000', borderRadius: 10, alignItems: 'center', paddingVertical: 10 }}>
              <Svg width={260} height={180}>
                <Rect x={0} y={0} width={260} height={180} fill="#050505" />
                <Ellipse cx={130} cy={90} rx={90 - Math.abs(k - s.images / 2)} ry={70} fill="#2a2a2a" />
                <Ellipse cx={130} cy={90} rx={40} ry={30 + (k % 5)} fill="#575757" />
                <Circle cx={100 + (k % 7) * 4} cy={80} r={8} fill="#8a8a8a" />
                <Line x1={10} y1={170} x2={60} y2={170} stroke="#ddd" strokeWidth={1} />
              </Svg>
              <T v="small" color="#bbb">Slice {k + 1} / {s.images} · schematic preview (DICOM viewer next iteration)</T>
            </View>
            <Slider value={k} max={s.images - 1} onChange={(v) => setSlice({ ...slice, [s.id]: v })} />
            {s.findings.map((f: any) => (
              <Row key={f.text} style={{ alignItems: 'flex-start' }}>
                <StatusChip status={f.status} />
                <T v="body" style={{ flex: 1 }} color={statusColor(p, f.status).fg === p.danger ? p.danger : p.text}>{f.text}</T>
              </Row>
            ))}
            <T v="small">Reported by {s.radiologist}</T>
          </Card>
        );
      })}
    </Screen>
  );
}
