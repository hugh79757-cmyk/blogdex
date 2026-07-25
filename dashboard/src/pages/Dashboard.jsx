import React from 'react';
import RevenueChart from '../components/RevenueChart';
import UserStats from '../components/UserStats';
import RecentActivity from '../components/RecentActivity';
import DashboardLayout from '../components/DashboardLayout';
import { useDashboardData } from '../hooks/useDashboardData';

const DAY_OPTIONS = [
  { label: '7일',  value: 7 },
  { label: '30일', value: 30 },
  { label: '90일', value: 90 },
];

/**
 * 대시보드 메인 페이지.
 * useDashboardData 훅으로 실제 API 데이터를 불러와서
 * UserStats, RevenueChart, RecentActivity에 전달합니다.
 */
const Dashboard = () => {
  const [days, setDays] = React.useState(30);
  const { data, loading, error } = useDashboardData(days);

  // ── RevenueChart용 시계열 데이터 ──
  // daily_revenue 배열을 { date, revenue, pv } 형태로 변환
  const chartData = React.useMemo(() => {
    if (!data?.revSummary?.daily_revenue) return [];
    return data.revSummary.daily_revenue.map((d) => ({
      date: d.date,
      revenue: d.rev ?? 0,
      pv: d.pv ?? 0,
    }));
  }, [data]);

  // ── UserStats용 요약 데이터 ──
  const statsData = React.useMemo(() => {
    if (!data?.summary) return null;
    const s = data.summary;
    const ctr = s.gsc_impressions > 0
      ? (s.gsc_clicks / s.gsc_impressions * 100).toFixed(2) + '%'
      : '0%';
    return {
      totalClicks:     s.gsc_clicks ?? 0,
      totalImpressions: s.gsc_impressions ?? 0,
      avgCtr:          ctr,
      totalBlogs:      s.blogs ?? 0,
      totalPosts:      s.posts ?? 0,
      coupangRevenue:  s.coupang_revenue ?? 0,
      coupangOrders:   s.coupang_orders ?? 0,
    };
  }, [data]);

  // ── RecentActivity (API에 해당 엔드포인트가 없으므로 고정 메시지) ──
  // TODO: 실제 활동 로그 API가 추가되면 교체
  const recentActivities = React.useMemo(() => {
    if (!data?.revSummary) return [];
    const r = data.revSummary;
    return [
      {
        user: '시스템',
        action: `오늘 수익: $${r.today_revenue?.toFixed(2) ?? '0.00'} | 7일 평균: $${r.avg7_revenue?.toFixed(2) ?? '0.00'}`,
        time: new Date().toISOString(),
      },
      {
        user: '시스템',
        action: `오늘 페이지뷰: ${(r.today_pv ?? 0).toLocaleString()}회`,
        time: new Date().toISOString(),
      },
    ];
  }, [data]);

  // ── 로딩 상태 ──
  if (loading) {
    return (
      <DashboardLayout>
        <div style={{
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          minHeight: '400px', fontSize: '18px', color: '#6b7280'
        }}>
          데이터 로딩 중...
        </div>
      </DashboardLayout>
    );
  }

  // ── 에러 상태 ──
  if (error) {
    return (
      <DashboardLayout>
        <div style={{
          display: 'flex', flexDirection: 'column', justifyContent: 'center',
          alignItems: 'center', minHeight: '400px'
        }}>
          <p style={{ fontSize: '18px', color: '#ef4444', marginBottom: '8px' }}>
            데이터를 불러올 수 없습니다.
          </p>
          <p style={{ fontSize: '14px', color: '#6b7280' }}>
            API 연결을 확인하세요. ({error.message})
          </p>
        </div>
      </DashboardLayout>
    );
  }

  // ── 정상 렌더링 ──
  return (
    <DashboardLayout>
      <div style={{ marginBottom: '24px' }}>
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginBottom: '4px'
        }}>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            대시보드
          </h1>

          {/* ── 기간 선택 ── */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {DAY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setDays(opt.value)}
                style={{
                  padding: '6px 14px',
                  fontSize: '13px',
                  fontWeight: days === opt.value ? 600 : 400,
                  border: '1px solid',
                  borderColor: days === opt.value ? '#3b82f6' : '#e5e7eb',
                  borderRadius: '8px',
                  background: days === opt.value ? '#eff6ff' : '#fff',
                  color: days === opt.value ? '#3b82f6' : '#6b7280',
                  cursor: 'pointer',
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <p style={{ fontSize: '14px', color: '#6b7280', margin: '4px 0 0 0' }}>
          블로그 성능 및 수익을 한눈에 확인하세요
        </p>
      </div>

      {statsData && <UserStats stats={statsData} />}

      <RevenueChart data={chartData} timeRange={`${days}일`} />

      <div style={{ display: 'flex', gap: '16px', marginTop: '24px' }}>
        <div style={{ flex: 1 }}>
          <RecentActivity activities={recentActivities} />
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
