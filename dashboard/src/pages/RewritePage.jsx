import React, { useState, useEffect, useMemo } from 'react';
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

const RewritePage = () => {
  const [keywords, setKeywords] = useState([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get('/gsc/keywords?days=' + days + '&limit=500')
      .then(r => {
        const data = (Array.isArray(r.data) ? r.data : []).map(k => ({ ...k, value: classifyKw(k.query) }));
        const queue = [];
        for (const k of data) {
          const pos = k.avg_position;
          const ctr = k.ctr;
          const imp = k.impressions;
          let action = null;
          let priority = 0;
          if (pos <= 10 && ctr < 5 && imp >= 5) {
            action = '타이틀/메타 개선';
            priority = imp * (10 - ctr);
          } else if (pos > 10 && pos <= 20 && imp >= 5) {
            action = '콘텐츠 보강 → 1페이지';
            priority = imp * 2;
          } else if (imp >= 10 && k.clicks === 0) {
            action = '타이틀 전면 교체';
            priority = imp * 5;
          }
          if (action) queue.push({ ...k, action, priority });
        }
        queue.sort((a, b) => b.priority - a.priority);
        setKeywords(queue);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  const titleFixes = useMemo(() => keywords.filter(k => k.action === '타이틀/메타 개선'), [keywords]);
  const contentFixes = useMemo(() => keywords.filter(k => k.action === '콘텐츠 보강 → 1페이지'), [keywords]);
  const zeroClicks = useMemo(() => keywords.filter(k => k.action === '타이틀 전면 교체'), [keywords]);

  const pillStyle = { padding: '6px 14px', borderRadius: 8, border: 'none', fontSize: 12, cursor: 'pointer', fontWeight: 600 };

  return (
    <div>
      <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>리라이트 큐</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {[7, 30, 60, 90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{ ...pillStyle, background: days === d ? '#3b82f6' : '#e5e7eb', color: days === d ? '#fff' : '#333' }}>
            {d}일
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 20 }}>
        <StatBox label="타이틀/메타 개선" value={titleFixes.length} color="#ef4444" />
        <StatBox label="콘텐츠 보강" value={contentFixes.length} color="#f59e0b" />
        <StatBox label="타이틀 전면 교체" value={zeroClicks.length} color="#8b5cf6" />
      </div>

      {loading ? <LoadingSpinner /> : (
        <DataTable
          columns={[
            { key: 'query', label: '키워드' },
            { key: 'action', label: '액션',
              render: (r) => {
                const c = r.action.includes('메타') ? '#ef4444' : r.action.includes('보강') ? '#f59e0b' : '#8b5cf6';
                return <span style={{ padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600, background: c + '20', color: c }}>{r.action}</span>;
              }
            },
            { key: 'impressions', label: '노출', align: 'right' },
            { key: 'clicks', label: '클릭', align: 'right' },
            { key: 'ctr', label: 'CTR', align: 'right', render: (r) => r.ctr + '%' },
            { key: 'avg_position', label: '순위', align: 'right' },
          ]}
          data={keywords}
          emptyMessage="리라이트 대상 없음"
        />
      )}
    </div>
  );
};

const StatBox = ({ label, value, color }) => (
  <div style={{ padding: 16, borderRadius: 10, border: '1px solid #e5e7eb', background: '#fff' }}>
    <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
  </div>
);

export default RewritePage;
