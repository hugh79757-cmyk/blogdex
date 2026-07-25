import React, { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const fmt = (n) => (typeof n === 'number' ? n.toLocaleString() : n);
const thStyle = { padding: '8px 12px', borderBottom: '2px solid #e5e7eb', textAlign: 'left', fontSize: 13, fontWeight: 600, background: '#f9fafb' };
const tdStyle = { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', fontSize: 13 };

const periods = [
  { days: 7, label: '7일' },
  { days: 30, label: '30일' },
  { days: 90, label: '90일' },
];

const SitePage = () => {
  const [period, setPeriod] = useState(30);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get('/gsc/sites', { params: { days: period } })
      .then(r => setData(Array.isArray(r.data) ? r.data : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 700 }}>사이트별 GSC 성과</span>
        <div style={{ display: 'flex', gap: 4, marginLeft: 16 }}>
          {periods.map(p => (
            <button key={p.days} onClick={() => setPeriod(p.days)} style={{
              padding: '6px 14px', borderRadius: 20, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500,
              background: period === p.days ? '#3b82f6' : '#f3f4f6',
              color: period === p.days ? '#fff' : '#374151',
            }}>{p.label}</button>
          ))}
        </div>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead><tr>
          <th style={thStyle}>사이트</th>
          <th style={thStyle}>클릭</th><th style={thStyle}>노출</th><th style={thStyle}>CTR</th>
        </tr></thead>
        <tbody>{data.map((r, i) => (
          <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
            <td style={{ ...tdStyle, fontWeight: 600 }}>{r.site}</td>
            <td style={{ ...tdStyle, textAlign: 'right' }}>{fmt(r.clicks)}</td>
            <td style={{ ...tdStyle, textAlign: 'right' }}>{fmt(r.impressions)}</td>
            <td style={{ ...tdStyle, textAlign: 'right' }}>{r.ctr}%</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
};

export default SitePage;
