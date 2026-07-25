-- Migration: 003_ga4_sync
-- Description: GA4 pageviews (was missing from all schema files) + sync_log
-- Source: worker/schema_v3.sql (sync_log) + newly documented ga4_pageviews
-- Applied: tracked in _migrations table
--
-- NOTE: ga4_pageviews has been in production use since v0.5 but was never
-- captured in a schema file. Its CREATE TABLE is defined here for the first time.

CREATE TABLE IF NOT EXISTS ga4_pageviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    date TEXT NOT NULL,
    page TEXT NOT NULL,
    pageviews INTEGER DEFAULT 0,
    sessions INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site, date, page)
);

CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    site TEXT,
    last_synced_at TEXT NOT NULL,
    last_date_covered TEXT,
    row_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ok',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ga4_pageviews_site_date ON ga4_pageviews(site, date);
CREATE INDEX IF NOT EXISTS idx_sync_log_source ON sync_log(source);
CREATE INDEX IF NOT EXISTS idx_sync_log_synced ON sync_log(last_synced_at);
