// Exercise & training — every session from your phone's health app (80+ types), iPhone motion detection and the Telomy patch,
// each with its load (heart-rate zones when the patch/ring was worn), and a training status from how this week's
// load compares with your last four weeks. See lib/training.ts for the method.
import { router, Stack } from 'expo-router';
import React, { useEffect, useMemo, useState } from 'react';
import { Pressable, View } from 'react-native';
import { Band, bandAvailable } from '@/lib/band';
import { useHealth } from '@/lib/health';
import { data, radius, space, type, usePalette } from '@/lib/theme';
import { buildSessions, dailyLoads, trainingStatus, WORKOUT_TYPE_COUNT, type Session } from '@/lib/training';
import { useWellness, type MinuteRec } from '@/lib/wellness';
import { Card, Chip, Icon, Row, Screen, Section, T } from '@/ui/core';
import { WorkoutHrLine, WorkoutZoneBreakdown } from '@/ui/welltory';
import { phoneActivity, type PhoneActivity } from '../../modules/ky-ecg';

const ZONE = [data.hrv, data.activity, data.temp, data.heart, data.rem];

export default function Training() {
  const p = usePalette();
  const h = useHealth(28);
  const w = useWellness(null);
  const [motion, setMotion] = useState<PhoneActivity[]>([]);
  const [mins, setMins] = useState<MinuteRec[]>([]);
  useEffect(() => {
    phoneActivity(24 * 7).then(setMotion).catch(() => {});
    if (bandAvailable) Band.wellnessRead('minutes', 8).then((m) => setMins(m as MinuteRec[])).catch(() => {});
  }, []);
  const caps = bandAvailable ? (Band.listCaptures() as any[]) : [];
  const sessions = useMemo(() => buildSessions(h.data ?? [], motion, caps, mins, w.age), [h.data, motion, mins, w.age, caps.length]);
  const loads = dailyLoads(sessions, 28);
  const status = trainingStatus(loads);
  const tone = { good: p.success, warn: p.warn, bad: p.danger, info: data.sleep, muted: p.muted }[status.tone];
  const peak = Math.max(1, ...loads);   // 1 = no load yet → chart hidden
  const recent = sessions.filter((s) => Date.now() / 1000 - s.start < 14 * 86400);
  const week = sessions.filter((s) => Date.now() / 1000 - s.start < 7 * 86400);
  const weekMin = week.reduce((a, s) => a + s.min, 0);

  return (
    <Screen edges={[]}>
      <Stack.Screen options={{ title: 'Exercise & training' }} />

      <Card style={{ gap: space[2] }}>
        <Row>
          <T v="label" style={{ flex: 1 }}>Training status</T>
          <Chip label={status.label} fg={tone} bg={p.surfaceAlt} />
        </Row>
        <Row gap={space[5]} style={{ alignItems: 'baseline' }}>
          <View><T v="num" style={{ fontSize: type.h1 }}>{week.length}</T><T v="small">sessions this week</T></View>
          <View><T v="num" style={{ fontSize: type.h1 }}>{weekMin >= 60 ? `${Math.floor(weekMin / 60)}h ${weekMin % 60}m` : `${weekMin}m`}</T><T v="small">active time</T></View>
          {status.ratio != null ? <View><T v="num" style={{ fontSize: type.h1 }} color={tone}>{status.ratio.toFixed(2)}</T><T v="small">load vs usual</T></View> : null}
        </Row>
        <T v="small">{status.advice}</T>
      </Card>

      {peak > 1 ? (
      <Section title="Load, last 4 weeks">
        <Card style={{ gap: space[2] }}>
          <Row style={{ alignItems: 'flex-end', height: 90 }} gap={2}>
            {loads.map((l, i) => (
              <View key={i} style={{ flex: 1, height: Math.max(2, (l / peak) * 86), borderRadius: 2, backgroundColor: i >= 21 ? data.heart : p.surfaceAlt }} />
            ))}
          </Row>
          <Row>
            <T v="small" style={{ flex: 1, fontSize: type.micro }} color={p.faint}>4 weeks ago</T>
            <T v="small" style={{ fontSize: type.micro }} color={p.faint}>This week (red)</T>
          </Row>
          <T v="small">Each bar is a day's training load. Heart-rate zones set the load when the patch or ring was on; otherwise it is estimated from the activity and its length.</T>
        </Card>
      </Section>
      ) : null}

      <Section title="Sessions">
        {recent.length ? recent.map((s) => <SessionRow key={s.id} s={s} mins={mins} age={w.age} />) : (
          <Card>
            <T v="h3">No sessions yet</T>
            <T v="small">Workouts sync from your phone's health app (Apple Health on iPhone; Health Connect — Samsung Health & Google Fit — on Android). Walks, runs and rides of 10 minutes or more are detected by your iPhone on their own.</T>
          </Card>
        )}
      </Section>

      <Card>
        <T v="label">What Telomy recognises</T>
        <T v="small">{WORKOUT_TYPE_COUNT} activity types from your phone's health app, from running, cycling, swimming and strength to yoga, HIIT, badminton, cricket and pickleball. Your iPhone's motion chip detects walks, runs and rides automatically; heart-rate zones from the patch or ring measure how hard every session was, whatever its type.</T>
      </Card>
    </Screen>
  );
}

function SessionRow({ s, mins = [], age = 35 }: { s: Session; mins?: MinuteRec[]; age?: number }) {
  const p = usePalette();
  const when = new Date(s.start * 1000);
  const total = s.zones?.reduce((a, b) => a + b, 0) ?? 0;
  return (
    <Card style={{ gap: space[2] }}>
      <Row>
        <View style={{ width: 36, height: 36, borderRadius: radius.md, backgroundColor: p.surfaceAlt, alignItems: 'center', justifyContent: 'center' }}>
          <Icon name={s.icon} size={18} color={data.activity} />
        </View>
        <View style={{ flex: 1 }}>
          <T v="h3" numberOfLines={1}>{s.name}</T>
          <T v="small">{when.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })} · {when.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} · {s.min} min</T>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <T v="num" style={{ fontSize: type.title }}>{Math.round(s.load)}</T>
          <T v="small" style={{ fontSize: type.micro }}>{s.loadFromHr ? 'load · heart rate' : 'load · estimated'}</T>
        </View>
      </Row>
      <Row gap={space[3]} style={{ flexWrap: 'wrap' }}>
        {s.km ? <T v="small">{s.km.toFixed(2)} km</T> : null}
        {s.kcal ? <T v="small">{Math.round(s.kcal)} kcal</T> : null}
        {s.avgHr ? <T v="small">avg {Math.round(s.avgHr)} bpm{s.maxHr ? ` · max ${Math.round(s.maxHr)}` : ''}</T> : null}
        <T v="small" color={p.faint}>{s.source}{s.device && s.source === 'Apple Health' ? ` · ${s.device}` : ''}</T>
      </Row>
      <WorkoutHrLine mins={mins} start={s.start} end={s.end} age={age} />
      {total ? <WorkoutZoneBreakdown zones={s.zones!} /> : null}
    </Card>
  );
}
