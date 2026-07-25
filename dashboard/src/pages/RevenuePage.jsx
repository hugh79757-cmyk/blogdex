// Extracted from App.jsx (original lines: 1721-1887 — PeriodReport)
// TODO: Verify all state and API calls are correctly migrated

import React, { useState, useEffect } from 'react';
import api from '../api';
import DataTable, { useSortable } from '../components/DataTable';
import LoadingSpinner from '../components/LoadingSpinner';

const periods = [
  { days: 1,  label: '어제' },
  { days: 3,  label: '3일' },
  { days: 7,  label: '7일' },
  { days: 30, label: '30일' },
];

const fmt = (n) => (typeof n === 'number' ? n.toLocaleString() : n);
const fmtR = (n) => (typeof n === 'number' ? '$' + n.toFixed(2) : n);

const pillStyle = {
  padding: '6px 14px', borderRadius: 20, border: 'none',
  cursor: 'pointer', fontSize: 13, fontWeight: 500,
};

const shortUrl = (url) => {
  try {
    const u = new URL(url);
    const p = decodeURIComponent(u.pathname);
    return u.hostname.split('.')[0] + p.slice(0, 35) + (p.length > 35 ? '...' : '');
  } catch (e) {
    return url.slice(0, 45);
  }
};

const RevenuePage = () => {
  const [period, setPeriod] = useState(7);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get('/analysis/period-report', { params: { days: period, limit: 20 } })
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <LoadingSpinner />;
  if (!data) return null;

  const t = data.totals || {};
  const periodLabel = periods.find(p => p.days === period)?.label || period + '일';

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 700 }}>수익 분석</span>
        <div style={{ display: 'flex', gap: 4, marginLeft: 16 }}>
          {periods.map(p => (
            <button
              key={p.days}
              onClick={() => setPeriod(p.days)}
              style={{
                ...pillStyle,
                background: period === p.days ? '#3b82f6' : '#f3f4f6',
                color: period === p.days ? '#fff' : '#374151',
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── 요약 카드 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: `총 PV (${periodLabel})`, value: fmt(t.pv), bg: '#eff6ff', color: '#1d4ed8' },
          { label: `총 수익 (${periodLabel})`, value: fmtR(t.revenue), bg: '#f0fdf4', color: '#16a34a' },
          { label: '평균 RPM', value: fmtR(t.rpm), bg: '#fefce8', color: '#ca8a04' },
          { label: '활성 사이트', value: `${t.sites}개`, bg: '#faf5ff', color: '#7c3aed' },
        ].map((card, i) => (
          <div key={i} style={{ background: card.bg, borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{card.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: card.color }}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* ── 사이트별 수익 + 고RPM 페이지 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>사이트별 수익</h3>
          <DataTable
            columns={[
              { key: 'site', label: '사이트', render: (r) => (
                <a href={'https://' + r.site} target="_blank" rel="noreferrer"
                   style={{ color: '#2563eb', textDecoration: 'none' }}>{r.site}</a>
              )},
              { key: 'total_pv', label: 'PV', align: 'right' },
              { key: 'total_rev', label: '수익', align: 'right',
                render: (r) => <span style={{ color: '#16a34a', fontWeight: 600 }}>{fmtR(r.total_rev)}</span> },
              { key: '_rpm', label: 'RPM', align: 'right',
                render: (r) => {
                  const rpm = r.total_pv > 0 ? Math.round(r.total_rev / r.total_pv * 1000 * 100) / 100 : 0;
                  return fmtR(rpm);
                }},
            ]}
            data={data.site_summary || []}
          />
        </div>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>고RPM 페이지 (효율 상위)</h3>
          <DataTable
            columns={[
              { key: 'page', label: '페이지', render: (r) => (
                <span title={r.page} style={{ fontSize: 12 }}>
                  <a href={r.page} target="_blank" rel="noreferrer"
                     style={{ color: '#2563eb', textDecoration: 'none' }}>{shortUrl(r.page)}</a>
                </span>
              )},
              { key: 'pv', label: 'PV', align: 'right' },
              { key: 'rev', label: '수익', align: 'right',
                render: (r) => <span style={{ color: '#16a34a', fontWeight: 600 }}>{fmtR(r.rev)}</span> },
              { key: 'rpm', label: 'RPM', align: 'right',
                render: (r) => <span style={{ color: '#ca8a04', fontWeight: 600 }}>{fmtR(r.rpm)}</span> },
            ]}
            data={data.high_rpm_pages || []}
          />
        </div>
      </div>

      {/* ── 수익 상위 + 트래픽 상위 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>수익 상위 페이지</h3>
          <DataTable
            columns={[
              { key: 'page', label: '페이지', render: (r) => (
                <span title={r.page} style={{ fontSize: 12 }}>
                  <a href={r.page} target="_blank" rel="noreferrer"
                     style={{ color: '#2563eb', textDecoration: 'none' }}>{shortUrl(r.page)}</a>
                </span>
              )},
              { key: 'pv', label: 'PV', align: 'right' },
              { key: 'rev', label: '수익', align: 'right',
                render: (r) => <span style={{ color: '#16a34a', fontWeight: 600 }}>{fmtR(r.rev)}</span> },
              { key: 'rpm', label: 'RPM', align: 'right' },
            ]}
            data={data.top_revenue_pages || []}
          />
        </div>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>트래픽 상위 페이지</h3>
          <DataTable
            columns={[
              { key: 'page', label: '페이지', render: (r) => (
                <span title={r.page} style={{ fontSize: 12 }}>
                  <a href={r.page} target="_blank" rel="noreferrer"
                     style={{ color: '#2563eb', textDecoration: 'none' }}>{shortUrl(r.page)}</a>
                </span>
              )},
              { key: 'pv', label: 'PV', align: 'right' },
              { key: 'rev', label: '수익', align: 'right',
                render: (r) => r.rev > 0
                  ? <span style={{ color: '#16a34a' }}>{fmtR(r.rev)}</span>
                  : <span style={{ color: '#d1d5db' }}>-</span> },
              { key: 'rpm', label: 'RPM', align: 'right',
                render: (r) => r.rpm > 0 ? fmtR(r.rpm) : '-' },
            ]}
            data={data.top_pv_pages || []}
          />
        </div>
      </div>
    </div>
  );
};

export default RevenuePage;
