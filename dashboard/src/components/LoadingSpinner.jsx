import React from 'react';

const LoadingSpinner = ({ message = '로딩 중...' }) => (
  <div style={{
    display: 'flex', justifyContent: 'center', alignItems: 'center',
    minHeight: 300, color: '#6b7280', fontSize: 16,
  }}>
    {message}
  </div>
);

export default LoadingSpinner;
