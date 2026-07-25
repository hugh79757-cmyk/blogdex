import React from 'react';

/**
 * 정렬 가능한 데이터 테이블.
 *
 * Props:
 *   columns: [{ key, label, render?, align?, style? }]
 *   data: array of objects
 *   sortable: boolean (default true)
 *   onRowClick: (row) => void
 *   emptyMessage: string (default "데이터 없음")
 *   loading: boolean
 */
function useSortable(data, defaultKey = null, defaultAsc = true) {
  const [sortKey, setSortKey] = React.useState(defaultKey);
  const [asc, setAsc] = React.useState(defaultAsc);

  const sorted = React.useMemo(() => {
    if (!sortKey || !data) return data || [];
    return [...data].sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (va == null) va = '';
      if (vb == null) vb = '';
      const na = typeof va === 'string' ? parseFloat(va.replace(/[^0-9.-]/g, '')) : va;
      const nb = typeof vb === 'string' ? parseFloat(vb.replace(/[^0-9.-]/g, '')) : vb;
      if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
      return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
  }, [data, sortKey, asc]);

  const toggle = (key) => {
    if (sortKey === key) setAsc(!asc);
    else { setSortKey(key); setAsc(false); }
  };

  const indicator = (key) => sortKey === key ? (asc ? ' ▲' : ' ▼') : ' ⇅';

  return { sorted, toggle, indicator };
}

const thStyle = {
  padding: '10px 12px', textAlign: 'left', fontWeight: 600,
  color: '#374151', borderBottom: '2px solid #e5e7eb', fontSize: 13,
};

const tdStyle = { padding: '8px 12px' };

const DataTable = ({
  columns,
  data = [],
  sortable = true,
  onRowClick,
  emptyMessage = '데이터 없음',
  loading = false,
}) => {
  const { sorted, toggle, indicator } = useSortable(data, columns[0]?.key, false);

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
        로딩 중...
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#9ca3af' }}>
        {emptyMessage}
      </div>
    );
  }

  const displayData = sortable ? sorted : data;

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={sortable ? () => toggle(col.key) : undefined}
                style={{
                  ...thStyle,
                  textAlign: col.align || 'left',
                  cursor: sortable ? 'pointer' : 'default',
                  userSelect: 'none',
                  ...(col.style || {}),
                }}
              >
                {col.label}
                {sortable ? indicator(col.key) : ''}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {displayData.map((row, i) => (
            <tr
              key={row.id ?? i}
              onClick={() => onRowClick?.(row)}
              style={{
                background: i % 2 ? '#f9fafb' : '#fff',
                cursor: onRowClick ? 'pointer' : 'default',
              }}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    ...tdStyle,
                    textAlign: col.align || 'left',
                    ...(col.style || {}),
                  }}
                >
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
export { useSortable };
