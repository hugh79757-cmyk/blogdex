import React, { useState } from 'react';
import RevenueChart from '../components/RevenueChart';
import UserStats from '../components/UserStats';
import RecentActivity from '../components/RecentActivity';
import DashboardLayout from '../components/DashboardLayout';

const generateRevenueData = (days, month) => {
  return Array.from({ length: days }, (_, i) => {
    const date = `${2026}-${month}-${String(i + 1).padStart(2, '0')}`;
    const baseRevenue = month === '03' ? 100000 : 50000;
    const revenueVariation = month === '03' ? 50000 : 100000;
    const basePV = month === '03' ? 20000 : 10000;
    const pvVariation = month === '03' ? 10000 : 20000;
    return {
      date,
      revenue: baseRevenue + Math.floor(Math.random() * revenueVariation),
      pv: basePV + Math.floor(Math.random() * pvVariation)
    };
  });
};

const Dashboard = () => {
  // Mock data
  const revenueData = React.useMemo(() => ({
    '1W': [
      { date: '2026-04-01', revenue: 120000, pv: 24000 },
      { date: '2026-04-02', revenue: 135000, pv: 27000 },
      { date: '2026-04-03', revenue: 142000, pv: 28400 },
      { date: '2026-04-04', revenue: 150000, pv: 30000 },
      { date: '2026-04-05', revenue: 160000, pv: 32000 },
      { date: '2026-04-06', revenue: 155000, pv: 31000 },
      { date: '2026-04-07', revenue: 170000, pv: 34000 }
    ],
    '1M': generateRevenueData(30, '03'),
    '3M': generateRevenueData(90, '01')
  }), []);

  const userStats = {
    totalUsers: 1248,
    totalUsersChange: 12,
    activeUsers: 872,
    activeUsersChange: 8,
    totalRevenue: 4850000,
    totalRevenueChange: 15,
    mrr: 1240.50,
    mrrChange: 5
  };

  const recentActivities = [
    { user: '홍길동', action: '새 포스트 발행: "블로그 수익 극대화 방법"', time: '2026-04-07T09:30:00' },
    { user: '김블로거', action: '수익 인출: ₩50,000', time: '2026-04-07T08:15:00' },
    { user: '박마케터', action: '광고 캠페인 시작: "구글 애드센스 최적화"', time: '2026-04-06T17:45:00' },
    { user: '이디자이너', action: '블로그 템플릿 업데이트: "모바일 최적화"', time: '2026-04-06T14:20:00' },
    { user: '최운영자', action: '플러그인 설치: "SEO 최적화 도구"', time: '2026-04-06T11:10:00' }
  ];

  const [timeRange, setTimeRange] = React.useState('1W');

  return (
    <DashboardLayout>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>대시보드</h1>
        <p style={{ fontSize: '14px', color: '#6b7280' }}>블로그 성능 및 수익을 한눈에 확인하세요</p>
      </div>

      <UserStats stats={userStats} />

      <RevenueChart data={revenueData[timeRange]} timeRange={timeRange} />

      <div style={{ display: 'flex', gap: '16px', marginTop: '24px' }}>
        <div style={{ flex: 1 }}>
          <RecentActivity activities={recentActivities} />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;