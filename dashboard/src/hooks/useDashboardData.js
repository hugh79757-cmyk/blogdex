import { useState, useEffect } from 'react';
import api from '../api';

/**
 * 대시보드 데이터를 API에서 가져오는 커스텀 훅.
 *
 * @param {number} days - 조회 기간 (7, 30, 90)
 * @returns {{ data: object|null, loading: boolean, error: Error|null }}
 *
 * data.shape:
 *   summary:     { blogs, posts, titles, gsc_clicks, gsc_impressions, coupang_revenue, coupang_orders }
 *   revSummary:  { today_revenue, yesterday_revenue, avg7_revenue, month_revenue,
 *                  today_pv, yesterday_pv, daily_revenue: [{date, pv, rev}, ...],
 *                  top_sites, zero_revenue_sites }
 *   gscDaily:    [{ date, clicks, impressions, ctr }, ...]
 *   coupang:     { daily: [...], totals: { clicks, orders, amount, revenue } }
 */
export function useDashboardData(days = 30) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    Promise.all([
      api.get(`/dashboard/summary?days=${days}`),
      api.get(`/analysis/revenue-summary`),
      api.get(`/gsc/daily?days=${days}`),
      api.get(`/coupang/summary?days=${days}`),
    ])
      .then(([summary, revSummary, gscDaily, coupang]) => {
        if (cancelled) return;
        setData({
          summary: summary.data,
          revSummary: revSummary.data,
          gscDaily: gscDaily.data,
          coupang: coupang.data,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [days]);

  return { data, loading, error };
}
