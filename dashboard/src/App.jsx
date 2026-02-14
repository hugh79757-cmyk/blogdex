import { useState, useEffect } from 'react'
import api from './api'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const tabs = ['대시보드', '사이트별', '키워드', '리라이트 큐', '타이틀 관리', '키워드 체크']

const COLORS = { high: '#ef4444', medium: '#f59e0b', low: '#9ca3af' }

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


function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [daily, setDaily] = useState([])
  const [days, setDays] = useState(30)
  const { sortField, sortDir, onSort, sortData } = useSort('impressions')



  useEffect(() => {
    api.get('/dashboard/summary?days=' + days).then(r => setSummary(r.data))
    api.get('/gsc/daily?days=' + days).then(r => setDaily(r.data))
  }, [days])

  if (!summary) return <p style={{padding:20}}>로딩 중...</p>

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
        <StatCard label={`클릭 (${days}일)`} value={summary.gsc_clicks?.toLocaleString()} color="#10b981" />
        <StatCard label={`노출 (${days}일)`} value={summary.gsc_impressions?.toLocaleString()} color="#3b82f6" />
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
      ) : <p style={{color:'#999'}}>데이터 없음</p>}
    </div>
  )
}

function SitesView() {
  const [sites, setSites] = useState([])
  const [days, setDays] = useState(30)

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
        <>
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
              {sites.map((s,i) => (
                <tr key={i} style={{borderBottom:'1px solid #eee'}}>
                  <td style={tdStyle}>{s.site}</td>
                  <td style={{...tdStyle,textAlign:'right',color:'#10b981',fontWeight:600}}>{s.clicks}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{s.impressions?.toLocaleString()}</td>
                  <td style={{...tdStyle,textAlign:'right'}}>{s.ctr}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : <p style={{color:'#999'}}>데이터 없음</p>}
    </div>
  )
}

function KeywordsView() {
  const [keywords, setKeywords] = useState([])
  const [days, setDays] = useState(30)
  const [filter, setFilter] = useState('')
  const { sortField, sortDir, onSort, sortData } = useSort('impressions')


  useEffect(() => {
    let url = '/gsc/keywords?days=' + days + '&limit=200'
    if (filter) url += '&value=' + filter
    api.get(url).then(r => {
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
            style={{...pillStyle, background: filter===f.v ? (COLORS[f.v]||'#3b82f6') : '#e5e7eb', color: filter===f.v ? '#fff' : '#333'}}>
            {f.l}
          </button>
        ))}
      </div>

      <div style={{marginBottom:8,color:'#666',fontSize:13}}>
        총 {keywords.length}개 | HIGH {keywords.filter(k=>k.value==='high').length} | MED {keywords.filter(k=>k.value==='medium').length} | LOW {keywords.filter(k=>k.value==='low').length}
      </div>

      <table style={tableStyle}>
                  <thead>
            <tr style={{background:'#f8fafc'}}>
              <SortHeader label="키워드" field="query" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="가치" field="value" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="노출" field="impressions" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="클릭" field="clicks" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="CTR" field="ctr" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="순위" field="avg_position" align="right" sortField={sortField} sortDir={sortDir} onSort={onSort} />
            </tr>
          </thead>

        <tbody>
          {keywords.slice(0,100).map((k,i) => (
            <tr key={i} style={{borderBottom:'1px solid #eee'}}>
              <td style={tdStyle}>{k.query}</td>
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

        if (action) {
          queue.push({...k, action, priority})
        }
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
            {keywords.slice(0,50).map((k,i) => {
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
  const [input, setInput] = useState('')
  const [titles, setTitles] = useState([])
  const [saved, setSaved] = useState(false)
  const [search, setSearch] = useState('')
  const [results, setResults] = useState([])

  const addTitle = () => {
    if (!input.trim()) return
    setTitles([...titles, { title: input.trim(), url: '', source: 'manual' }])
    setInput('')
    setSaved(false)
  }

  const removeTitle = (i) => setTitles(titles.filter((_, idx) => idx !== i))

  const saveTitles = async () => {
    if (titles.length === 0) return
    try {
      await api.post('/titles', { titles })
      setSaved(true)
      setTitles([])
    } catch (e) { alert('저장 실패: ' + e.message) }
  }

  const searchTitles = async () => {
    if (!search.trim()) return
    try {
      const res = await api.get('/titles/search?q=' + encodeURIComponent(search))
      setResults(res.data.results || [])
    } catch (e) { alert('검색 실패: ' + e.message) }
  }

  return (
    <div>
      <h3 style={{marginBottom:12}}>타이틀 입력</h3>
      <div style={{display:'flex',gap:8,marginBottom:12}}>
        <input value={input} onChange={e=>setInput(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&addTitle()}
          placeholder="새 타이틀 입력 후 Enter"
          style={inputStyle} />
        <button onClick={addTitle} style={btnStyle}>추가</button>
      </div>
      {titles.length > 0 && (
        <div style={{marginBottom:12}}>
          {titles.map((t,i) => (
            <div key={i} style={{display:'flex',justifyContent:'space-between',padding:8,background:'#f5f5f5',borderRadius:6,marginBottom:4}}>
              <span>{t.title}</span>
              <button onClick={()=>removeTitle(i)} style={{color:'red',border:'none',background:'none',cursor:'pointer'}}>X</button>
            </div>
          ))}
          <button onClick={saveTitles} style={{...btnStyle,background:'#10b981',marginTop:8}}>
            {titles.length}개 저장
          </button>
        </div>
      )}
      {saved && <p style={{color:'#10b981'}}>저장 완료!</p>}

      <h3 style={{marginTop:24,marginBottom:12}}>타이틀 검색</h3>
      <div style={{display:'flex',gap:8}}>
        <input value={search} onChange={e=>setSearch(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&searchTitles()}
          placeholder="키워드로 검색" style={inputStyle} />
        <button onClick={searchTitles} style={btnStyle}>검색</button>
      </div>
      {results.length > 0 && (
        <table style={{...tableStyle,marginTop:12}}>
          <thead><tr style={{background:'#f8fafc'}}><th style={thStyle}>타이틀</th><th style={thStyle}>출처</th><th style={thStyle}>상태</th></tr></thead>
          <tbody>{results.slice(0,50).map((r,i)=>(
            <tr key={i} style={{borderBottom:'1px solid #eee'}}><td style={tdStyle}>{r.title}</td><td style={tdStyle}>{r.source}</td><td style={tdStyle}>{r.status}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  )
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
        <>
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
        </>
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div style={{padding:16,background:'#fff',borderRadius:12,border:'1px solid #e5e7eb',boxShadow:'0 1px 3px rgba(0,0,0,0.05)'}}>
      <div style={{fontSize:13,color:'#6b7280',marginBottom:4}}>{label}</div>
      <div style={{fontSize:28,fontWeight:700,color:color||'#111'}}>{value}</div>
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
      {tab===5 && <KeywordCheck/>}
    </div>
  )
}

export default App
