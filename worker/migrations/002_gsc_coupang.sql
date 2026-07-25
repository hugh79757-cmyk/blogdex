-- Migration: 002_gsc_coupang
-- Description: GSC daily/keyword tables + Coupang revenue
-- Source: worker/schema_v2.sql
-- Applied: tracked in _migrations table

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

CREATE TABLE IF NOT EXISTS gsc_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    query TEXT NOT NULL,
    page TEXT DEFAULT '',
    clicks INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    ctr REAL DEFAULT 0,
    position REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date, query, page)
);

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

CREATE INDEX IF NOT EXISTS idx_gsc_daily_site_date ON gsc_daily(site, date);
CREATE INDEX IF NOT EXISTS idx_gsc_keywords_site_date ON gsc_keywords(site, date);
CREATE INDEX IF NOT EXISTS idx_gsc_keywords_query ON gsc_keywords(query);
CREATE INDEX IF NOT EXISTS idx_coupang_date ON coupang_revenue(date);
CREATE INDEX IF NOT EXISTS idx_coupang_sub ON coupang_revenue(sub_id);
