import { useVideoPlayer, VideoView } from 'expo-video';
import React, { useEffect, useState } from 'react';
import { AccessibilityInfo, Pressable, StyleSheet, Text, View } from 'react-native';

import { fonts } from '@/lib/theme';

/** Telomy boot animation (from the brand video). Plays once per cold start; tap to skip; skipped under Reduce Motion. */
export function Intro({ onDone }: { onDone: () => void }) {
  const [reduce, setReduce] = useState<boolean | null>(null);
  const player = useVideoPlayer(require('../../assets/boot.mp4'), (p) => {
    p.muted = true;
    p.loop = false;
  });
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then((r) => {
      setReduce(r);
      if (r) onDone();
      else player.play();
    });
    const sub = player.addListener('playToEnd', onDone);
    const safety = setTimeout(onDone, 10000);
    return () => {
      sub.remove();
      clearTimeout(safety);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  if (reduce) return null;
  return (
    <Pressable onPress={onDone} style={[StyleSheet.absoluteFill, { backgroundColor: '#000', zIndex: 100 }]} accessibilityLabel="Skip intro" accessibilityRole="button">
      <VideoView player={player} style={StyleSheet.absoluteFill} contentFit="cover" nativeControls={false} />
      <View style={{ position: 'absolute', bottom: 60, width: '100%', alignItems: 'center' }}>
        <Text style={{ color: '#8E8C85', fontFamily: fonts.light, fontSize: 13, letterSpacing: 2 }}>TAP TO SKIP</Text>
      </View>
    </Pressable>
  );
}
