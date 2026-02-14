import { useState } from 'react'
import api from './api'

const tabs = ['타이틀 관리', '키워드 체크', '퍼포먼스']

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

  const removeTitle = (i) => {
    setTitles(titles.filter((_, idx) => idx !== i))
  }

  const saveTitles = async () => {
    if (titles.length === 0) return
    try {
      await api.post('/titles', { titles })
      setSaved(true)
      setTitles([])
    } catch (e) {
      alert('저장 실패: ' + e.message)
    }
  }

  const searchTitles = async () => {
    if (!search.trim()) return
    try {
      const res = await api.get('/titles/search?q=' + encodeURIComponent(search))
      setResults(res.data.results || [])
    } catch (e) {
      alert('검색 실패: ' + e.message)
    }
  }

  return (
    <div>
      <h2 style={{marginBottom:16}}>타이틀 입력</h2>
      <div style={{display:'flex',gap:8,marginBottom:12}}>
        <input value={input} onChange={e=>setInput(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&addTitle()}
          placeholder="새 타이틀 입력 후 Enter"
          style={{flex:1,padding:10,fontSize:16,borderRadius:8,border:'1px solid #ccc'}} />
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
      <h2 style={{marginTop:24,marginBottom:16}}>타이틀 검색</h2>
      <div style={{display:'flex',gap:8}}>
        <input value={search} onChange={e=>setSearch(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&searchTitles()}
          placeholder="키워드로 검색"
          style={{flex:1,padding:10,fontSize:16,borderRadius:8,border:'1px solid #ccc'}} />
        <button onClick={searchTitles} style={btnStyle}>검색</button>
      </div>
      {results.length > 0 && (
        <table style={tableStyle}>
          <thead><tr><th>타이틀</th><th>출처</th></tr></thead>
          <tbody>{results.map((r,i)=>(
            <tr key={i}><td>{r.title}</td><td>{r.source}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  )
}

function KeywordCheck() {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState([])

  const search = async () => {
    if (!keyword.trim()) return
    try {
      const res = await api.get('/posts/search?q=' + encodeURIComponent(keyword))
      setResults(res.data.results || [])
    } catch (e) {
      alert('검색 실패: ' + e.message)
    }
  }

  return (
    <div>
      <h2 style={{marginBottom:16}}>키워드 중복 체크</h2>
      <div style={{display:'flex',gap:8,marginBottom:16}}>
        <input value={keyword} onChange={e=>setKeyword(e.target.value)}
          onKeyDown={e=>e.key==='Enter'&&search()}
          placeholder="키워드 입력"
          style={{flex:1,padding:10,fontSize:16,borderRadius:8,border:'1px solid #ccc'}} />
        <button onClick={search} style={btnStyle}>체크</button>
      </div>
      {results.length > 0 ? (
        <table style={tableStyle}>
          <thead><tr><th>블로그</th><th>타이틀</th><th>발행일</th></tr></thead>
          <tbody>{results.map((r,i)=>(
            <tr key={i}><td>{r.blog_name}</td><td>{r.title}</td><td>{r.published_at}</td></tr>
          ))}</tbody>
        </table>
      ) : keyword && <p style={{color:'#666'}}>검색 결과 없음</p>}
    </div>
  )
}

function Performance() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get('/performance?days=30')
      setData(res.data.results || [])
    } catch (e) {
      alert('로드 실패: ' + e.message)
    }
    setLoading(false)
  }

  return (
    <div>
      <h2 style={{marginBottom:16}}>퍼포먼스 (최근 30일)</h2>
      <button onClick={load} style={btnStyle}>{loading ? '로딩...' : '데이터 불러오기'}</button>
      {data.length > 0 && (
        <table style={{...tableStyle,marginTop:16}}>
          <thead><tr><th>블로그</th><th>조회수</th><th>클릭</th></tr></thead>
          <tbody>{data.map((r,i)=>(
            <tr key={i}><td>{r.title}</td><td>{r.pageviews}</td><td>{r.clicks}</td></tr>
          ))}</tbody>
        </table>
      )}
    </div>
  )
}

const btnStyle = {padding:'10px 20px',fontSize:16,borderRadius:8,border:'none',background:'#3b82f6',color:'#fff',cursor:'pointer'}
const tableStyle = {width:'100%',borderCollapse:'collapse',marginTop:12,fontSize:14}

function App() {
  const [tab, setTab] = useState(0)
  return (
    <div style={{maxWidth:800,margin:'0 auto',padding:16,fontFamily:'sans-serif'}}>
      <h1 style={{fontSize:24,marginBottom:16}}>Blogdex</h1>
      <div style={{display:'flex',gap:4,marginBottom:24}}>
        {tabs.map((t,i)=>(
          <button key={i} onClick={()=>setTab(i)}
            style={{padding:'10px 16px',borderRadius:8,border:'none',
              background:tab===i?'#3b82f6':'#e5e7eb',
              color:tab===i?'#fff':'#333',cursor:'pointer',fontSize:14}}>
            {t}
          </button>
        ))}
      </div>
      {tab===0 && <TitleManager/>}
      {tab===1 && <KeywordCheck/>}
      {tab===2 && <Performance/>}
    </div>
  )
}

export default App
