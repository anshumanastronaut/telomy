import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, Animated, Pressable, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api } from '@/lib/api';
import { radius, space } from '@/lib/theme';
import { Button, Icon, Row, T } from '@/ui/core';

// Always dark (DS §10.6). Large type, emergency/exit always visible.
const C = { bg: '#0E100F', text: '#ECEAE4', muted: '#8E8C85', copper: '#D69466', teal: '#6FBBA4', danger: '#E07B69' };
const PATTERNS = [
  { k: 'coherent', l: 'Coherent 5·5', inhale: 5, hold: 0, exhale: 5 },
  { k: 'box', l: 'Box 4·4·4·4', inhale: 4, hold: 4, exhale: 4 },
  { k: 'sleep', l: 'Wind-down 4·7·8', inhale: 4, hold: 7, exhale: 8 },
];

export default function Breathe() {
  const [mins, setMins] = useState(5);
  const [pat, setPat] = useState(PATTERNS[0]);
  const [running, setRunning] = useState(false);
  const [left, setLeft] = useState(0);
  const [phase, setPhase] = useState('Ready');
  const [done, setDone] = useState<string | null>(null);
  const scale = useRef(new Animated.Value(0.6)).current;
  const reduce = useRef(false);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then((v) => (reduce.current = v));
  }, []);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000);
    let stop = false;
    const cycle = async () => {
      while (!stop) {
        for (const [name, secs, to] of [['Breathe in', pat.inhale, 1], ['Hold', pat.hold, 1], ['Breathe out', pat.exhale, 0.6]] as const) {
          if (stop || !secs) continue;
          setPhase(name);
          Haptics.selectionAsync().catch(() => {});
          if (!reduce.current) Animated.timing(scale, { toValue: to, duration: secs * 1000, useNativeDriver: true }).start();
          await new Promise((r) => setTimeout(r, secs * 1000));
        }
      }
    };
    cycle();
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [running, pat, scale]);

  useEffect(() => {
    if (running && left === 0) finish(mins);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left, running]);

  async function finish(m: number) {
    setRunning(false);
    setPhase('Done');
    const used = Math.max(0.5, m);
    const r = await api('/sessions', { body: { kind: pat.k, minutes: used } }).catch(() => null);
    setDone(r ? `Session saved · ${Math.round(used)} min. Sinc will compare tonight's HRV with your baseline.` : 'Saved locally — we couldn’t reach the server.');
  }

  return (
    <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: insets.top, paddingBottom: insets.bottom }}>
      <Row style={{ padding: space[4] }}>
        <T v="h3" color={C.text}>Breathe</T>
        <View style={{ flex: 1 }} />
        <Pressable onPress={() => (running ? finish((mins * 60 - left) / 60) : router.back())} hitSlop={12} accessibilityLabel="End session" style={{ backgroundColor: C.danger, borderRadius: radius.pill, paddingHorizontal: 14, paddingVertical: 8 }}>
          <T v="body" color="#fff" style={{ fontWeight: '700' }}>{running ? 'End' : 'Close'}</T>
        </Pressable>
      </Row>
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: space[6] }}>
        <Animated.View style={{ width: 240, height: 240, borderRadius: 120, borderWidth: 2, borderColor: C.copper, alignItems: 'center', justifyContent: 'center', transform: [{ scale }] }}>
          <T v="h1" color={C.text} style={{ fontSize: 30 }}>{phase}</T>
        </Animated.View>
        <T v="numLg" color={C.copper}>
          {running ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}` : `${mins}:00`}
        </T>
        {done ? <T v="body" color={C.teal} style={{ textAlign: 'center', paddingHorizontal: 30 }}>{done}</T> : null}
      </View>
      {!running ? (
        <View style={{ padding: space[4], gap: space[3] }}>
          <Row>
            {[3, 5, 10, 20].map((m) => (
              <Pressable key={m} onPress={() => setMins(m)} style={{ flex: 1, paddingVertical: 12, borderRadius: radius.md, borderWidth: 1, borderColor: mins === m ? C.copper : '#2E332F', alignItems: 'center' }}>
                <T v="body" color={mins === m ? C.copper : C.muted}>{m} min</T>
              </Pressable>
            ))}
          </Row>
          <Row>
            {PATTERNS.map((x) => (
              <Pressable key={x.k} onPress={() => setPat(x)} style={{ flex: 1, paddingVertical: 10, borderRadius: radius.md, borderWidth: 1, borderColor: pat.k === x.k ? C.teal : '#2E332F', alignItems: 'center' }}>
                <T v="small" color={pat.k === x.k ? C.teal : C.muted}>{x.l}</T>
              </Pressable>
            ))}
          </Row>
          <Button kind="copper" title="Start" icon="play.fill" onPress={() => { setDone(null); setLeft(mins * 60); setRunning(true); }} testID="start-breathe" />
        </View>
      ) : (
        <Row style={{ padding: space[4], justifyContent: 'center' }}>
          <Icon name="waveform" color={C.muted} size={14} />
          <T v="small" color={C.muted}>{pat.l}</T>
        </Row>
      )}
    </View>
  );
}
