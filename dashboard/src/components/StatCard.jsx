import React from 'react';

const StatCard = ({ label, value, color = 'var(--text-primary)', unit = '', change }) => (
  <div style={{
    padding: 16, background: '#fff', borderRadius: 12,
    border: '1px solid #e5e7eb', boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
  }}>
    <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 700, color, marginBottom: 4 }}>
      {unit === '₩' ? `₩${Number(value).toLocaleString()}` :
       unit === '$' ? `$${Number(value).toFixed(2)}` :
       Number(value).toLocaleString()}
    </div>
    {change !== undefined && (
      <div style={{ fontSize: 12, color: change >= 0 ? '#10b981' : '#ef4444' }}>
        {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
      </div>
    )}
  </div>
);

export default StatCard;
