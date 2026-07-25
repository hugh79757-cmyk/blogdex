import React, { useState, useEffect } from 'react';
import api from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

const thStyle = { padding: '8px 12px', borderBottom: '2px solid #e5e7eb', textAlign: 'left', fontSize: 13, fontWeight: 600, background: '#f9fafb' };
const tdStyle = { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', fontSize: 13 };

const OpportunityPage = () => {
  const [rewrite, setRewrite] = useState([]);
  const [topPages, setTopPages] = useState([]);
  const [seoOpp, setSeoOpp] = useState([]);
  const [blogEff, setBlogEff] = useState([]);
  const [rpmRanking, setRpmRanking] = useState([]);
  const [revSummary, setRevSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [panel, setPanel] = useState('rewrite');

  useEffect(() => {
    Promise.all([
      api.get('/analysis/rewrite-targets'),
      api.get('/analysis/top-pages'),
      api.get('/analysis/seo-opportunity'),
      api.get('/analysis/blog-efficiency'),
      api.get('/analysis/rpm-ranking'),
      api.get('/analysis/period-report', { params: { days: 30, limit: 200 } }),
    ]).then(([r, t, s, b, rpm, rev]) => {
      setRewrite(Array.isArray(r.data) ? r.data : []);
      setTopPages(Array.isArray(t.data) ? t.data : []);
      setSeoOpp(Array.isArray(s.data) ? s.data : []);
      setBlogEff(Array.isArray(b.data) ? b.data : []);
      setRpmRanking(Array.isArray(rpm.data) ? rpm.data : []);
      setRevSummary(Array.isArray(rev.data?.site_summary) ? rev.data.site_summary : []);
      setLoading(false);
    }).catch(e => { console.error(e); setLoading(false); });
  }, []);

  if (loading) return <LoadingSpinner />;

  const panels = [
    { key: 'rewrite', label: '타이틀 리라이트 대상', count: rewrite.length, color: '#ef4444' },
    { key: 'top', label: '트래픽 TOP 글', count: topPages.length, color: '#3b82f6' },
    { key: 'seo', label: '구글 SEO 보강', count: seoOpp.length, color: '#f59e0b' },
    { key: 'eff', label: '블로그별 효율', count: blogEff.length, color: '#10b981' },
    { key: 'rpm', label: 'RPM 높은 글', count: rpmRanking.length, color: '#8b5cf6' },
    { key: 'rev', label: '사이트별 수익', count: revSummary.length, color: '#ec4899' },
  ];

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>수익 기회</h2>
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {panels.map(b => (
          <button key={b.key} onClick={() => setPanel(b.key)} style={{
            padding: '12px 20px', borderRadius: 10, cursor: 'pointer', minWidth: 160, textAlign: 'left',
            border: panel === b.key ? '2px solid ' + b.color : '1px solid #e5e7eb',
            background: panel === b.key ? b.color + '15' : '#fff',
          }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: b.color }}>{b.count}</div>
            <div style={{ fontSize: 13, color: '#374151', marginTop: 4 }}>{b.label}</div>
          </button>
        ))}
      </div>

      {panel === 'rewrite' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>노출은 되지만 클릭이 없는 글 — 타이틀 변경 필요</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
              <th style={thStyle}>노출</th><th style={thStyle}>순위</th><th style={thStyle}>검색어</th>
            </tr></thead>
            <tbody>{rewrite.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <a href={r.page} target="_blank" rel="noreferrer" style={{ color: '#6b7280', fontSize: 12 }}>
                    {decodeURIComponent(r.page).split('/').pop() || r.page}
                  </a>
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>{r.imp}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pos}</td>
                <td style={{ ...tdStyle, fontSize: 11, color: '#6b7280', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.queries}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {panel === 'top' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>페이지뷰 TOP 30 — 가장 많이 읽히는 글</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
              <th style={thStyle}>PV</th><th style={thStyle}>세션</th>
            </tr></thead>
            <tbody>{topPages.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <a href={r.page} target="_blank" rel="noreferrer" style={{ color: '#6b7280', fontSize: 12 }}>
                    {decodeURIComponent(r.page).split('/').pop() || r.page}
                  </a>
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: '#059669' }}>{r.pv}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.sess}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {panel === 'seo' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>GA4 트래픽 있지만 구글 노출 없음 — SEO 보강 대상</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>URL</th><th style={thStyle}>PV</th>
            </tr></thead>
            <tbody>{seoOpp.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <a href={r.page} target="_blank" rel="noreferrer" style={{ color: '#6b7280', fontSize: 12 }}>
                    {decodeURIComponent(r.page).split('/').pop() || r.page}
                  </a>
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: '#d97706' }}>{r.pv}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {panel === 'eff' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>블로그별 효율 — 글 1편당 평균 PV</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>총 PV</th>
              <th style={thStyle}>글 수</th><th style={thStyle}>글당 PV</th>
            </tr></thead>
            <tbody>{blogEff.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.total_pv?.toLocaleString()}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pages}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: '#059669' }}>{r.pv_per_page}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {panel === 'rpm' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>RPM 높은 글 TOP 50 — 이런 주제가 돈이 됩니다</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
              <th style={thStyle}>PV</th><th style={thStyle}>수익($)</th><th style={thStyle}>RPM($)</th>
            </tr></thead>
            <tbody>{rpmRanking.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <a href={r.page} target="_blank" rel="noreferrer" style={{ color: '#6b7280', fontSize: 12 }}>
                    {decodeURIComponent(r.page).split('/').pop() || r.page}
                  </a>
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pv}</td>
                <td style={{ ...tdStyle, textAlign: 'right', color: '#059669' }}>${Number(r.rev).toFixed(2)}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: Number(r.rpm) > 10 ? '#dc2626' : Number(r.rpm) > 5 ? '#f59e0b' : '#6b7280' }}>${Number(r.rpm).toFixed(2)}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {panel === 'rev' && (
        <div>
          <h3 style={{ marginBottom: 12 }}>사이트별 수익 요약 — 어디에 글을 써야 돈이 되나</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>사이트</th><th style={thStyle}>총 PV</th>
              <th style={thStyle}>총 수익($)</th><th style={thStyle}>RPM($)</th><th style={thStyle}>글 수</th>
            </tr></thead>
            <tbody>{revSummary.map((r, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#2563eb' }}>{r.site}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.total_pv?.toLocaleString()}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: '#059669' }}>${Number(r.total_rev).toFixed(2)}</td>
                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 700, color: Number(r.rpm) > 5 ? '#dc2626' : Number(r.rpm) > 2 ? '#f59e0b' : '#6b7280' }}>${Number(r.rpm).toFixed(2)}</td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>{r.pages}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default OpportunityPage;
