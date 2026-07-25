import React from 'react';

const ErrorMessage = ({ message = '데이터를 불러올 수 없습니다.', detail }) => (
  <div style={{
    display: 'flex', flexDirection: 'column', justifyContent: 'center',
    alignItems: 'center', minHeight: 300,
  }}>
    <p style={{ fontSize: 16, color: '#ef4444', marginBottom: 8 }}>{message}</p>
    {detail && <p style={{ fontSize: 13, color: '#6b7280' }}>{detail}</p>}
  </div>
);

export default ErrorMessage;
