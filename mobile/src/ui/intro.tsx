import React, { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts } from '@/lib/theme';
import { TelomyLoader } from '@/ui/loader';
import { Logo } from '@/ui/logo';

/** Telomy boot animation — the DNA-helix motion mark on the brand dark, then the wordmark. Plays once per cold
 *  start; tap to skip; shortened under Reduce Motion. */
export function Intro({ onDone }: { onDone: () => void }) {
  const [reduce, setReduce] = useState(false);
  const done = useRef(false);
  const finish = () => { if (!done.current) { done.current = true; onDone(); } };
  useEffect(() => {
    let timer: any;
    AccessibilityInfo.isReduceMotionEnabled().then((r) => {
      setReduce(r);
      timer = setTimeout(finish, r ? 900 : 2600);
    }).catch(() => { timer = setTimeout(finish, 2600); });
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <Pressable onPress={finish} style={[StyleSheet.absoluteFill, { backgroundColor: '#0B0D0D', zIndex: 100, alignItems: 'center', justifyContent: 'center' }]}
      accessibilityLabel="Skip intro" accessibilityRole="button">
      <View style={{ alignItems: 'center', gap: 30 }}>
        <TelomyLoader tint="#F8F8F5" width={300} height={122} count={13} />
        <Logo kind="word" width={168} tone="dark" />
      </View>
      {!reduce ? (
        <View style={{ position: 'absolute', bottom: 60, width: '100%', alignItems: 'center' }}>
          <Text style={{ color: '#8E8C85', fontFamily: fonts.light, fontSize: 13, letterSpacing: 2 }}>TAP TO SKIP</Text>
        </View>
      ) : null}
    </Pressable>
  );
}
