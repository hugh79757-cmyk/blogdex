#!/usr/bin/env bash
# =============================================================================
#  Blogdex D1 Migration Script
#
#  Iterates through worker/migrations/*.sql in order, checks _migrations
#  table to skip already-applied files, and applies new ones.
#
#  Usage:
#    ./worker/migrate.sh                    # apply to production
#    ./worker/migrate.sh --env preview      # apply to preview
#    ./worker/migrate.sh --dry-run          # show what would be applied
#    ./worker/migrate.sh --env preview --dry-run
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"

ENV="production"
DRY_RUN=false

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)
            ENV="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env production|preview] [--dry-run]"
            exit 1
            ;;
    esac
done

if [[ "$ENV" != "production" && "$ENV" != "preview" ]]; then
    echo "Error: --env must be 'production' or 'preview', got '$ENV'"
    exit 1
fi

echo "=========================================="
echo "  Blogdex D1 Migration"
echo "  Environment: $ENV"
echo "  Migrations:  $MIGRATIONS_DIR"
echo "  Dry run:     $DRY_RUN"
echo "=========================================="
echo ""

# ── Get list of migration files (sorted) ──
MIGRATION_FILES=()
for f in "$MIGRATIONS_DIR"/*.sql; do
    MIGRATION_FILES+=("$f")
done
IFS=$'\n' MIGRATION_FILES=($(sort <<<"${MIGRATION_FILES[*]}")); unset IFS

if [[ ${#MIGRATION_FILES[@]} -eq 0 ]]; then
    echo "No migration files found in $MIGRATIONS_DIR"
    exit 0
fi

echo "Found ${#MIGRATION_FILES[@]} migration files"
echo ""

# ── Check if _migrations table exists and list applied versions ──
# We do this by trying to query the table; if it fails, no migrations applied yet.
MIGRATIONS_QUERY="SELECT filename FROM _migrations ORDER BY id"
APPLIED=$(cd "$PROJECT_DIR" && npx wrangler d1 execute blogdex_db --env "$ENV" --command "$MIGRATIONS_QUERY" --json 2>/dev/null || echo "")

APPLIED_FILES=()
if echo "$APPLIED" | grep -q '"filename"'; then
    while IFS= read -r line; do
        fname=$(echo "$line" | sed 's/.*"filename":"\([^"]*\)".*/\1/')
        if [[ -n "$fname" ]]; then
            APPLIED_FILES+=("$fname")
        fi
    done < <(echo "$APPLIED" | grep -o '"filename":"[^"]*"')
fi

echo "Already applied: ${#APPLIED_FILES[@]} files"
echo ""

# ── Apply each migration ──
APPLIED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

for MIGRATION_FILE in "${MIGRATION_FILES[@]}"; do
    BASENAME=$(basename "$MIGRATION_FILE")

    # Check if already applied
    if printf '%s\n' "${APPLIED_FILES[@]}" | grep -qx "$BASENAME"; then
        echo "  ⏭️  $BASENAME (already applied)"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        continue
    fi

    echo "  ▶  $BASENAME"

    if $DRY_RUN; then
        echo "       [dry-run — would apply]"
        APPLIED_COUNT=$((APPLIED_COUNT + 1))
        continue
    fi

    # Read the SQL content
    SQL_CONTENT=$(cat "$MIGRATION_FILE")

    # Execute via wrangler
    # For 000_migrations_table.sql, the INSERT OR IGNORE records the migration
    if ! OUTPUT=$(cd "$PROJECT_DIR" && npx wrangler d1 execute blogdex_db \
        --env "$ENV" \
        --command "$SQL_CONTENT" \
        --json 2>&1); then
        echo "       ❌ FAILED"
        echo "       Error: $(echo "$OUTPUT" | tail -3)"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        continue
    fi

    echo "       ✅ Applied"
    APPLIED_COUNT=$((APPLIED_COUNT + 1))
done

# ── Summary ──
echo ""
echo "=========================================="
echo "  Migration complete"
echo "  Applied: $APPLIED_COUNT"
echo "  Skipped: $SKIPPED_COUNT"
echo "  Errors:  $ERROR_COUNT"
if $DRY_RUN; then
    echo "  (dry run — no changes made)"
fi
echo "=========================================="

if [[ $ERROR_COUNT -gt 0 ]]; then
    exit 1
fi
