#!/usr/bin/env bash
# =============================================================================
#  Blogdex Cron Setup Script
#
#  Automatically detects the project path and Python virtual environment,
#  then adds a daily crontab entry for daily_sync.py.
#
#  Idempotent — running twice won't add duplicate cron entries.
#
#  Usage:
#    bash scripts/setup_cron.sh
#    bash scripts/setup_cron.sh --dry-run    # show what would be added
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

DRY_RUN=false
for arg in "$@"; do
    [ "$arg" = "--dry-run" ] && DRY_RUN=true
done

echo ""
echo "============================================"
echo "  Blogdex Cron 설정"
echo "  Project: $PROJECT_DIR"
echo "============================================"
echo ""

# ── 1. Python 경로 감지 ──
VENV_PATHS=(
    "$PROJECT_DIR/cli/venv/bin/python3"
    "$PROJECT_DIR/cli/venv/bin/python"
    "$PROJECT_DIR/venv/bin/python3"
    "$PROJECT_DIR/venv/bin/python"
    "$PROJECT_DIR/.venv/bin/python3"
    "$PROJECT_DIR/.venv/bin/python"
)

PYTHON=""
for p in "${VENV_PATHS[@]}"; do
    if [ -x "$p" ]; then
        PYTHON="$p"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    PYTHON="$(command -v python3 || true)"
    echo "  ⚠️   가상환경을 찾을 수 없습니다. 시스템 Python($PYTHON)을 사용합니다."
    echo "       (cli/venv/bin/python3, venv/bin/python3, .venv/bin/python3)"
else
    echo "  ✅ Python: $PYTHON"
fi

# ── 2. 로그 디렉토리 확인 ──
LOG_DIR="$PROJECT_DIR/logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo "  ✅ 로그 디렉토리 생성: $LOG_DIR"
else
    echo "  ✅ 로그 디렉토리: $LOG_DIR"
fi

# ── 3. cron 표현식 구성 ──
# 매일 새벽 1시 (UTC+0 → 한국 시간 오전 10시)
CRON_TIME="0 1 * * *"
CRON_CMD="cd $PROJECT_DIR && $PYTHON $PROJECT_DIR/cli/daily_sync.py >> $LOG_DIR/daily_sync.log 2>&1"
CRON_LINE="$CRON_TIME $CRON_CMD"
CRON_TAG="# blogdex-daily-sync"

echo ""
echo "  제안된 crontab 항목:"
echo ""
echo "    ┌─────────────────────────────────────────────"
echo "    │ $CRON_LINE"
echo "    │ $CRON_TAG"
echo "    └─────────────────────────────────────────────"
echo ""

# ── 4. 중복 확인 (tag 기준) ──
EXISTING_CRON=$(crontab -l 2>/dev/null || true)
if echo "$EXISTING_CRON" | grep -q "$CRON_TAG"; then
    echo "  ℹ️  이미 등록된 cron 항목이 있습니다 (tag: $CRON_TAG)"
    echo "     기존 항목:"
    echo "$EXISTING_CRON" | grep "$CRON_TAG"
    echo ""
    echo "  새로 추가하지 않고 종료합니다."
    echo "  (제거 후 재실행하려면: crontab -e 로 직접 수정)"
    exit 0
fi

if $DRY_RUN; then
    echo "🟡 Dry-run 모드 — crontab이 변경되지 않았습니다."
    exit 0
fi

# ── 5. 사용자 확인 ──
echo -n "위 crontab 항목을 추가할까요? (y/N) "
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "🚫 취소되었습니다."
    exit 0
fi

# ── 6. crontab 추가 ──
(crontab -l 2>/dev/null || true; echo "# $CRON_TAG"; echo "$CRON_LINE") | crontab -

echo ""
echo "  ✅ crontab 추가 완료!"

# ── 7. 검증 ──
echo ""
echo "  현재 crontab:"
echo "  ─────────────────────────────────────────────"
crontab -l | grep -v "^#" | grep -v "^$" || echo "  (항목 없음)"
echo "  ─────────────────────────────────────────────"
echo ""
echo "============================================"
echo "  완료! daily_sync.py가 매일 01:00에 실행됩니다."
echo "  로그: $LOG_DIR/daily_sync.log"
echo "============================================"
