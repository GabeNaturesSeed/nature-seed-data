'use client';

import { useState, useEffect } from 'react';

const cache: Record<string, unknown> = {};

export function useJsonData<T>(filename: string): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>((cache[filename] as T) ?? null);
  const [loading, setLoading] = useState(!cache[filename]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (cache[filename]) {
      setData(cache[filename] as T);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    fetch(`/data/${filename}.json`)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(json => {
        if (!cancelled) {
          cache[filename] = json;
          setData(json as T);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [filename]);

  return { data, loading, error };
}
