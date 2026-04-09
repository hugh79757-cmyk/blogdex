import React from 'react';

const StatCard = ({ label, value, change, unit = '', color = 'var(--text-primary)' }) => (
  <div style={{ background: '#fff', borderRadius: '12px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #e5e7eb' }}>
    <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '4px' }}>{label}</div>
    <div style={{ fontSize: '28px', fontWeight: 700, color, marginBottom: '4px' }}>{
      unit === '₩' ? `₩${Number(value).toLocaleString()}` : 
      unit === '$' ? `$${Number(value).toFixed(2)}` : 
      Number(value).toLocaleString()
    }</div>
    {change !== undefined && (
      <div style={{ fontSize: '12px', color: change >= 0 ? '#10b981' : '#ef4444' }}>
        {change >= 0 ? '↑' : '↓'} {Math.abs(change)}% vs 지난 기간
      </div>
    )}
  </div>
);

const UserStats = ({ stats }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
      <StatCard label="총 사용자" value={stats.totalUsers} change={stats.totalUsersChange} color="#3b82f6" />
      <StatCard label="활성 사용자" value={stats.activeUsers} change={stats.activeUsersChange} color="#10b981" />
      <StatCard label="총 수익" value={stats.totalRevenue} unit="₩" change={stats.totalRevenueChange} color="#f59e0b" />
      <StatCard label="MRR" value={stats.mrr} unit="$" change={stats.mrrChange} color="#8b5cf6" />
    </div>
  );
};

export default UserStats;