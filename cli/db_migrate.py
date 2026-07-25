#!/usr/bin/env python3
"""
Blogdex D1 Database Migrator (Python)

Applies pending SQL migrations to the Cloudflare D1 database via wrangler CLI.
Tracks applied migrations in the _migrations table.

Usage:
    python cli/db_migrate.py                    # production
    python cli/db_migrate.py --env preview      # preview
    python cli/db_migrate.py --dry-run          # show what would be applied
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ── Paths ──
PROJECT_DIR = Path(__file__).resolve().parent.parent
WORKER_DIR = PROJECT_DIR / "worker"
MIGRATIONS_DIR = WORKER_DIR / "migrations"


def get_applied_migrations(env: str) -> set[str]:
    """Query the _migrations table for already-applied filenames."""
    try:
        result = subprocess.run(
            [
                "npx", "wrangler", "d1", "execute", "blogdex_db",
                "--env", env,
                "--command", "SELECT filename FROM _migrations ORDER BY id",
                "--json",
            ],
            capture_output=True, text=True, timeout=30,
            cwd=str(WORKER_DIR),
        )
        if result.returncode != 0:
            return set()  # Table probably doesn't exist yet

        rows = json.loads(result.stdout) if result.stdout.strip() else []
        if isinstance(rows, list):
            return {row.get("filename", "") for row in rows if row.get("filename")}
        return set()
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return set()


def apply_migration(env: str, migration_path: Path, dry_run: bool) -> bool:
    """Apply a single migration file. Returns True on success."""
    filename = migration_path.name
    sql = migration_path.read_text(encoding="utf-8")

    if dry_run:
        return True

    try:
        result = subprocess.run(
            [
                "npx", "wrangler", "d1", "execute", "blogdex_db",
                "--env", env,
                "--command", sql,
                "--json",
            ],
            capture_output=True, text=True, timeout=60,
            cwd=str(WORKER_DIR),
        )
        if result.returncode != 0:
            print(f"       ❌ FAILED")
            print(f"       {result.stderr.strip()[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"       ❌ TIMEOUT (60s)")
        return False
    except FileNotFoundError as e:
        print(f"       ❌ {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Blogdex D1 Database Migrator")
    parser.add_argument("--env", default="production", choices=["production", "preview"],
                        help="D1 environment (default: production)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be applied without making changes")
    args = parser.parse_args()

    # ── Discover migration files ──
    if not MIGRATIONS_DIR.exists():
        print(f"Error: migrations directory not found: {MIGRATIONS_DIR}")
        sys.exit(1)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        print("No migration files found.")
        return

    # ── Check applied status ──
    print("=" * 50)
    print(f"  Blogdex D1 Migration")
    print(f"  Environment: {args.env}")
    print(f"  Migrations:  {MIGRATIONS_DIR}")
    print(f"  Dry run:     {args.dry_run}")
    print("=" * 50)
    print(f"\nFound {len(migration_files)} migration files\n")

    applied = get_applied_migrations(args.env)
    print(f"Already applied: {len(applied)} files\n")

    # ── Apply ──
    applied_count = 0
    skipped_count = 0
    error_count = 0

    for mf in migration_files:
        fname = mf.name
        if fname in applied:
            print(f"  ⏭️  {fname} (already applied)")
            skipped_count += 1
            continue

        print(f"  ▶  {fname}")
        if args.dry_run:
            print(f"       [dry-run — would apply]")
            applied_count += 1
            continue

        if apply_migration(args.env, mf, args.dry_run):
            print(f"       ✅ Applied")
            applied_count += 1
        else:
            error_count += 1

    # ── Summary ──
    print()
    print("=" * 50)
    print(f"  Applied: {applied_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors:  {error_count}")
    if args.dry_run:
        print("  (dry run — no changes made)")
    print("=" * 50)

    if error_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
