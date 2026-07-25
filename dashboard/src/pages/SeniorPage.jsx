import React, { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const thStyle = { padding: '8px 12px', borderBottom: '2px solid #e5e7eb', textAlign: 'left', fontSize: 13, fontWeight: 600, background: '#f9fafb' };
const tdStyle = { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', fontSize: 13 };

const SeniorPage = () => {
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

  const zeroRev = data.zero_revenue_sites || [];
  const topRpm = data.top_rpm_pages || [];

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>수익 개선 포인트</h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>
            수익 0 사이트 (7일간 PV &ge; 50)
          </h3>
          <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
            트래픽은 있지만 AdSense 수익이 없는 사이트 — GA4-AdSense 링크 또는 광고 코드 확인 필요
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>PV</th>
            </tr></thead>
            <tbody>{zeroRev.length === 0 ? (
              <tr><td colSpan={2} style={{ ...tdStyle, color: '#9ca3af', textAlign: 'center' }}>해당 사이트 없음</td></tr>
            ) : zeroRev.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.site}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pv}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>

        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 10 }}>고RPM 페이지 TOP 10</h3>
          <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 10 }}>
            적은 트래픽으로 높은 수익을 내는 글 — 이 주제를 확장하세요
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>PV</th>
              <th style={thStyle}>수익</th><th style={thStyle}>RPM</th>
            </tr></thead>
            <tbody>{topRpm.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600 }}>{r.site}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pv}</td>
                <td style={{ ...tdStyle, textAlign: 'right', color: '#059669' }}>${Number(r.rev).toFixed(2)}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: Number(r.rpm) > 5 ? '#dc2626' : '#ca8a04' }}>${Number(r.rpm).toFixed(2)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SeniorPage;
