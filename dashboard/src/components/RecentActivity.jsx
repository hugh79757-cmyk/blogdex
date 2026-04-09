import React from 'react';

const RecentActivity = ({ activities }) => {
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('ko-KR', {
      month: '2-digit', day: '2-digit', 
      hour: '2-digit', minute: '2-digit', 
      hour12: false
    }).replace(/(\d+)\. (\d+)\. (\d+):(\d+)/, '$1-$2 $3:$4');
  };

  return (
    <div style={{ background: '#fff', borderRadius: '12px', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', border: '1px solid #e5e7eb' }}>
      <h3 style={{ margin: '0 0 16px', fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>최근 활동</h3>
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {activities.map((activity, index) => (
          <div key={index} style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderBottom: index < activities.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)', marginBottom: '2px' }}>
                {activity.user}
              </div>
              <div style={{ fontSize: '12px', color: '#6b7280' }}>
                {activity.action}
              </div>
            </div>
            <div style={{ fontSize: '12px', color: '#9ca3af', whiteSpace: 'nowrap', marginLeft: '12px' }}>
              {formatTime(activity.time)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecentActivity;