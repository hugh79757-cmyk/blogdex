-- v0.7.0 Bing 전용 테이블

CREATE TABLE IF NOT EXISTS bing_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    account TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date)
);

CREATE TABLE IF NOT EXISTS bing_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    query TEXT NOT NULL,
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    position REAL DEFAULT 0,
    account TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date, query)
);

CREATE INDEX IF NOT EXISTS idx_bing_daily_site_date ON bing_daily(site, date);
CREATE INDEX IF NOT EXISTS idx_bing_keywords_site_date ON bing_keywords(site, date);
CREATE INDEX IF NOT EXISTS idx_bing_keywords_query ON bing_keywords(query);
