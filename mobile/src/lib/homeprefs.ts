// What the Home (Today) screen shows, and in what order — fully customisable. Stored per device (AsyncStorage); the
// Today screen renders the enabled sections in the saved order. Defaults keep the current layout so nothing changes
// until the person customises it.
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useState } from 'react';

export type HomeWidget =
  | 'recovery' | 'sleep' | 'vitals' | 'timeline' | 'bioage' | 'longevity' | 'strain' | 'stress' | 'fitness' | 'activity' | 'devices' | 'daytimeline';

export const WIDGETS: { key: HomeWidget; label: string; desc: string }[] = [
  { key: 'recovery', label: 'Recovery dial', desc: 'The big readiness score for today' },
  { key: 'sleep', label: 'Last night', desc: 'Sleep stages, duration and score' },
  { key: 'vitals', label: 'Vitals grid', desc: 'HR, HRV, SpO₂, temperature, breathing, steps…' },
  { key: 'timeline', label: 'Day timeline', desc: 'Your day hour by hour' },
  { key: 'daytimeline', label: 'Vitals timeline', desc: 'All-day heart rate and vitals with events on one clock (needs the patch/WHOOP)' },
  { key: 'strain', label: 'Effort / strain', desc: "Today's training load" },
  { key: 'stress', label: 'Stress', desc: 'Autonomic stress through the day' },
  { key: 'fitness', label: 'Fitness', desc: 'VO₂max and resting heart rate' },
  { key: 'bioage', label: 'Biological age', desc: 'Blood, heart, muscle and fitness ages' },
  { key: 'longevity', label: 'Longevity', desc: 'Your blood age vs chronological' },
  { key: 'activity', label: 'Activity & events', desc: 'Workouts, therapies and what you logged' },
  { key: 'devices', label: 'Devices', desc: 'Patch, ring, Apple Health status' },
];

// Default order matches the current Home so existing users see no change until they customise.
export const DEFAULT_ORDER: HomeWidget[] = ['recovery', 'sleep', 'vitals', 'timeline', 'strain', 'fitness', 'bioage', 'activity', 'devices'];

const KEY = 'telomy.home.layout.v1';
export type HomeLayout = { order: HomeWidget[]; enabled: Record<HomeWidget, boolean> };

function defaults(): HomeLayout {
  const enabled = Object.fromEntries(WIDGETS.map((w) => [w.key, DEFAULT_ORDER.includes(w.key)])) as Record<HomeWidget, boolean>;
  return { order: [...DEFAULT_ORDER, ...WIDGETS.map((w) => w.key).filter((k) => !DEFAULT_ORDER.includes(k))], enabled };
}

export function useHomeLayout() {
  const [layout, setLayout] = useState<HomeLayout>(defaults());
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    AsyncStorage.getItem(KEY).then((raw) => {
      if (raw) {
        try {
          const l = JSON.parse(raw) as HomeLayout;
          const d = defaults();
          // merge so new widgets appear and removed ones drop, without losing the person's choices
          const order = [...l.order.filter((k) => d.enabled[k] !== undefined), ...d.order.filter((k) => !l.order.includes(k))];
          const enabled = { ...d.enabled, ...l.enabled };
          setLayout({ order, enabled });
        } catch { /* keep defaults */ }
      }
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);
  const save = useCallback(async (l: HomeLayout) => { setLayout(l); try { await AsyncStorage.setItem(KEY, JSON.stringify(l)); } catch {} }, []);
  const toggle = useCallback((k: HomeWidget) => save({ ...layout, enabled: { ...layout.enabled, [k]: !layout.enabled[k] } }), [layout, save]);
  const move = useCallback((k: HomeWidget, dir: -1 | 1) => {
    const order = [...layout.order];
    const i = order.indexOf(k);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    save({ ...layout, order });
  }, [layout, save]);
  const reset = useCallback(() => save(defaults()), [save]);
  return { layout, loaded, toggle, move, reset, enabledInOrder: layout.order.filter((k) => layout.enabled[k]) };
}
