import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { api, ApiError } from './api/client';

/** Load data from the API with loading / error state. Reloads when the screen regains focus. */
export function useApi<T>(path: string | null, params?: Record<string, any>, opts: { refetchOnFocus?: boolean } = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const key = JSON.stringify([path, params]);
  const first = useRef(true);

  const load = useCallback(async () => {
    if (!path) return;
    setLoading(true);
    setError(null);
    try {
      setData(await api<T>(path, { params }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'حدث خطأ غير متوقع.');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    load();
  }, [load]);

  useFocusEffect(
    useCallback(() => {
      if (first.current) {
        first.current = false;
        return;
      }
      if (opts.refetchOnFocus !== false) load();
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [load]),
  );

  return { data, error, loading, reload: load, setData };
}
