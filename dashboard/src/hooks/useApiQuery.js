import { useState, useEffect } from 'react';
import api from '../api';

/**
 * Generic API query hook with auto-refetch and manual refresh.
 *
 * @param {string} endpoint - API path (e.g. '/gsc/keywords')
 * @param {object} params   - query params (e.g. { days: 30 })
 * @param {array}  deps     - trigger refetch when these change
 * @returns {{ data, loading, error, refetch }}
 */
export function useApiQuery(endpoint, params = {}, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.get(endpoint, { params })
      .then(r => { if (!cancelled) setData(r.data); })
      .catch(err => { if (!cancelled) setError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });

    return () => { cancelled = true; };
  }, [...deps, refresh]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data,
    loading,
    error,
    refetch: () => setRefresh(r => r + 1),
  };
}
