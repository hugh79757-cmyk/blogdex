#!/usr/bin/env bash
# =============================================================================
#  Blogdex 일회성/실험적 스크립트 아카이브
#
#  삭제하지는 않지만 더 이상 사용되지 않는 스크립트들을
#  cli/archive/ 디렉토리로 이동하여 보관합니다.
#
#  Usage:
#    bash scripts/archive_scripts.sh
#    bash scripts/archive_scripts.sh --dry-run    # 이동 대상만 출력
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVE_DIR="$PROJECT_DIR/cli/archive"

DRY_RUN=false
for arg in "$@"; do
    [ "$arg" = "--dry-run" ] && DRY_RUN=true
done

# ── 아카이브 대상 ──
# 각 줄: "설명|상대경로"
SCRIPTS=(
    "스팸 URL 정리 (일회성)|cli/spam_cleanup.py"
    "스팸 정리 변형 (중복)|cli/spam_cleanup2.py"
    "스팸 URL 인스펙션 (일회성)|cli/spam_inspect.py"
    "GA4 측정ID 삽입 (일회성)|cli/ga4_inject.py"
    "GA4 인젝션 변형 (중복)|cli/ga4_inject2.py"
    "GA4 속성 감사 (일회성)|cli/ga4_audit.py"
    "GA4 속성 정리 (일회성)|cli/ga4_cleanup.py"
    "GA4 측정ID 조회 (일회성)|cli/ga4_measurement_ids.py"
    "Google Indexing API 제출 (일회성)|cli/index_submit.py"
    "GSC 페이지별 백필 (실험적)|cli/gsc_backfill_pages.py"
)

# ── 존재하는 스크립트만 필터링 ──
EXISTING=()
for entry in "${SCRIPTS[@]}"; do
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    if [ -f "$full" ]; then
        EXISTING+=("$entry")
    fi
done

# ── 출력 ──
echo ""
echo "============================================"
echo "  Blogdex 스크립트 아카이브"
echo "  대상: cli/archive/"
echo "============================================"
echo ""

if [ ${#EXISTING[@]} -eq 0 ]; then
    echo "아카이브할 파일이 없습니다."
    exit 0
fi

echo "아카이브 대상 (${#EXISTING[@]}개):"
for entry in "${EXISTING[@]}"; do
    desc="${entry%%|*}"
    path="${entry#*|}"
    size=$(stat -f "%z" "$PROJECT_DIR/$path" 2>/dev/null || echo "?")
    echo "  📦 [$desc] $path ($size bytes)"
done

if $DRY_RUN; then
    echo ""
    echo "🟡 Dry-run 모드 — 실제 이동되지 않았습니다."
    exit 0
fi

echo ""
echo -n "위 파일들을 cli/archive/ 로 이동합니다. 계속하시겠습니까? (y/N) "
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "🚫 취소되었습니다."
    exit 0
fi

# ── README.md 생성 (처음 한 번) ──
README_PATH="$ARCHIVE_DIR/README.md"
if [ ! -f "$README_PATH" ]; then
    cat > "$README_PATH" << 'READMEEOF'
# Blogdex 아카이브 스크립트

이 디렉토리는 **일회성 실행** 또는 **실험적 기능**으로
더 이상 사용되지 않는 Python 스크립트를 보관합니다.

## 보관 사유

| 파일 | 사유 | 대체/비고 |
|------|------|-----------|
| `spam_cleanup.py` | 일회성 스팸 정리 작업 | 작업 완료 후 불필요 |
| `spam_cleanup2.py` | spam_cleanup.py의 변형 | 중복, 작업 완료 |
| `spam_inspect.py` | 스팸 URL 인스펙션 | 일회성 작업 |
| `ga4_inject.py` | Hugo 사이트 GA4 측정ID 삽입 | 이미 삽입 완료 |
| `ga4_inject2.py` | ga4_inject.py 변형 | 중복 |
| `ga4_audit.py` | GA4 속성 감사 | 감사 완료 |
| `ga4_cleanup.py` | GA4 속성 정리 | 정리 완료 |
| `ga4_measurement_ids.py` | GA4 측정ID 조회 | 일회성 조회 |
| `index_submit.py` | Google Indexing API 제출 | `daily_sync.py`에서 간헐적 호출 → 제거 검토 |
| `gsc_backfill_pages.py` | GSC 페이지별 백필 | 실험적, 미완료 |

## 복원 방법

```bash
git mv cli/archive/<filename>.py cli/<filename>.py
```

또는 직접 복사:

```bash
cp cli/archive/<filename>.py cli/<filename>.py
```

> 참고: 이 파일들은 삭제되지 않았습니다. 필요시 언제든 복원 가능합니다.
READMEEOF
    echo "  📝 README.md 생성 완료"
fi

# ── 이동 실행 ──
MOVED=0
for entry in "${EXISTING[@]}"; do
    desc="${entry%%|*}"
    path="${entry#*|}"
    full="$PROJECT_DIR/$path"
    filename=$(basename "$full")
    dest="$ARCHIVE_DIR/$filename"

    if mv "$full" "$dest"; then
        echo "  ✅ 이동: $path → cli/archive/$filename"
        MOVED=$((MOVED + 1))
    else
        echo "  ❌ 실패: $path"
    fi
done

echo ""
echo "============================================"
echo "  아카이브 완료: $MOVED개 파일 이동"
echo "  보관 위치: cli/archive/"
echo "============================================"
