import React, { useState, useEffect } from 'react';
import api from '../api';
import DataTable from '../components/DataTable';
import LoadingSpinner from '../components/LoadingSpinner';

const KRW_RATE = 1300;

const fmtR = (n) => (typeof n === 'number' ? '$' + n.toFixed(2) : n);
const fmtK = (n) => (typeof n === 'number' ? '₩' + n.toLocaleString() : n);

const shortUrl = (url) => {
  try {
    const u = new URL(url);
    const p = decodeURIComponent(u.pathname);
    return u.hostname.split('.')[0] + p.slice(0, 35) + (p.length > 35 ? '...' : '');
  } catch (e) {
    return url.slice(0, 45);
  }
};

const CpcHintPage = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/analysis/rpm-ranking')
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, alignItems: 'center' }}>
        <span style={{ fontSize: 18, fontWeight: 700 }}>고단가 힌트</span>
        <span style={{ fontSize: 12, color: '#6b7280' }}>RPM 상위 50개 페이지</span>
      </div>

      <DataTable
        columns={[
          { key: 'site', label: '사이트', render: (r) => (
            <a href={'https://' + r.site} target="_blank" rel="noreferrer"
               style={{ color: '#2563eb', textDecoration: 'none' }}>{r.site}</a>
          )},
          { key: 'page', label: '페이지', render: (r) => (
            <span title={r.page} style={{ fontSize: 12 }}>
              {shortUrl(r.page)}
            </span>
          )},
          { key: 'pv', label: 'PV', align: 'right' },
          { key: 'rev', label: '수익', align: 'right',
            render: (r) => <span style={{ color: '#16a34a', fontWeight: 600 }}>{fmtR(r.rev)}</span> },
          { key: 'rpm', label: 'RPM ($)', align: 'right',
            render: (r) => <span style={{ color: '#ca8a04', fontWeight: 600 }}>{fmtR(r.rpm)}</span> },
          { key: '_rpm_krw', label: 'RPM (₩)', align: 'right',
            render: (r) => {
              const krw = (r.rpm || 0) * KRW_RATE;
              return <span style={{ color: '#7c3aed', fontWeight: 600 }}>{fmtK(krw)}</span>;
            }},
        ]}
        data={data}
      />
    </div>
  );
};

export default CpcHintPage;
