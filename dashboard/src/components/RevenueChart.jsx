import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const RevenueChart = ({ data, timeRange }) => {
  const formatYAxis = (value) => {
    if (value >= 1000000) return `${value / 1000000}M`;
    if (value >= 1000) return `${value / 1000}K`;
    return value;
  };

  return (
    <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #e5e7eb' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>수익 추이 ({timeRange})</h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: '#10b981' }}>● 수익</span>
          <span style={{ fontSize: '12px', color: '#3b82f6' }}>● 페이지뷰</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(date) => timeRange === '1W' ? date.slice(5) : date} />
          <YAxis yAxisId="left" orientation="left" stroke="#10b981" tickFormatter={formatYAxis} />
          <YAxis yAxisId="right" orientation="right" stroke="#3b82f6" tickFormatter={formatYAxis} />
          <Tooltip 
            formatter={(value, name) => [value.toLocaleString(), name]}
            labelFormatter={(label) => `날짜: ${label}`}
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
          />
          <Legend wrapperStyle={{ fontSize: '12px' }} />
          <Line yAxisId="left" type="monotone" dataKey="revenue" name="수익" stroke="#10b981" strokeWidth={2} dot={false} />
          <Line yAxisId="right" type="monotone" dataKey="pv" name="페이지뷰" stroke="#3b82f6" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default RevenueChart;