import React, { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const fmtR = (n) => (typeof n === 'number' ? '$' + n.toFixed(2) : n);
const fmt = (n) => (typeof n === 'number' ? n.toLocaleString() : n);
const thStyle = { padding: '8px 12px', borderBottom: '2px solid #e5e7eb', textAlign: 'left', fontSize: 13, fontWeight: 600, background: '#f9fafb' };
const tdStyle = { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', fontSize: 13 };

const CoachingPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/coaching/today')
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (!data) return null;

  const s = data.summary || {};

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>오늘의 코칭</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: '이번달 수익', value: fmtR(s.month_revenue), bg: '#f0fdf4', color: '#16a34a' },
          { label: '목표 ($300)', value: s.month_progress + '%', bg: '#eff6ff', color: '#2563eb' },
          { label: '일평균', value: fmtR(s.daily_avg), bg: '#fefce8', color: '#ca8a04' },
          { label: '필요 일수익 ($300까지)', value: fmtR(s.daily_needed), bg: '#fef2f2', color: '#dc2626' },
        ].map((c, i) => (
          <div key={i} style={{ background: c.bg, borderRadius: 12, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>사이트별 수익 (30일)</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>PV</th>
              <th style={thStyle}>수익</th><th style={thStyle}>글 수</th>
            </tr></thead>
            <tbody>{(data.site_summary || []).slice(0, 20).map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.site}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{fmt(r.pv)}</td>
                <td style={{ ...tdStyle, textAlign: 'right', color: '#059669', fontWeight: 600 }}>{fmtR(r.rev)}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pages}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>타이틀 리라이트 대상</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>검색어</th>
              <th style={thStyle}>노출</th><th style={thStyle}>순위</th>
            </tr></thead>
            <tbody>{(data.rewrite_targets || []).map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.site}</td>
                <td style={{ ...tdStyle, fontSize: 12 }}>{r.query}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{fmt(r.imp)}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pos}위</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default CoachingPage;
