import { useState, useEffect } from 'react'
import api from './api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const tabs = ['대시보드', '사이트별', '키워드', '리라이트 큐', '타이틀 관리', '타이틀 수집', '키워드 체크', '수익 기회']

const HIGH_PATTERNS = ['추천','비교','가격','후기','리뷰','순위','신청','방법','절차','가입','등록','발급','할인','쿠폰','무료','혜택','보험','대출','적금','투자','보조금','지원금','환급','세금','vs','차이','장단점','구매']
const LOW_PATTERNS = ['뜻','의미','영어로','누구','나이','키','몸무게','생일','mbti','학력']

function classifyKw(q) {
  const ql = q.toLowerCase()
  for (const p of HIGH_PATTERNS) { if (ql.includes(p)) return 'high' }
  for (const p of LOW_PATTERNS) { if (ql.includes(p)) return 'low' }
  return 'medium'
}

function SortHeader({ label, field, sortField, sortDir, onSort, align }) {
  const active = sortField === field
  const arrow = active ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''
  return (
    <th style={{...thStyle, textAlign: align||'left', cursor:'pointer', userSelect:'none'}}
        onClick={() => onSort(field)}>
      {label}{arrow}
    </th>
  )
}

function useSort(defaultField, defaultDir='desc') {
  const [sortField, setSortField] = useState(defaultField)
  const [sortDir, setSortDir] = useState(defaultDir)
  const onSort = (field) => {
    if (sortField === field) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }
  const sortData = (data) => {
    return [...data].sort((a, b) => {
      let va = a[sortField], vb = b[sortField]
      if (typeof va === 'string') va = va.toLowerCase()
      if (typeof vb === 'string') vb = vb.toLowerCase()
      if (va < vb) return sortDir === 'asc' ? -1 : 1
      if (va > vb) return sortDir === 'asc' ? 1 : -1
      return 0
    })
  }
  return { sortField, sortDir, onSort, sortData }
}

function StatCard({ label, value, color }) {
  return (
    <div style={{padding:16,background:'#fff',borderRadius:12,border:'1px solid #e5e7eb',boxShadow:'0 1px 3px rgba(0,0,0,0.05)'}}>
      <div style={{fontSize:13,color:'#6b7280',marginBottom:4}}>{label}</div>
      <div style={{fontSize:28,fontWeight:700,color:color||'#111'}}>{value}</div>
    </div>
  )
}

function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [daily, setDaily] = useState([])
  const [days, setDays] = useState(30)

  useEffect(() => {
    api.get('/dashboard/summary?days=' + days).then(r => setSummary(r.data))
    api.get('/gsc/daily?days=' + days).then(r => setDaily(r.data))
  }, [days])

  if (!summary) return (<p style={{padding:20}}>로딩 중...</p>)

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        {[7,30,60,90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{...pillStyle, background: days===d ? '#3b82f6' : '#e5e7eb', color: days===d ? '#fff' : '#333'}}>
            {d}일
          </button>
        ))}
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12, marginBottom:24}}>
        <StatCard label="블로그" value={summary.blogs} />
        <StatCard label="포스트" value={summary.posts?.toLocaleString()} />
        <StatCard label={days+'일 클릭'} value={summary.gsc_clicks?.toLocaleString()} color="#10b981" />
        <StatCard label={days+'일 노출'} value={summary.gsc_impressions?.toLocaleString()} color="#3b82f6" />
      </div>
      <h3 style={{marginBottom:12}}>일별 클릭·노출 추이</h3>
      {daily.length > 0 ? (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={daily}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{fontSize:11}} tickFormatter={d => d.slice(5)} />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Line yAxisId="right" type="monotone" dataKey="impressions" stroke="#3b82f6" name="노출" dot={false} />
            <Line yAxisId="left" type="monotone" dataKey="clicks" stroke="#10b981" name="클릭" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      ) : (<p style={{color:'#999'}}>데이터 없음</p>)}
    </div>
  )
}

