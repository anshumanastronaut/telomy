// Foreground location → live environment ("here right now"). Permission is asked only when the member opens a
// location feature, used while the app is open, and never stored (the backend /environment/here is stateless).
import * as Location from 'expo-location';
import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from './api';

export type HereEnv = {
  ok: boolean; reason?: string; place?: string; lat?: number; lon?: number; as_of?: string;
  current?: {
    pm2_5?: number; pm10?: number; no2?: number; ozone?: number; us_aqi?: number; uv_index?: number;
    aqi_category?: string; temp_c?: number; feels_like_c?: number; humidity?: number; wind_kmh?: number;
    is_day?: boolean; weather?: string;
  };
  uv_max_today?: number; temp_min_today?: number; temp_max_today?: number; sunrise?: string; sunset?: string;
  outdoor_score?: number; outdoor_band?: string;
  alerts?: { level: 'ok' | 'warn' | 'danger'; icon: string; text: string }[];
  source?: string;
};

export type HereStatus = 'idle' | 'asking' | 'denied' | 'loading' | 'ready' | 'error';

/** Get the device location (when-in-use) and the live conditions there. `auto` requests on mount. */
export function useHere(auto = true) {
  const [data, setData] = useState<HereEnv | null>(null);
  const [status, setStatus] = useState<HereStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const load = useCallback(async () => {
    try {
      setError(null); setStatus('asking');
      let perm = await Location.getForegroundPermissionsAsync();
      if (!perm.granted && perm.canAskAgain) perm = await Location.requestForegroundPermissionsAsync();
      if (!perm.granted) { if (alive.current) setStatus('denied'); return; }
      if (alive.current) setStatus('loading');
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Low });
      const env = await api<HereEnv>(`/environment/here?lat=${pos.coords.latitude.toFixed(4)}&lon=${pos.coords.longitude.toFixed(4)}`);
      if (!alive.current) return;
      setData(env); setStatus(env.ok ? 'ready' : 'error');
      if (!env.ok) setError(env.reason ?? 'Could not load conditions.');
    } catch (e: any) {
      if (alive.current) { setError(e?.message ?? 'Location unavailable.'); setStatus('error'); }
    }
  }, []);

  useEffect(() => { if (auto) load(); }, [auto, load]);
  return { data, status, error, reload: load };
}
