-- Migration: 000_migrations_table
-- Description: Migration tracking table — records every applied migration
-- Applied: tracked in _migrations table (this file bootstraps it)
-- 
-- WARNING: This is the bootstrap migration. It must always be applied first.
-- The _migrations table stores the version history so subsequent runs
-- skip already-applied migrations.

CREATE TABLE IF NOT EXISTS _migrations (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    version   TEXT NOT NULL UNIQUE,
    filename  TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Record this migration itself
INSERT OR IGNORE INTO _migrations (version, filename)
VALUES ('000', '000_migrations_table.sql');
