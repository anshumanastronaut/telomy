import React, { useState } from 'react';
import { Text, View } from 'react-native';

import { BodyScene, Projected } from '@/ui/body3d';

export default function BodyTest() {
  const [p, setP] = useState<Projected>({});
  return (
    <View style={{ flex: 1, backgroundColor: '#F2F8FB' }}>
      <BodyScene anchors={[{ id: 'heart', pos: [-0.04, 1.27, 0.09] }]} onProject={setP} height={680} />
      {p.heart ? <View style={{ position: 'absolute', left: p.heart.x - 5, top: p.heart.y - 5, width: 10, height: 10, borderRadius: 5, backgroundColor: '#E5533D' }} /> : null}
      <Text style={{ textAlign: 'center' }}>{JSON.stringify(p.heart ?? {})}</Text>
    </View>
  );
}
