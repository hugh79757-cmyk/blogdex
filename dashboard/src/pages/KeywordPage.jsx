import React, { useState, useEffect } from 'react';
import api from '../api';
import DataTable from '../components/DataTable';
import LoadingSpinner from '../components/LoadingSpinner';

const HIGH_PATTERNS = ['추천','비교','가격','후기','리뷰','순위','신청','방법','절차','가입','등록','발급','할인','쿠폰','무료','혜택','보험','대출','적금','투자','보조금','지원금','환급','세금','vs','차이','장단점','구매'];
const LOW_PATTERNS = ['뜻','의미','영어로','누구','나이','키','몸무게','생일','mbti','학력'];

const classifyKw = (q) => {
  const ql = q.toLowerCase();
  for (const p of HIGH_PATTERNS) { if (ql.includes(p)) return 'high'; }
  for (const p of LOW_PATTERNS) { if (ql.includes(p)) return 'low'; }
  return 'medium';
};

const pillStyle = { padding: '6px 14px', borderRadius: 8, border: 'none', fontSize: 12, cursor: 'pointer', fontWeight: 600 };

const KeywordPage = () => {
  const [keywords, setKeywords] = useState([]);
  const [days, setDays] = useState(30);
  const [filter, setFilter] = useState('');
  const [limit, setLimit] = useState(200);

  useEffect(() => {
    api.get('/gsc/keywords?days=' + days + '&limit=200').then(r => {
      const data = (Array.isArray(r.data) ? r.data : []).map(k => ({ ...k, value: classifyKw(k.query) }));
      if (filter) {
        setKeywords(data.filter(k => k.value === filter));
      } else {
        setKeywords(data);
      }
    }).catch(console.error);
  }, [days, filter]);

  const high = keywords.filter(k => k.value === 'high').length;
  const med = keywords.filter(k => k.value === 'medium').length;
  const low = keywords.filter(k => k.value === 'low').length;

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>키워드</h2>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {[7, 30, 60, 90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{ ...pillStyle, background: days === d ? '#3b82f6' : '#e5e7eb', color: days === d ? '#fff' : '#333' }}>
            {d}일
          </button>
        ))}
        <span style={{ width: 16 }} />
        {[{ l: '전체', v: '' }, { l: 'HIGH', v: 'high' }, { l: 'MED', v: 'medium' }, { l: 'LOW', v: 'low' }].map(f => (
          <button key={f.v} onClick={() => setFilter(f.v)}
            style={{ ...pillStyle, background: filter === f.v ? '#3b82f6' : '#e5e7eb', color: filter === f.v ? '#fff' : '#333' }}>
            {f.l}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 16, alignItems: 'center' }}>
        <span style={{ fontSize: 12, color: '#6b7280', marginRight: 4 }}>표시:</span>
        {[50, 100, 200, 500].map(n => (
          <button key={n} onClick={() => setLimit(n)}
            style={{ padding: '4px 10px', borderRadius: 6, border: 'none', fontSize: 12, cursor: 'pointer',
              background: limit === n ? '#3b82f6' : '#e5e7eb', color: limit === n ? '#fff' : '#333' }}>
            {n}개
          </button>
        ))}
      </div>

      <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>
        총 {keywords.length}개 | HIGH {high} | MED {med} | LOW {low}
      </div>

      <DataTable
        columns={[
          { key: 'query', label: '키워드' },
          { key: 'blog_name', label: '블로그', render: (r) => <span style={{ fontSize: 11, color: '#6b7280' }}>{r.blog_name || r.site || '-'}</span> },
          { key: 'value', label: '가치',
            render: (r) => {
              const c = r.value === 'high' ? '#dc2626' : r.value === 'medium' ? '#d97706' : '#6b7280';
              const bg = r.value === 'high' ? '#fee2e2' : r.value === 'medium' ? '#fef3c7' : '#f3f4f6';
              return <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600, background: bg, color: c }}>{r.value.toUpperCase()}</span>;
            }
          },
          { key: 'impressions', label: '노출', align: 'right' },
          { key: 'clicks', label: '클릭', align: 'right' },
          { key: 'ctr', label: 'CTR', align: 'right', render: (r) => r.ctr + '%' },
          { key: 'avg_position', label: '순위', align: 'right' },
        ]}
        data={keywords}
        emptyMessage="키워드 데이터 없음"
      />
    </div>
  );
};

export default KeywordPage;
