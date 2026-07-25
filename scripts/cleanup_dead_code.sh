#!/usr/bin/env bash
# =============================================================================
#  Blogdex 데드코드 정리 스크립트
#
#  안전하게 삭제할 수 있는 백업 파일, 로그 파일, 일회성 산출물을 제거합니다.
#  실행 전 dry-run 목록을 출력하고 사용자 확인을 받습니다.
#
#  Usage:
#    bash scripts/cleanup_dead_code.sh
#    bash scripts/cleanup_dead_code.sh --dry-run    # 목록만 출력
#    bash scripts/cleanup_dead_code.sh --force      # 확인 생략
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/cleanup_log_$(date +%Y%m%d).txt"

DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --force)   FORCE=true ;;
    esac
done

# ── 삭제 대상 파일 목록 ──────────────────────────────────────────────
# 각 줄: "설명|경로"
TARGETS=(
    # .bak 백업 파일 (원본이 존재하므로 안전)
    "bak|cli/daily_sync.py.bak"
    "bak|cli/daily_sync.py.bak.20260322_102200"
    "bak|cli/daily_sync.py.bak.20260516_075354"
    "bak|cli/gsc.py.bak"
    "bak|cli/gsc_detail.py.bak"
    "bak|cli/google_auth.py.bak"
    "bak|cli/perf.py.bak"
    "bak|cli/find_best_blog.py.bak"
    "bak|cli/index_submit.py.bak"
    "bak|cli/publish_config.yaml.bak"
    # pickle 토큰 백업 (JSON 마이그레이션 완료)
    "token-bak|cli/google_token.pickle.bak"
    "token-bak|cli/google_token.pickle.bak2"
    "token-bak|cli/google_token.pickle.bak.20260319"
    # 패치 파일
    "patch|cli/daily_sync.py.patch"
    # 배포 결과 로그
    "log|cli/deploy_ga4_result.txt"
    "log|cli/deploy_v2_result.txt"
    "log|cli/deploy_v3_result.txt"
    "log|cli/ga4_audit_result.txt"
    "log|cli/ga4_inject_result.txt"
    "log|cli/ga4_inject2_result.txt"
    "log|cli/ga4_measurement_ids_result.txt"
    "log|cli/redeploy_result.txt"
    "log|cli/redeploy2_result.txt"
    "log|cli/backfill2.log"
    # 스팸 리포트 (일회성 산출물)
    "report|cli/spam_report.json"
    "report|cli/spam_urls_for_removal.txt"
    # 프로젝트 루트 백업 스크립트/덤프
    "backup|backup2.py"
    "backup|backup3.py"
    "backup|backup3 2.py"
    "backup|backup_20260227_134358.txt"
    "backup|backup_20260228_085016.txt"
    "backup|backup_20260325_135408.txt"
)

# ── 삭제 대상 디렉토리 목록 ───────────────────────────────────────────
DIR_TARGETS=(
    "snapshots_backup|cli/snapshots_backup"
    "empty_backup|cli/snapshots/empty_backup"
)

# ── 존재하는 파일만 필터링 ─────────────────────────────────────────────
EXISTING_FILES=()
for entry in "${TARGETS[@]}"; do
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    if [ -f "$full" ]; then
        EXISTING_FILES+=("$entry")
    fi
done

EXISTING_DIRS=()
for entry in "${DIR_TARGETS[@]}"; do
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    if [ -d "$full" ]; then
        EXISTING_DIRS+=("$entry")
    fi
done

# ── Dry-run / 삭제 목록 출력 ──────────────────────────────────────────
echo ""
echo "============================================"
echo "  Blogdex 데드코드 정리"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "============================================"
echo ""

if [ ${#EXISTING_FILES[@]} -eq 0 ] && [ ${#EXISTING_DIRS[@]} -eq 0 ]; then
    echo "삭제할 파일이 없습니다."
    exit 0
fi

echo "삭제 대상 파일 (${#EXISTING_FILES[@]}개):"
echo "----------------------------------------------"
for entry in "${EXISTING_FILES[@]}"; do
    desc="${entry%%|*}"
    path="${entry#*|}"
    size=$(stat -f "%z" "$PROJECT_DIR/$path" 2>/dev/null || echo "?")
    printf "  [%s] %s (%s bytes)\n" "$desc" "$path" "$size"
done

if [ ${#EXISTING_DIRS[@]} -gt 0 ]; then
    echo ""
    echo "삭제 대상 디렉토리 (${#EXISTING_DIRS[@]}개):"
    echo "----------------------------------------------"
    for entry in "${EXISTING_DIRS[@]}"; do
        path="${entry#*|}"
        file_count=$(find "$PROJECT_DIR/$path" -type f 2>/dev/null | wc -l | tr -d ' ')
        echo "  [dir] $path (${file_count}개 파일)"
    done
fi

# ── Dry-run 모드면 여기서 종료 ─────────────────────────────────────────
if $DRY_RUN; then
    echo ""
    echo "🟡 Dry-run 모드 — 실제 삭제되지 않았습니다."
    exit 0
fi

# ── 사용자 확인 ────────────────────────────────────────────────────────
if ! $FORCE; then
    echo ""
    echo -n "위 파일들을 삭제합니다. 계속하시겠습니까? (y/N) "
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "🚫 취소되었습니다."
        exit 0
    fi
fi

# ── 실제 삭제 실행 ─────────────────────────────────────────────────────
DELETED_COUNT=0
ERROR_COUNT=0

# 로그 파일 초기화
echo "Cleanup log - $(date '+%Y-%m-%d %H:%M:%S')" > "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# 파일 삭제
for entry in "${EXISTING_FILES[@]}"; do
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    if rm "$full"; then
        echo "  ✅ 삭제: $path"
        echo "DELETED: $path ($(stat -f "%z" "$full" 2>/dev/null || echo "?"))" >> "$LOG_FILE"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    else
        echo "  ❌ 실패: $path"
        echo "FAILED: $path" >> "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done

# 디렉토리 삭제
for entry in "${EXISTING_DIRS[@]}":; do
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    file_count=$(find "$full" -type f 2>/dev/null | wc -l | tr -d ' ')
    if rm -rf "$full"; then
        echo "  ✅ 삭제: $path/ (${file_count}개 파일)"
        echo "DELETED_DIR: $path/ (${file_count} files)" >> "$LOG_FILE"
        DELETED_COUNT=$((DELETED_COUNT + 1))
    else
        echo "  ❌ 실패: $path/"
        echo "FAILED_DIR: $path/" >> "$LOG_FILE"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
done

# ── 요약 ──────────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  정리 완료"
echo "  삭제: $DELETED_COUNT개"
echo "  실패: $ERROR_COUNT개"
echo "  로그: $LOG_FILE"
echo "============================================"
