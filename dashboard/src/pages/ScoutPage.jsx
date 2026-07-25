import React, { useState } from 'react';
import api from '../api';

const thStyle = { padding: '8px 12px', borderBottom: '2px solid #e5e7eb', textAlign: 'left', fontSize: 13, fontWeight: 600, background: '#f9fafb' };
const tdStyle = { padding: '8px 12px', borderBottom: '1px solid #f3f4f6', fontSize: 13 };

const ScoutPage = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const r = await api.get('/scout', { params: { q: query, display: 10 } });
      setResult(r.data);
    } catch (e) {
      alert('검색 실패: ' + (e.response?.data?.error || e.message));
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter') search(); };

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>네이버 블로그 스카우트</h2>

      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <input
          value={query} onChange={e => setQuery(e.target.value)} onKeyDown={handleKeyDown}
          placeholder="검색어를 입력하세요"
          style={{ flex: 1, padding: '10px 14px', borderRadius: 8, border: '1px solid #d1d5db', fontSize: 14 }}
        />
        <button onClick={search} disabled={loading} style={{
          padding: '10px 24px', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 600,
          background: loading ? '#9ca3af' : '#3b82f6', color: '#fff',
        }}>
          {loading ? '검색중...' : '검색'}
        </button>
      </div>

      {result && (
        <div>
          <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 12 }}>
            총 {result.total || 0}건 · 표시: {(result.items || []).length}건
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={thStyle}>블로그명</th><th style={thStyle}>글</th>
              <th style={thStyle}>날짜</th><th style={thStyle}>링크</th>
            </tr></thead>
            <tbody>{(result.items || []).map((item, i) => (
              <tr key={i} style={{ background: i % 2 ? '#f9fafb' : '#fff' }}>
                <td style={tdStyle}>{item.bloggername || '-'}</td>
                <td style={{ ...tdStyle, maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span dangerouslySetInnerHTML={{ __html: item.title || '' }} />
                </td>
                <td style={tdStyle}>{item.postdate || '-'}</td>
                <td style={tdStyle}>
                  <a href={item.link} target="_blank" rel="noreferrer" style={{ color: '#2563eb', fontSize: 12 }}>열기</a>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ScoutPage;
