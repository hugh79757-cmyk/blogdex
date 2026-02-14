-- v0.3.0 스키마 확장

-- GSC 일별 사이트 요약
CREATE TABLE IF NOT EXISTS gsc_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date)
);

-- GSC 키워드 일별 데이터
CREATE TABLE IF NOT EXISTS gsc_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    query TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    position REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date, query)
);

-- 쿠팡 파트너스 수익
CREATE TABLE IF NOT EXISTS coupang_revenue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    sub_id TEXT,
    clicks INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    amount REAL DEFAULT 0,
    revenue REAL DEFAULT 0,
    product TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, sub_id, product)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_gsc_daily_site_date ON gsc_daily(site, date);
CREATE INDEX IF NOT EXISTS idx_gsc_keywords_site_date ON gsc_keywords(site, date);
CREATE INDEX IF NOT EXISTS idx_gsc_keywords_query ON gsc_keywords(query);
CREATE INDEX IF NOT EXISTS idx_coupang_date ON coupang_revenue(date);
CREATE INDEX IF NOT EXISTS idx_coupang_sub ON coupang_revenue(sub_id);
