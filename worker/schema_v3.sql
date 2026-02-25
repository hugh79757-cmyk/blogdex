-- v0.7.0 sync_log 테이블

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

CREATE INDEX IF NOT EXISTS idx_sync_log_source ON sync_log(source);
CREATE INDEX IF NOT EXISTS idx_sync_log_synced ON sync_log(last_synced_at);
