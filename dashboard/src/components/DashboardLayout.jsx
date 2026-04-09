import React from 'react';

const TopBar = () => (
  <div style={{ 
    height: '60px', 
    display: 'flex', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    padding: '0 24px', 
    background: '#fff', 
    borderBottom: '1px solid #e5e7eb', 
    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
  }}>
    <div style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>블로그 대시보드</div>
    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
      <button style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer' }}>알림</button>
      <button style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer' }}>설정</button>
      <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>U</div>
    </div>
  </div>
);

const BottomNav = () => (
  <div style={{ 
    height: '60px', 
    display: 'flex', 
    justifyContent: 'center', 
    alignItems: 'center', 
    background: '#fff', 
    borderTop: '1px solid #e5e7eb', 
    boxShadow: '0 -1px 3px rgba(0,0,0,0.05)'
  }}>
    <div style={{ display: 'flex', gap: '32px' }}>
      {['대시보드', '분석', '수익', '설정'].map((item, index) => (
        <button key={index} style={{ 
          background: 'none', 
          border: 'none', 
          color: index === 0 ? '#3b82f6' : '#6b7280', 
          fontSize: '14px', 
          fontWeight: index === 0 ? 600 : 400, 
          cursor: 'pointer', 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          gap: '2px'
        }}>
          <span>{item}</span>
          {index === 0 && <div style={{ width: '4px', height: '4px', background: '#3b82f6', borderRadius: '50%' }} />}
        </button>
      ))}
    </div>
  </div>
);

const DashboardLayout = ({ children }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: '#f9fafb' }}>
      <TopBar />
      <main style={{ flex: 1, padding: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
        {children}
      </main>
      <BottomNav />
    </div>
  );
};

export default DashboardLayout;