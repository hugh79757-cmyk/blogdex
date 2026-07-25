#!/usr/bin/env python3
"""
Blogdex Health Check

Checks core system health: API reachability, env vars, token files,
log freshness, and data presence. Suitable for monitoring or Telegram alerting.

Usage:
    python scripts/health_check.py
    python scripts/health_check.py --verbose

Exit code: 0 = all pass, 1 = any fail
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("  ❌ [DEP] requests 라이브러리가 필요합니다: pip install requests")
    sys.exit(1)

# ── ANSI 색상 ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── 설정 ──
PROJECT_DIR = Path(__file__).resolve().parent.parent

# Health check configuration (can be overridden via env vars)
API_URL = os.environ.get(
    "BLOGDEX_API_URL",
    "https://blogdex-api.hugh79757.workers.dev"
)
API_KEY = os.environ.get("BLOGDEX_API_KEY", "")

REQUIRED_ENV_VARS = [
    "BLOGDEX_API_KEY",
]

OPTIONAL_ENV_VARS = [
    ("TELEGRAM_BOT_TOKEN", "Telegram 알림"),
    ("TELEGRAM_CHAT_ID", "Telegram 채팅 ID"),
    ("NAVER_CLIENT_ID", "네이버 API (노인복지)"),
    ("NAVER_CLIENT_SECRET", "네이버 API 시크릿"),
    ("OPENAI_API_KEY", "AI 타이틀 생성"),
]

TOKEN_FILES = [
    "credentials/token_1_twinssn.json",
    "credentials/token_2_informationhot.json",
    "credentials/token_3_aikorea24.json",
]

LOG_PATHS = [
    PROJECT_DIR / "logs" / "daily_sync.log",
]

# Try cli/logs/ as well (for daily_sync.py's per-date logs)
CLI_LOG_DIR = PROJECT_DIR / "cli" / "logs"
if CLI_LOG_DIR.exists():
    log_files = sorted(CLI_LOG_DIR.glob("daily_sync_*.log"))
    if log_files:
        LOG_PATHS.append(log_files[-1])


def ok(msg):
    print(f"  {GREEN}✅{RESET} {msg}")


def fail(msg):
    print(f"  {RED}❌{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}⚠️{RESET} {msg}")


def main():
    parser = argparse.ArgumentParser(description="Blogdex Health Check")
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    args = parser.parse_args()

    all_pass = True

    print()
    print(f"{BOLD}============================================{RESET}")
    print(f"{BOLD}  Blogdex Health Check{RESET}")
    print(f"{BOLD}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}============================================{RESET}")
    print()

    # ── 1. API Reachability ──
    print(f"{CYAN}[1/5] API 연결{RESET}")
    if not API_KEY:
        fail("BLOGDEX_API_KEY 환경변수가 설정되지 않음 (스킵)")
        if args.verbose:
            warn("  .env 파일에서 키를 설정하거나 export BLOGDEX_API_KEY=... 실행")
        # Don't mark as fail — API key is a separate check
    else:
        try:
            r = requests.get(
                f"{API_URL}/dashboard/summary",
                headers={"X-API-Key": API_KEY},
                timeout=10,
            )
            if r.status_code == 200:
                ok(f"API 응답: {API_URL}/dashboard/summary (200)")
                if args.verbose:
                    data = r.json()
                    warn(f"  blogs={data.get('blogs')}, posts={data.get('posts')}, "
                         f"gsc_clicks={data.get('gsc_clicks')}")
            elif r.status_code == 401:
                fail(f"API 인증 실패 (401): BLOGDEX_API_KEY 불일치")
                all_pass = False
            else:
                fail(f"API 응답 코드: {r.status_code}")
                all_pass = False
        except requests.exceptions.ConnectionError:
            fail(f"API 연결 실패: {API_URL}")
            all_pass = False
        except requests.exceptions.Timeout:
            fail(f"API 타임아웃 (10초): {API_URL}")
            all_pass = False
        except Exception as e:
            fail(f"API 요청 실패: {e}")
            all_pass = False

    print()

    # ── 2. Environment Variables ──
    print(f"{CYAN}[2/5] 환경변수{RESET}")
    for var in REQUIRED_ENV_VARS:
        val = os.environ.get(var)
        if val and "your_key" not in val and "여기에" not in val:
            ok(f"{var} 설정됨")
        else:
            fail(f"{var} 누락 또는 기본값")
            all_pass = False

    if args.verbose:
        for var, desc in OPTIONAL_ENV_VARS:
            val = os.environ.get(var)
            if val and "your" not in val and "여기" not in val:
                ok(f"{var} ({desc}) 설정됨")
            else:
                warn(f"{var} ({desc}) 미설정 — 선택 사항")

    print()

    # ── 3. Token Files ──
    print(f"{CYAN}[3/5] OAuth 토큰 파일{RESET}")
    found_any = False
    for rel_path in TOKEN_FILES:
        full = PROJECT_DIR / rel_path
        if full.exists():
            size = full.stat().st_size
            ok(f"{rel_path} ({size:,} bytes)")
            found_any = True
        else:
            warn(f"{rel_path} 없음")

    if not found_any:
        fail("OAuth 토큰 파일이 없습니다. cli/migrate_tokens.py 또는 google_auth.py 실행 필요")
        all_pass = False
    print()

    # ── 4. Log Freshness ──
    print(f"{CYAN}[4/5] 로그 최신성{RESET}")
    now = datetime.now()
    found_recent = False
    for log_path in LOG_PATHS:
        if log_path.exists():
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
            age = (now - mtime).total_seconds()
            hours_ago = age / 3600
            if hours_ago <= 25:
                ok(f"{log_path.name} 최종 수정: {mtime.strftime('%Y-%m-%d %H:%M')} ({hours_ago:.0f}시간 전)")
                found_recent = True
            else:
                warn(f"{log_path.name} 수정: {mtime.strftime('%Y-%m-%d %H:%M')} ({hours_ago:.0f}시간 전, 25시간 초과)")
        else:
            warn(f"{log_path} 없음")

    if not found_recent:
        fail("최근 25시간 이내의 로그 파일 없음 — daily_sync.py가 실행되지 않았을 수 있음")
        all_pass = False
    print()

    # ── 5. Data Freshness (D1에 오늘 데이터가 있는지) ──
    print(f"{CYAN}[5/5] 데이터 최신성 (D1){RESET}")
    if API_KEY:
        try:
            r = requests.get(
                f"{API_URL}/gsc/daily?days=1",
                headers={"X-API-Key": API_KEY},
                timeout=10,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]
                    ok(f"GSC 데이터: {len(data)}개 사이트, 최신일자={latest.get('date', '?')}")
                else:
                    warn("GSC 데이터 없음 (최근 1일)")
            else:
                warn(f"GSC API 응답: {r.status_code}")
        except Exception as e:
            warn(f"GSC 데이터 조회 실패: {e}")
    else:
        warn("API 키 없음 — 스킵")

    print()

    # ── 요약 ──
    if all_pass:
        print(f"{GREEN}{BOLD}✅ 모든 검사 통과{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}❌ 일부 검사 실패{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