function SitesView() {
  const [sites, setSites] = useState([])
  const [days, setDays] = useState(30)
  const { sortField, sortDir, onSort, sortData } = useSort('impressions')

  useEffect(() => {
    api.get('/gsc/sites?days=' + days).then(r => setSites(r.data))
  }, [days])

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        {[7,30,60,90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{...pillStyle, background: days===d ? '#3b82f6' : '#e5e7eb', color: days===d ? '#fff' : '#333'}}>
            {d}일
          </button>
        ))}
      </div>
      {sites.length > 0 ? (
        <div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sites.filter(s => s.impressions > 0)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="site" tick={{fontSize:10}} angle={-30} textAnchor="end" height={80} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="impressions" fill="#3b82f6" name="노출" />
              <Bar dataKey="clicks" fill="#10b981" name="클릭" />
            </BarChart>
          </ResponsiveContainer>
          <table style={tableStyle}>
            <thead>
              <tr style={{background:'#f8fafc'}}>
                <SortHeader label="사이트" field="site" sortField={sortField} sortDir={sortDir} onSort={onSort} />
                <SortHeader label="클릭" field="clicks" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
                <SortHeader label="노출" field="impressions" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
                <SortHeader label="CTR" field="ctr" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              </tr>
            </thead>
            <tbody>
              {sortData(sites).map((s,i) => (
                <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                  <td style={tdStyle}>{s.site}</td>
                  <td style={{...tdStyle,textAlign:'right',color:'#10b981',fontWeight:600}}>{s.clicks}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{s.impressions?.toLocaleString()}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{s.ctr}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (<p style={{color:'#999'}}>데이터 없음</p>)}
    </div>
  )
}

function KeywordsView() {
  const [keywords, setKeywords] = useState([])
  const [days, setDays] = useState(30)
  const [filter, setFilter] = useState('')
  const [limit, setLimit] = useState(200)
  const { sortField, sortDir, onSort, sortData } = useSort('impressions')

  useEffect(() => {
    api.get('/gsc/keywords?days=' + days + '&limit=200').then(r => {
      const data = r.data.map(k => ({...k, value: classifyKw(k.query)}))
      if (filter) {
        setKeywords(data.filter(k => k.value === filter))
      } else {
        setKeywords(data)
      }
    })
  }, [days, filter])

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:12}}>
        {[7,30,60,90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{...pillStyle, background: days===d ? '#3b82f6' : '#e5e7eb', color: days===d ? '#fff' : '#333'}}>
            {d}일
          </button>
        ))}
        <span style={{width:16}} />
        {[{l:'전체',v:''},{l:'HIGH',v:'high'},{l:'MED',v:'medium'},{l:'LOW',v:'low'}].map(f => (
          <button key={f.v} onClick={() => setFilter(f.v)}
            style={{...pillStyle, background: filter===f.v ? '#3b82f6' : '#e5e7eb', color: filter===f.v ? '#fff' : '#333'}}>
            {f.l}
          </button>
        ))}
      </div>
      <div style={{display:'flex',gap:4,marginBottom:16,alignItems:'center'}}>
        <span style={{fontSize:12,color:'#6b7280',marginRight:4}}>표시:</span>
        {[50,100,200,500].map(n => (
          <button key={n} onClick={() => setLimit(n)}
            style={{padding:'4px 10px',borderRadius:6,border:'none',fontSize:12,cursor:'pointer',
              background: limit===n ? '#3b82f6' : '#e5e7eb', color: limit===n ? '#fff' : '#333'}}>{n}개</button>
        ))}
      </div>
      <div style={{marginBottom:8,color:'#666',fontSize:13}}>
        총 {keywords.length}개 | HIGH {keywords.filter(k=>k.value==='high').length} | MED {keywords.filter(k=>k.value==='medium').length} | LOW {keywords.filter(k=>k.value==='low').length}
      </div>
      <table style={tableStyle}>
        <thead>
          <tr style={{background:'#f8fafc'}}>
            <SortHeader label="키워드" field="query" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="블로그" field="blog_name" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="가치" field="value" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="노출" field="impressions" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="클릭" field="clicks" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="CTR" field="ctr" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            <SortHeader label="순위" field="avg_position" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
          </tr>
        </thead>
        <tbody>
          {sortData(keywords).slice(0,100).map((k,i) => (
            <tr key={i} style={{borderBottom:'1px solid #eee'}}>
              <td style={tdStyle}>{k.query}</td>
              <td style={{...tdStyle,fontSize:11,color:'#6b7280'}}>{k.blog_name || k.site || '-'}</td>
              <td style={tdStyle}>
                <span style={{padding:'2px 8px',borderRadius:10,fontSize:11,fontWeight:600,
                  background: k.value==='high'?'#fee2e2':k.value==='medium'?'#fef3c7':'#f3f4f6',
                  color: k.value==='high'?'#dc2626':k.value==='medium'?'#d97706':'#6b7280'}}>
                  {k.value.toUpperCase()}
                </span>
              </td>
              <td style={{...tdStyle,textAlign:'right'}}>{k.impressions?.toLocaleString()}</td>
              <td style={{...tdStyle,textAlign:'right',color:'#10b981',fontWeight:600}}>{k.clicks}</td>
              <td style={{...tdStyle,textAlign:'right'}}>{k.ctr}%</td>
              <td style={{...tdStyle,textAlign:'right'}}>{k.avg_position}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RewriteQueue() {
  const [keywords, setKeywords] = useState([])
  const [days, setDays] = useState(30)
  const { sortField, sortDir, onSort, sortData } = useSort('priority')

  useEffect(() => {
    api.get('/gsc/keywords?days=' + days + '&limit=500').then(r => {
      const data = r.data.map(k => ({...k, value: classifyKw(k.query)}))
      const queue = []
      for (const k of data) {
        const pos = k.avg_position
        const ctr = k.ctr
        const imp = k.impressions
        let action = null
        let priority = 0
        if (pos <= 10 && ctr < 5 && imp >= 5) {
          action = '타이틀/메타 개선'
          priority = imp * (10 - ctr)
        } else if (pos > 10 && pos <= 20 && imp >= 5) {
          action = '콘텐츠 보강 → 1페이지'
          priority = imp * 2
        } else if (imp >= 10 && k.clicks === 0) {
          action = '타이틀 전면 교체'
          priority = imp * 5
        }
        if (action) queue.push({...k, action, priority})
      }
      queue.sort((a,b) => b.priority - a.priority)
      setKeywords(queue)
    })
  }, [days])

  const titleFixes = keywords.filter(k => k.action === '타이틀/메타 개선')
  const contentFixes = keywords.filter(k => k.action === '콘텐츠 보강 → 1페이지')
  const zeroClicks = keywords.filter(k => k.action === '타이틀 전면 교체')

  return (
    <div>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        {[7,30,60,90].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{...pillStyle, background: days===d ? '#3b82f6' : '#e5e7eb', color: days===d ? '#fff' : '#333'}}>
            {d}일
          </button>
        ))}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12,marginBottom:20}}>
        <StatCard label="타이틀/메타 개선" value={titleFixes.length} color="#ef4444" />
        <StatCard label="콘텐츠 보강" value={contentFixes.length} color="#f59e0b" />
        <StatCard label="타이틀 전면 교체" value={zeroClicks.length} color="#8b5cf6" />
      </div>
      {keywords.length > 0 && (
        <table style={tableStyle}>
          <thead>
            <tr style={{background:'#f8fafc'}}>
              <SortHeader label="키워드" field="query" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="액션" field="action" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="노출" field="impressions" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="클릭" field="clicks" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="CTR" field="ctr" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="순위" field="avg_position" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            </tr>
          </thead>
          <tbody>
            {sortData(keywords).slice(0,50).map((k,i) => {
              const actionColor = k.action.includes('메타') ? '#ef4444' : k.action.includes('보강') ? '#f59e0b' : '#8b5cf6'
              return (
                <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                  <td style={tdStyle}>{k.query}</td>
                  <td style={tdStyle}>
                    <span style={{padding:'2px 8px',borderRadius:10,fontSize:11,fontWeight:600,background:actionColor+'20',color:actionColor}}>
                      {k.action}
                    </span>
                  </td>
                  <td style={{...tdStyle,textAlign:'right'}}>{k.impressions?.toLocaleString()}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{k.clicks}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{k.ctr}%</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{k.avg_position}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}

function TitleManager() {
  const [tab, setTab] = useState('browse')
  const [input, setInput] = useState('')
  const [titles, setTitles] = useState([])
  const [bulk, setBulk] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [csvLog, setCsvLog] = useState([])
  const [analyzing, setAnalyzing] = useState(false)
  const [recommendations, setRecommendations] = useState([])
  const [detail, setDetail] = useState(null)

  // browse state
  const [filter, setFilter] = useState('all')
  const [browseData, setBrowseData] = useState([])
  const [browseTotal, setBrowseTotal] = useState(0)
  const [browsePage, setBrowsePage] = useState(1)
  const [selected, setSelected] = useState(new Set())
  const [sources, setSources] = useState([])
  const [sourceFilter, setSourceFilter] = useState('')
  const [selectAll, setSelectAll] = useState(false)

  // search state
  const [search, setSearch] = useState('')
  const [results, setResults] = useState([])

  const loadBrowse = async (status, page) => {
    try {
      const res = await api.get('/titles/filter?status=' + status + '&page=' + page + '&limit=30' + (sourceFilter ? '&source=' + encodeURIComponent(sourceFilter) : ''))
      setBrowseData(res.data.data || [])
      setBrowseTotal(res.data.total || 0)
      setSelected(new Set())
      setSelectAll(false)
    } catch(e) { console.error(e) }
  }

  useEffect(() => { if (tab === 'browse') loadBrowse(filter, browsePage) }, [tab, filter, browsePage, sourceFilter])
  useEffect(() => { api.get('/titles/sources').then(r => setSources(r.data || [])).catch(() => {}) }, [])

  const toggleSelect = (id) => {
    const s = new Set(selected)
    if (s.has(id)) s.delete(id); else s.add(id)
    setSelected(s)
  }
  const toggleAll = () => {
    if (selectAll) { setSelected(new Set()); setSelectAll(false) }
    else { setSelected(new Set(browseData.map(t => t.id))); setSelectAll(true) }
  }
  const bulkStatus = async (status) => {
    if (selected.size === 0) return
    try {
      await api.put('/titles/bulk-status', { ids: Array.from(selected), status })
      loadBrowse(filter, browsePage)
    } catch(e) { alert('실패: ' + e.message) }
  }

  const [analyzeResults, setAnalyzeResults] = useState([])
  const [analyzeLoading, setAnalyzeLoading] = useState(false)

  const analyzeSelected = async () => {
    if (selected.size === 0) return
    setAnalyzeLoading(true)
    const selectedTitles = browseData.filter(t => selected.has(t.id)).map(t => t.title)
    try {
      const allRecs = []
      for (let i = 0; i < selectedTitles.length; i += 20) {
        const batch = selectedTitles.slice(i, i + 20)
        const res = await api.post('/titles/recommend', { titles: batch })
        allRecs.push(...res.data)
      }
      setAnalyzeResults(allRecs)
    } catch(e) { alert('분석 실패: ' + e.message) }
    setAnalyzeLoading(false)
  }

  const addTitle = () => { if (input.trim()) { setTitles([...titles, input.trim()]); setInput('') } }
  const removeTitle = (i) => setTitles(titles.filter((_, idx) => idx !== i))
  const saveTitles = async () => {
    if (titles.length === 0) return
    try {
      await api.post('/titles', { titles: titles.map(t => ({ title: t })) })
      setCsvLog(prev => [...prev, titles.length + '건 저장 완료'])
      setTitles([])
    } catch(e) { alert('저장 실패') }
  }
  const addBulk = () => {
    const lines = bulk.split('\n').map(l => l.trim()).filter(l => l.length > 0)
    if (lines.length > 0) { setTitles([...titles, ...lines]); setBulk(''); setCsvLog(prev => [...prev, lines.length + '건 추가']) }
  }
  const handleCsvFile = async (file) => {
    const text = await file.text()
    const lines = text.split('\n')
    const skip = ['카테고리','태그 목록','전체보기','category','title,']
    const parsed = []
    for (const line of lines) {
      const tr = line.trim()
      if (!tr) continue
      if (skip.some(p => tr.toLowerCase().includes(p.toLowerCase()))) continue
      const title = (tr.split(',')[0] || '').replace(/^"|"$/g, '').trim()
      if (title.length >= 2) parsed.push(title)
    }
    setCsvLog(prev => [...prev, file.name + ': ' + parsed.length + '건 파싱'])
    if (parsed.length === 0) return
    for (let i = 0; i < parsed.length; i += 500) {
      const batch = parsed.slice(i, i + 500)
      try {
        await api.post('/titles', { titles: batch.map(t => ({ title: t })) })
        setCsvLog(prev => [...prev, (i + batch.length) + '/' + parsed.length + ' 업로드'])
      } catch(e) { setCsvLog(prev => [...prev, 'ERROR: ' + e.message]) }
    }
    setCsvLog(prev => [...prev, '블로그 추천 분석 시작...'])
    setAnalyzing(true)
    try {
      const allRecs = []
      for (let i = 0; i < parsed.length; i += 20) {
        const res = await api.post('/titles/recommend', { titles: parsed.slice(i, i + 20) })
        allRecs.push(...res.data)
      }
      setRecommendations(allRecs)
      setCsvLog(prev => [...prev, allRecs.length + '건 분석 완료'])
    } catch(e) { setCsvLog(prev => [...prev, '분석 실패: ' + e.message]) }
    setAnalyzing(false)
  }
  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.csv')).forEach(handleCsvFile) }
  const handleFileInput = (e) => { Array.from(e.target.files).filter(f => f.name.endsWith('.csv')).forEach(handleCsvFile) }
  const searchTitles = async () => {
    if (!search.trim()) return
    try { const res = await api.get('/titles/search?q=' + encodeURIComponent(search)); setResults(res.data) } catch(e) { alert('검색 실패') }
  }
  const showDetail = async (id) => {
    // 먼저 타이틀 텍스트 가져오기
    const titleItem = browseData.find(t => t.id === id) || results.find(t => t.id === id)
    const titleText = titleItem?.title || ''
    
    // 로컬 API (Kiwi) 시도
    try {
      const localRes = await fetch('http://localhost:5001/api/title-detail', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ title: titleText })
      })
      if (localRes.ok) {
        const localData = await localRes.json()
        setDetail({
          title: titleItem || { title: titleText },
          keywords: localData.keywords,
          related_posts: localData.related_posts,
          gsc_keywords: localData.gsc_keywords,
          summary: localData.summary
        })
        return
      }
    } catch(e) {}
    
    // 로컬 실패시 Workers API
    try {
      const res = await api.get('/titles/detail/' + id)
      setDetail(res.data)
    } catch(e) { alert('상세 조회 실패') }
  }

  const statusColor = { saved: '#10b981', rejected: '#ef4444', pending: '#f59e0b', used: '#3b82f6' }
  const statusLabel = { saved: '저장됨', rejected: '제외', pending: '대기', used: '사용됨' }
  const recColor = (s) => s > 50 ? '#10b981' : s > 10 ? '#f59e0b' : '#6b7280'

  return (
    <div>
      {/* 서브탭 */}
      <div style={{display:'flex',gap:4,marginBottom:16}}>
        {[{k:'browse',l:'타이틀 목록'},{k:'add',l:'등록/CSV'},{k:'search',l:'검색'}].map(t => (
          <button key={t.k} onClick={() => setTab(t.k)}
            style={{padding:'6px 14px',borderRadius:6,border:'none',fontSize:13,cursor:'pointer',
              background: tab===t.k ? '#3b82f6' : '#f3f4f6', color: tab===t.k ? '#fff' : '#374151'}}>{t.l}</button>
        ))}
      </div>

      {/* === 타이틀 목록 탭 === */}
      {tab === 'browse' && (
        <div>
          <div style={{display:'flex',gap:4,marginBottom:12,flexWrap:'wrap',alignItems:'center'}}>
            {['all','pending','saved','rejected','used'].map(s => (
              <button key={s} onClick={() => { setFilter(s); setBrowsePage(1) }}
                style={{padding:'5px 12px',borderRadius:6,border:'none',fontSize:12,cursor:'pointer',
                  background: filter===s ? '#3b82f6' : '#f3f4f6', color: filter===s ? '#fff' : '#374151'}}>
                {s === 'all' ? '전체' : (statusLabel[s] || s)}
              </button>
            ))}
            <span style={{marginLeft:'auto',fontSize:12,color:'#6b7280'}}>총 {browseTotal}건</span>
          </div>

          {sources.length > 0 && (
            <div style={{display:'flex',gap:4,marginBottom:12,flexWrap:'wrap',alignItems:'center'}}>
              <span style={{fontSize:12,color:'#6b7280',marginRight:4}}>출처:</span>
              <button onClick={() => { setSourceFilter(''); setBrowsePage(1) }}
                style={{padding:'4px 10px',borderRadius:6,border:'none',fontSize:11,cursor:'pointer',
                  background: !sourceFilter ? '#7c3aed' : '#f3f4f6', color: !sourceFilter ? '#fff' : '#374151'}}>전체</button>
              {sources.filter(s => s.source).map(s => (
                <button key={s.source} onClick={() => { setSourceFilter(s.source); setBrowsePage(1) }}
                  style={{padding:'4px 10px',borderRadius:6,border:'none',fontSize:11,cursor:'pointer',
                    background: sourceFilter === s.source ? '#7c3aed' : '#f3f4f6', color: sourceFilter === s.source ? '#fff' : '#374151'}}>
                  {s.source} ({s.count})
                </button>
              ))}
            </div>
          )}

          {selected.size > 0 && (
            <div style={{display:'flex',gap:6,marginBottom:12,padding:8,background:'#f0f9ff',borderRadius:8}}>
              <span style={{fontSize:12,color:'#374151',lineHeight:'28px'}}>{selected.size}건 선택</span>
              <button onClick={() => bulkStatus('saved')} style={{padding:'4px 10px',borderRadius:4,border:'none',background:'#10b981',color:'#fff',fontSize:12,cursor:'pointer'}}>저장</button>
              <button onClick={() => bulkStatus('rejected')} style={{padding:'4px 10px',borderRadius:4,border:'none',background:'#ef4444',color:'#fff',fontSize:12,cursor:'pointer'}}>제외</button>
              <button onClick={() => bulkStatus('used')} style={{padding:'4px 10px',borderRadius:4,border:'none',background:'#3b82f6',color:'#fff',fontSize:12,cursor:'pointer'}}>사용됨</button>
              <button onClick={() => bulkStatus('pending')} style={{padding:'4px 10px',borderRadius:4,border:'none',background:'#f59e0b',color:'#fff',fontSize:12,cursor:'pointer'}}>대기로</button>
              <button onClick={analyzeSelected} style={{padding:'4px 10px',borderRadius:4,border:'none',background:'#7c3aed',color:'#fff',fontSize:12,cursor:'pointer',marginLeft:'auto'}}>블로그 추천 분석</button>
            </div>
          )}

          {analyzeLoading && <p style={{color:'#7c3aed',marginBottom:12}}>블로그 추천 분석 중...</p>}
          {analyzeResults.length > 0 && (
            <div style={{marginBottom:16,background:'#faf5ff',border:'1px solid #e9d5ff',borderRadius:12,padding:16}}>
              <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
                <h4 style={{margin:0,color:'#7c3aed'}}>블로그 추천 결과 ({analyzeResults.length}건)</h4>
                <button onClick={() => setAnalyzeResults([])} style={{background:'none',border:'none',color:'#9ca3af',cursor:'pointer'}}>닫기</button>
              </div>
              <table style={tableStyle}>
                <thead><tr style={{background:'#f8fafc'}}>
                  <th style={thStyle}>타이틀</th>
                  <th style={{...thStyle,textAlign:'center'}}>추천 블로그</th>
                  <th style={{...thStyle,textAlign:'right'}}>점수</th>
                  <th style={{...thStyle,textAlign:'right'}}>노출</th>
                  <th style={{...thStyle,textAlign:'center'}}>중복</th>
                  <th style={thStyle}>근거</th>
                </tr></thead>
                <tbody>{analyzeResults.map((r, i) => (
                  <tr key={i} style={{borderBottom:'1px solid #f3f4f6'}}>
                    <td style={{...tdStyle,maxWidth:220,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.title}</td>
                    <td style={{...tdStyle,textAlign:'center',fontWeight:600,color: r.score > 50 ? '#10b981' : r.score > 10 ? '#f59e0b' : '#6b7280'}}>{r.recommendation || '-'}</td>
                    <td style={{...tdStyle,textAlign:'right'}}>{r.score || 0}</td>
                    <td style={{...tdStyle,textAlign:'right'}}>{r.impressions || 0}</td>
                    <td style={{...tdStyle,textAlign:'center'}}>{r.dup_count || 0}</td>
                    <td style={{...tdStyle,fontSize:11,color:'#6b7280'}}>{(r.reasons || []).join(', ') || '-'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}

          <table style={tableStyle}>
            <thead><tr style={{background:'#f8fafc'}}>
              <th style={{...thStyle,width:30}}><input type="checkbox" checked={selectAll} onChange={toggleAll}/></th>
              <th style={thStyle}>타이틀</th>
              <th style={{...thStyle,textAlign:'center',width:90}}>발행 블로그</th>
              <th style={{...thStyle,width:100}}>출처</th>
              <th style={{...thStyle,textAlign:'center',width:60}}>상태</th>
            </tr></thead>
            <tbody>{browseData.map(t => (
              <tr key={t.id} style={{borderBottom:'1px solid #f3f4f6',cursor:'pointer'}} onClick={() => showDetail(t.id)}>
                <td style={tdStyle} onClick={e => e.stopPropagation()}><input type="checkbox" checked={selected.has(t.id)} onChange={() => toggleSelect(t.id)}/></td>
                <td style={{...tdStyle,maxWidth:350,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{t.title}</td>
                <td style={{...tdStyle,textAlign:'center',fontSize:11}}>
                  {t.published_in && t.published_in.length > 0
                    ? t.published_in.map((p,j) => <div key={j} style={{color:'#10b981'}}>{p.blog_name}</div>)
                    : <span style={{color:'#d1d5db'}}>-</span>}
                </td>
                <td style={{...tdStyle,fontSize:11,color:'#6b7280'}}>{t.source || '-'}</td>
                <td style={{...tdStyle,textAlign:'center'}}>
                  <span style={{fontSize:11,padding:'2px 8px',borderRadius:10,background:(statusColor[t.status]||'#e5e7eb')+'20',color:statusColor[t.status]||'#6b7280'}}>
                    {statusLabel[t.status] || t.status || 'pending'}
                  </span>
                </td>
              </tr>
            ))}</tbody>
          </table>

          {browseTotal > 30 && (
            <div style={{display:'flex',justifyContent:'center',gap:8,marginTop:12}}>
              <button disabled={browsePage<=1} onClick={() => setBrowsePage(browsePage-1)} style={{...btnStyle,opacity:browsePage<=1?0.3:1}}>이전</button>
              <span style={{fontSize:12,lineHeight:'32px',color:'#6b7280'}}>{browsePage} / {Math.ceil(browseTotal/30)}</span>
              <button disabled={browsePage>=Math.ceil(browseTotal/30)} onClick={() => setBrowsePage(browsePage+1)} style={{...btnStyle,opacity:browsePage>=Math.ceil(browseTotal/30)?0.3:1}}>다음</button>
            </div>
          )}
        </div>
      )}

      {/* === 등록/CSV 탭 === */}
      {tab === 'add' && (
        <div>
      <div style={{background:'#f0fdf4',border:'1px solid #bbf7d0',borderRadius:12,padding:16,marginBottom:16}}>
        <h4 style={{margin:'0 0 8px',fontSize:14,color:'#166534'}}>경쟁사 타이틀 수집</h4>
        <p style={{fontSize:12,color:'#374151',margin:'0 0 8px'}}>터미널에서 실행 후 생성된 CSV를 아래에 드래그하세요</p>
        <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
          <div style={{background:'#fff',border:'1px solid #d1d5db',borderRadius:8,padding:'8px 12px',fontSize:12}}>
            <div style={{fontWeight:600,marginBottom:4}}>일반 사이트 (티스토리/WP)</div>
            <code style={{fontSize:11,color:'#6b7280'}}>python crawl_titles.py</code>
          </div>
          <div style={{background:'#fff',border:'1px solid #d1d5db',borderRadius:8,padding:'8px 12px',fontSize:12}}>
            <div style={{fontWeight:600,marginBottom:4}}>네이버 블로그</div>
            <code style={{fontSize:11,color:'#6b7280'}}>python crawl_naver.py</code>
          </div>
        </div>
        <p style={{fontSize:11,color:'#6b7280',margin:'8px 0 0'}}>CSV 저장 위치: cli/collected_titles/</p>
      </div>


      <div onDrop={handleDrop} onDragOver={e=>{e.preventDefault();setDragOver(true)}} onDragLeave={()=>setDragOver(false)}
            style={{border:dragOver?'2px solid #3b82f6':'2px dashed #d1d5db',borderRadius:12,padding:32,textAlign:'center',marginBottom:16,background:dragOver?'#eff6ff':'#fafafa',cursor:'pointer'}}
            onClick={()=>document.getElementById('csvInput').click()}>
            <div style={{fontSize:14,color:'#6b7280'}}>CSV 파일을 여기에 드래그하거나 클릭</div>
            <div style={{fontSize:12,color:'#9ca3af',marginTop:4}}>업로드 후 자동 블로그 추천 분석</div>
            <input id="csvInput" type="file" accept=".csv" multiple style={{display:'none'}} onChange={handleFileInput}/>
          </div>

          {csvLog.length > 0 && (
            <div style={{background:'#f8fafc',border:'1px solid #e5e7eb',borderRadius:8,padding:12,marginBottom:16,maxHeight:120,overflowY:'auto'}}>
              {csvLog.map((l,i) => <div key={i} style={{fontSize:12,color:l.includes('ERROR')?'#ef4444':'#374151'}}>{l}</div>)}
            </div>
          )}

          {analyzing && <p style={{color:'#3b82f6',marginBottom:12}}>분석 중...</p>}
          {recommendations.length > 0 && (
            <div style={{marginBottom:24}}>
              <h3 style={{marginBottom:8}}>블로그 추천 결과 ({recommendations.length}건)</h3>
              <table style={tableStyle}>
                <thead><tr style={{background:'#f8fafc'}}>
                  <th style={thStyle}>타이틀</th>
                  <th style={{...thStyle,textAlign:'center'}}>추천 블로그</th>
                  <th style={{...thStyle,textAlign:'right'}}>점수</th>
                  <th style={{...thStyle,textAlign:'right'}}>노출</th>
                  <th style={{...thStyle,textAlign:'center'}}>중복</th>
                  <th style={thStyle}>근거</th>
                </tr></thead>
                <tbody>{recommendations.map((r,i) => (
                  <tr key={i} style={{borderBottom:'1px solid #f3f4f6'}}>
                    <td style={{...tdStyle,maxWidth:220,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.title}</td>
                    <td style={{...tdStyle,textAlign:'center',fontWeight:600,color:recColor(r.score)}}>{r.recommendation||'-'}</td>
                    <td style={{...tdStyle,textAlign:'right'}}>{r.score||0}</td>
                    <td style={{...tdStyle,textAlign:'right'}}>{r.impressions||0}</td>
                    <td style={{...tdStyle,textAlign:'center'}}>{r.dup_count||0}</td>
                    <td style={{...tdStyle,fontSize:11,color:'#6b7280'}}>{(r.reasons||[]).join(', ')||'-'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}

          <div style={{marginBottom:16}}>
            <textarea value={bulk} onChange={e=>setBulk(e.target.value)} placeholder="여러 타이틀을 줄바꿈으로 입력" rows={4} style={{...inputStyle,width:'100%',resize:'vertical'}}/>
            <button onClick={addBulk} style={{...btnStyle,marginTop:4}}>대량 추가</button>
          </div>

          <div style={{display:'flex',gap:8,marginBottom:16}}>
            <input value={input} onChange={e=>setInput(e.target.value)} placeholder="타이틀 입력" onKeyDown={e=>e.key==='Enter'&&addTitle()} style={{...inputStyle,flex:1}}/>
            <button onClick={addTitle} style={btnStyle}>추가</button>
          </div>

          {titles.length > 0 && (
            <div style={{marginBottom:16}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
                <span style={{fontSize:13,color:'#6b7280'}}>대기: {titles.length}건</span>
                <button onClick={saveTitles} style={{...btnStyle,background:'#10b981'}}>전체 저장</button>
              </div>
              {titles.map((t,i) => (
                <div key={i} style={{display:'flex',justifyContent:'space-between',padding:'6px 0',borderBottom:'1px solid #f3f4f6',fontSize:13}}>
                  <span>{t}</span>
                  <button onClick={()=>removeTitle(i)} style={{background:'none',border:'none',color:'#ef4444',cursor:'pointer'}}>x</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* === 검색 탭 === */}
      {tab === 'search' && (
        <div>
          <div style={{display:'flex',gap:8,marginBottom:12}}>
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="키워드 검색" onKeyDown={e=>e.key==='Enter'&&searchTitles()} style={{...inputStyle,flex:1}}/>
            <button onClick={searchTitles} style={btnStyle}>검색</button>
          </div>
          {results.length > 0 && (
            <table style={tableStyle}>
              <thead><tr style={{background:'#f8fafc'}}>
                <th style={thStyle}>타이틀</th>
                <th style={{...thStyle,textAlign:'center'}}>발행 블로그</th>
                <th style={{...thStyle,textAlign:'center'}}>상태</th>
                <th style={{...thStyle,textAlign:'center'}}>상세</th>
              </tr></thead>
              <tbody>{results.map((r,i) => (
                <tr key={i} style={{borderBottom:'1px solid #f3f4f6',cursor:'pointer'}} onClick={()=>showDetail(r.id)}>
                  <td style={tdStyle}>{r.title}</td>
                  <td style={{...tdStyle,textAlign:'center',fontSize:11}}>
                    {r.published_in && r.published_in.length > 0
                      ? r.published_in.map((p,j) => <div key={j} style={{color:'#10b981'}}>{p.blog_name}</div>)
                      : <span style={{color:'#d1d5db'}}>-</span>}
                  </td>
                  <td style={{...tdStyle,textAlign:'center'}}>
                    <span style={{fontSize:11,padding:'2px 8px',borderRadius:10,background:(statusColor[r.status]||'#e5e7eb')+'20',color:statusColor[r.status]||'#6b7280'}}>
                      {statusLabel[r.status]||r.status||'pending'}
                    </span>
                  </td>
                  <td style={{...tdStyle,textAlign:'center',color:'#3b82f6'}}>보기</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}

      {/* 상세 모달 */}
      {detail && (
        <div style={{position:'fixed',top:0,left:0,right:0,bottom:0,background:'rgba(0,0,0,0.5)',display:'flex',alignItems:'center',justifyContent:'center',zIndex:999}} onClick={()=>setDetail(null)}>
          <div style={{background:'#fff',borderRadius:16,padding:24,maxWidth:700,width:'90%',maxHeight:'80vh',overflowY:'auto'}} onClick={e=>e.stopPropagation()}>
            <div style={{display:'flex',justifyContent:'space-between',marginBottom:16}}>
              <h3 style={{margin:0}}>{detail.title?.title||''}</h3>
              {detail.keywords && detail.keywords.length > 0 && (
                <div style={{display:'flex',gap:4,flexWrap:'wrap',marginTop:8}}>
                  {detail.keywords.map((kw,i) => (
                    <span key={i} style={{padding:'2px 8px',borderRadius:10,fontSize:11,background:'#eff6ff',color:'#2563eb'}}>{kw}</span>
                  ))}
                </div>
              )}
              <button onClick={()=>setDetail(null)} style={{background:'none',border:'none',fontSize:20,cursor:'pointer'}}>x</button>
            </div>
            {detail.related_posts?.length > 0 && (
              <div style={{marginBottom:16}}>
                <h4 style={{marginBottom:8,color:'#374151'}}>발행된 관련 글</h4>
                {detail.related_posts.map((p,i) => (
                  <div key={i} style={{padding:'8px 0',borderBottom:'1px solid #f3f4f6',fontSize:13}}>
                    <div style={{fontWeight:600}}>{p.blog_name}</div>
                    <div>{p.title}</div>
                    {p.url && <a href={p.url} target="_blank" rel="noreferrer" style={{color:'#3b82f6',fontSize:12}}>{p.url}</a>}
                    <div style={{color:'#9ca3af',fontSize:11}}>{p.published_at}</div>
                  </div>
                ))}
              </div>
            )}
            {detail.gsc_keywords?.length > 0 && (
              <div>
                <h4 style={{marginBottom:8,color:'#374151'}}>GSC 키워드 성과</h4>
                <table style={tableStyle}>
                  <thead><tr style={{background:'#f8fafc'}}>
                    <th style={thStyle}>사이트</th><th style={thStyle}>키워드</th>
                    <th style={{...thStyle,textAlign:'right'}}>클릭</th><th style={{...thStyle,textAlign:'right'}}>노출</th><th style={{...thStyle,textAlign:'right'}}>순위</th>
                  </tr></thead>
                  <tbody>{detail.gsc_keywords.map((k,i) => (
                    <tr key={i} style={{borderBottom:'1px solid #f3f4f6'}}>
                      <td style={{...tdStyle,fontSize:12}}>{k.site}</td><td style={tdStyle}>{k.query}</td>
                      <td style={{...tdStyle,textAlign:'right'}}>{k.clicks}</td><td style={{...tdStyle,textAlign:'right'}}>{k.impressions}</td>
                      <td style={{...tdStyle,textAlign:'right'}}>{k.avg_position?.toFixed(1)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            )}
            {(!detail.related_posts||detail.related_posts.length===0)&&(!detail.gsc_keywords||detail.gsc_keywords.length===0) && (
              <p style={{color:'#9ca3af'}}>관련 데이터가 없습니다</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function TitleCrawler() {
  const [url, setUrl] = useState('')
  const [maxCount, setMaxCount] = useState(100)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const LOCAL_API = 'http://localhost:5001'

  const startCrawl = async () => {
    if (!url.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch(LOCAL_API + '/api/crawl', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ url: url.trim(), max: maxCount })
      })
      const data = await res.json()
      if (data.error && !data.titles) {
        setError(data.error)
      } else {
        setResult(data)
      }
    } catch(e) {
      setError('로컬 서버 연결 실패. 터미널에서 먼저 실행하세요: python local_api.py')
    }
    setLoading(false)
  }

  return (
    <div>
      <div style={{background:'#eff6ff',border:'1px solid #bfdbfe',borderRadius:12,padding:16,marginBottom:16}}>
        <p style={{fontSize:12,color:'#1e40af',margin:0}}>로컬 서버 필요: <code>cd /Users/twinssn/Projects/blogdex/cli && python local_api.py</code></p>
      </div>

      <div style={{display:'flex',gap:8,marginBottom:16,flexWrap:'wrap'}}>
        <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.tistory.com 또는 https://blog.naver.com/blogid"
          onKeyDown={e => e.key === 'Enter' && startCrawl()}
          style={{...inputStyle,flex:1,minWidth:300}} />
        <select value={maxCount} onChange={e => setMaxCount(Number(e.target.value))}
          style={{...inputStyle,width:100}}>
          <option value={50}>50개</option>
          <option value={100}>100개</option>
          <option value={200}>200개</option>
          <option value={500}>500개</option>
          <option value={1000}>1000개</option>
        </select>
        <button onClick={startCrawl} disabled={loading}
          style={{...btnStyle, opacity: loading ? 0.5 : 1}}>
          {loading ? '수집 중...' : '수집 시작'}
        </button>
      </div>

      {error && (
        <div style={{background:'#fef2f2',border:'1px solid #fecaca',borderRadius:8,padding:12,marginBottom:16,color:'#dc2626',fontSize:13}}>
          {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:16}}>
            <StatCard label="출처" value={result.source} />
            <StatCard label="전체 포스트" value={result.total_posts} />
            <StatCard label="수집된 타이틀" value={result.crawled} color="#10b981" />
            <StatCard label="DB 저장" value={result.saved_to_db ? 'OK' : '실패'} color={result.saved_to_db ? '#10b981' : '#ef4444'} />
          </div>

          {result.titles && result.titles.length > 0 && (
            <table style={tableStyle}>
              <thead><tr style={{background:'#f8fafc'}}>
                <th style={{...thStyle,width:40}}>#</th>
                <th style={thStyle}>타이틀</th>
                <th style={thStyle}>URL</th>
              </tr></thead>
              <tbody>{result.titles.map((t, i) => (
                <tr key={i} style={{borderBottom:'1px solid #f3f4f6'}}>
                  <td style={{...tdStyle,textAlign:'center',color:'#9ca3af'}}>{i+1}</td>
                  <td style={tdStyle}>{t.title}</td>
                  <td style={{...tdStyle,fontSize:11,maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                    <a href={t.url} target="_blank" rel="noreferrer" style={{color:'#3b82f6'}}>{t.url}</a>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}


function OpportunityDashboard() {
  const [rewrite, setRewrite] = useState([])
  const [topPages, setTopPages] = useState([])
  const [seoOpp, setSeoOpp] = useState([])
  const [blogEff, setBlogEff] = useState([])
  const [rpmRanking, setRpmRanking] = useState([])
  const [revSummary, setRevSummary] = useState([])
  const [loading, setLoading] = useState(true)
  const [panel, setPanel] = useState('rewrite')

  useEffect(() => {
    Promise.all([
      api.get('/analysis/rewrite-targets'),
      api.get('/analysis/top-pages'),
      api.get('/analysis/seo-opportunity'),
      api.get('/analysis/blog-efficiency'),
      api.get('/analysis/rpm-ranking'),
      api.get('/analysis/revenue-summary'),
    ]).then(([r, t, s, b, rpm, rev]) => {
      setRewrite(r); setTopPages(t); setSeoOpp(s); setBlogEff(b); setRpmRanking(rpm||[]); setRevSummary(rev||[]); setLoading(false)
    }).catch(e => { console.error(e); setLoading(false) })
  }, [])

  if (loading) return <div style={{padding:40,textAlign:'center'}}>분석 데이터 로딩 중...</div>

  const panelBtns = [
    {key:'rewrite', label:'타이틀 리라이트 대상', count:rewrite.length, color:'#ef4444'},
    {key:'top', label:'트래픽 TOP 글', count:topPages.length, color:'#3b82f6'},
    {key:'seo', label:'구글 SEO 보강', count:seoOpp.length, color:'#f59e0b'},
    {key:'eff', label:'블로그별 효율', count:blogEff.length, color:'#10b981'},
    {key:'rpm', label:'RPM 높은 글', count:rpmRanking.length, color:'#8b5cf6'},
    {key:'rev', label:'사이트별 수익', count:revSummary.length, color:'#ec4899'},
  ]

  const thStyle = {padding:'8px 12px',borderBottom:'2px solid #e5e7eb',textAlign:'left',fontSize:13,fontWeight:600,background:'#f9fafb'}
  const tdStyle = {padding:'8px 12px',borderBottom:'1px solid #f3f4f6',fontSize:13}

  return <div>
    <div style={{display:'flex',gap:12,marginBottom:20,flexWrap:'wrap'}}>
      {panelBtns.map(b => (
        <button key={b.key} onClick={() => setPanel(b.key)} style={{
          padding:'12px 20px', borderRadius:10, border: panel===b.key ? '2px solid '+b.color : '1px solid #e5e7eb',
          background: panel===b.key ? b.color+'15' : '#fff', cursor:'pointer', minWidth:180
        }}>
          <div style={{fontSize:24,fontWeight:700,color:b.color}}>{b.count}</div>
          <div style={{fontSize:13,color:'#374151',marginTop:4}}>{b.label}</div>
        </button>
      ))}
    </div>

    {panel==='rewrite' && <div>
      <h3 style={{marginBottom:12}}>노출은 되지만 클릭이 없는 글 - 타이틀 변경 필요</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
          <th style={thStyle}>노출</th><th style={thStyle}>순위</th><th style={thStyle}>검색어</th>
        </tr></thead>
        <tbody>{rewrite.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,maxWidth:300,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            <a href={r.page} target="_blank" rel="noreferrer" style={{color:'#6b7280',fontSize:12}}>{decodeURIComponent(r.page).split('/').pop() || r.page}</a>
          </td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:600}}>{r.imp}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.pos}</td>
          <td style={{...tdStyle,fontSize:11,color:'#6b7280',maxWidth:200,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.queries}</td>
        </tr>)}</tbody>
      </table>
    </div>}

    {panel==='top' && <div>
      <h3 style={{marginBottom:12}}>페이지뷰 TOP 30 - 가장 많이 읽히는 글</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
          <th style={thStyle}>PV</th><th style={thStyle}>세션</th>
        </tr></thead>
        <tbody>{topPages.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,maxWidth:350,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            <a href={r.page} target="_blank" rel="noreferrer" style={{color:'#6b7280',fontSize:12}}>{decodeURIComponent(r.page).split('/').pop() || r.page}</a>
          </td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color:'#059669'}}>{r.pv}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.sess}</td>
        </tr>)}</tbody>
      </table>
    </div>}

    {panel==='seo' && <div>
      <h3 style={{marginBottom:12}}>GA4 트래픽 있지만 구글 노출 없음 - SEO 보강 대상</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>URL</th><th style={thStyle}>PV</th>
        </tr></thead>
        <tbody>{seoOpp.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,maxWidth:400,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            <a href={r.page} target="_blank" rel="noreferrer" style={{color:'#6b7280',fontSize:12}}>{decodeURIComponent(r.page).split('/').pop() || r.page}</a>
          </td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color:'#d97706'}}>{r.pv}</td>
        </tr>)}</tbody>
      </table>
    </div>}

    {panel==='eff' && <div>
      <h3 style={{marginBottom:12}}>블로그별 효율 - 글 1편당 평균 PV</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>총 PV</th>
          <th style={thStyle}>글 수</th><th style={thStyle}>글당 PV</th>
        </tr></thead>
        <tbody>{blogEff.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.total_pv?.toLocaleString()}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.pages}</td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color:'#059669'}}>{r.pv_per_page}</td>
        </tr>)}</tbody>
      </table>
    </div>}

    {panel==='rpm' && <div>
      <h3 style={{marginBottom:12}}>RPM 높은 글 TOP 50 - 이런 주제가 돈이 됩니다</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>URL</th>
          <th style={thStyle}>PV</th><th style={thStyle}>수익($)</th><th style={thStyle}>RPM($)</th>
        </tr></thead>
        <tbody>{rpmRanking.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,maxWidth:300,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
            <a href={r.page} target="_blank" rel="noreferrer" style={{color:'#6b7280',fontSize:12}}>{decodeURIComponent(r.page).split('/').pop() || r.page}</a>
          </td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.pv}</td>
          <td style={{...tdStyle,textAlign:'right',color:'#059669'}}>${r.rev?.toFixed(2)}</td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color: r.rpm > 10 ? '#dc2626' : r.rpm > 5 ? '#f59e0b' : '#6b7280'}}>${r.rpm?.toFixed(2)}</td>
        </tr>)}</tbody>
      </table>
    </div>}

    {panel==='rev' && <div>
      <h3 style={{marginBottom:12}}>사이트별 수익 요약 (30일) - 어디에 글을 써야 돈이 되나</h3>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead><tr>
          <th style={thStyle}>사이트</th><th style={thStyle}>총 PV</th>
          <th style={thStyle}>총 수익($)</th><th style={thStyle}>RPM($)</th><th style={thStyle}>글 수</th>
        </tr></thead>
        <tbody>{revSummary.map((r,i) => <tr key={i} style={{background:i%2?'#f9fafb':'#fff'}}>
          <td style={{...tdStyle,fontWeight:600,color:'#2563eb'}}>{r.site}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.total_pv?.toLocaleString()}</td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color:'#059669'}}>${r.total_rev?.toFixed(2)}</td>
          <td style={{...tdStyle,textAlign:'right',fontWeight:700,color: r.rpm > 5 ? '#dc2626' : r.rpm > 2 ? '#f59e0b' : '#6b7280'}}>${r.rpm?.toFixed(2)}</td>
          <td style={{...tdStyle,textAlign:'right'}}>{r.pages}</td>
        </tr>)}</tbody>
      </table>
    </div>}

  </div>
}

function KeywordCheck() {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState([])
  const [searched, setSearched] = useState(false)

  const search = async () => {
    if (!keyword.trim()) return
    try {
      const res = await api.get('/posts/search?q=' + encodeURIComponent(keyword))
      setResults(res.data.results || [])
      setSearched(true)
    } catch (e) { alert('검색 실패: ' + e.message) }
  }

  return (
    <div>
      <h3 style={{marginBottom:12}}>키워드 중복 체크</h3>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <input value={keyword} onChange={e=>setKeyword(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&search()}
          placeholder="키워드 입력" style={inputStyle} />
        <button onClick={search} style={btnStyle}>체크</button>
      </div>
      {searched && results.length === 0 && (
        <div style={{padding:16,background:'#ecfdf5',borderRadius:8,color:'#065f46',fontWeight:600}}>
          '{keyword}' — 쓴 적 없음! 새로운 주제입니다.
        </div>
      )}
      {results.length > 0 && (
        <div>
          <div style={{padding:12,background:'#fef3c7',borderRadius:8,color:'#92400e',marginBottom:12,fontWeight:600}}>
            '{keyword}' 관련 글 {results.length}건 발견
          </div>
          <table style={tableStyle}>
            <thead><tr style={{background:'#f8fafc'}}>
              <th style={thStyle}>블로그</th><th style={thStyle}>타이틀</th><th style={thStyle}>발행일</th>
            </tr></thead>
            <tbody>{results.slice(0,30).map((r,i)=>(
              <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                <td style={{...tdStyle,fontSize:12,color:'#666'}}>{r.blog_name}</td>
                <td style={tdStyle}>{r.title}</td>
                <td style={{...tdStyle,fontSize:12,color:'#999'}}>{r.published_at}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  )
}

const pillStyle = {padding:'6px 14px',borderRadius:20,border:'none',cursor:'pointer',fontSize:13,fontWeight:500}
const btnStyle = {padding:'10px 20px',fontSize:14,borderRadius:8,border:'none',background:'#3b82f6',color:'#fff',cursor:'pointer',fontWeight:500}
const inputStyle = {flex:1,padding:10,fontSize:14,borderRadius:8,border:'1px solid #d1d5db',outline:'none'}
const tableStyle = {width:'100%',borderCollapse:'collapse',fontSize:13}
const thStyle = {padding:'10px 12px',textAlign:'left',fontWeight:600,color:'#374151',borderBottom:'2px solid #e5e7eb'}
const tdStyle = {padding:'8px 12px'}

function App() {
  const [tab, setTab] = useState(0)
  return (
    <div style={{maxWidth:1000,margin:'0 auto',padding:'16px 20px',fontFamily:'-apple-system,BlinkMacSystemFont,sans-serif'}}>
      <h1 style={{fontSize:22,marginBottom:16,fontWeight:700}}>Blogdex</h1>
      <div style={{display:'flex',gap:4,marginBottom:24,flexWrap:'wrap'}}>
        {tabs.map((t,i)=>(
          <button key={i} onClick={()=>setTab(i)}
            style={{padding:'8px 16px',borderRadius:8,border:'none',
              background:tab===i?'#3b82f6':'#f3f4f6',
              color:tab===i?'#fff':'#374151',cursor:'pointer',fontSize:13,fontWeight:500}}>
            {t}
          </button>
        ))}
      </div>
      {tab===0 && <Dashboard/>}
      {tab===1 && <SitesView/>}
      {tab===2 && <KeywordsView/>}
      {tab===3 && <RewriteQueue/>}
      {tab===4 && <TitleManager/>}
      {tab===5 && <TitleCrawler/>}
      {tab===6 && <KeywordCheck/>}
      {tab===7 && <OpportunityDashboard/>}
    </div>
  )
}

export default App

