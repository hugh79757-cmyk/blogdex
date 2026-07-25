import React from 'react';

const StatCard = ({ label, value, unit = '', color = 'var(--text-primary)' }) => (
  <div style={{
    background: '#fff', borderRadius: '12px', padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #e5e7eb'
  }}>
    <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '28px', fontWeight: 700, color, marginBottom: '4px' }}>
      {unit === '₩'
        ? `₩${Number(value).toLocaleString()}`
        : unit === '$'
          ? `$${Number(value).toFixed(2)}`
          : Number(value).toLocaleString()}
    </div>
  </div>
);

/**
 * 블로그 성능 요약 통계.
 *
 * @param {{ stats: { totalClicks, totalImpressions, avgCtr, totalBlogs, totalPosts, coupangRevenue, coupangOrders } }} props
 */
const UserStats = ({ stats }) => {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: '16px', marginBottom: '24px'
    }}>
      <StatCard label="총 클릭" value={stats.totalClicks} color="#3b82f6" />
      <StatCard label="총 노출" value={stats.totalImpressions} color="#10b981" />
      <StatCard label="평균 CTR" value={stats.avgCtr} color="#f59e0b" />
      <StatCard label="관리 블로그" value={stats.totalBlogs} color="#8b5cf6" />
      <StatCard label="전체 글" value={stats.totalPosts} color="#ec4899" />
      <StatCard label="쿠팡 수익" value={stats.coupangRevenue} unit="₩" color="#ef4444" />
    </div>
  );
};

export default UserStats;
