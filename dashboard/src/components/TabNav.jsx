import React from 'react';

const TABS = [
  '오늘의 코칭', '수익 분석', '수익 기회',
  '키워드', '사이트별', '스카우트', '고단가 힌트',
  '노인복지',
];

const TabNav = ({ activeTab, onTabChange }) => (
  <div style={{ display: 'flex', gap: 4, marginBottom: 24, flexWrap: 'wrap' }}>
    {TABS.map((t, i) => (
      <button
        key={i}
        onClick={() => onTabChange(i)}
        style={{
          padding: '8px 16px',
          borderRadius: 8,
          border: 'none',
          background: activeTab === i ? '#3b82f6' : '#f3f4f6',
          color: activeTab === i ? '#fff' : '#374151',
          cursor: 'pointer',
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        {t}
      </button>
    ))}
  </div>
);

export default TabNav;
