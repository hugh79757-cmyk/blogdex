#!/usr/bin/env python3
"""
Blogdex Sync Report Parser

Reads logs/sync_report.jsonl (JSONL format) and shows run summaries.

Usage:
    python scripts/parse_sync_report.py            # last 10 runs
    python scripts/parse_sync_report.py --last 7   # last 7 runs
    python scripts/parse_sync_report.py --failures # show only failed runs
    python scripts/parse_sync_report.py --watch    # follow mode (tail -f)
    python scripts/parse_sync_report.py --json     # raw JSON output

Dependencies: stdlib only
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPORT_PATH = Path(__file__).resolve().parent.parent / "logs" / "sync_report.jsonl"

STATUS_COLORS = {
    "ok": "\033[92m",       # green
    "warning": "\033[93m",  # yellow
    "error": "\033[91m",    # red
    "skipped": "\033[90m",  # gray
}
RESET = "\033[0m"


def load_reports(path: Path) -> list[dict]:
    """JSONL 파일에서 모든 리포트 로드"""
    if not path.exists():
        print(f"리포트 파일 없음: {path}")
        return []
    reports = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                reports.append(json.loads(line))
    return reports


def print_run_header(run: dict, index: int):
    """개별 실행 헤더 출력"""
    date = run.get("date", "?")
    time_str = run.get("time", "?")[11:19] if run.get("time") else "?"
    elapsed = run.get("elapsed_seconds", 0)
    summary = run.get("summary", {})
    total = summary.get("total", 0)
    ok_count = summary.get("ok", 0)
    warn_count = summary.get("warning", 0)
    err_count = summary.get("error", 0)
    skip_count = summary.get("skipped", 0)

    # 전체 상태
    if err_count > 0:
        status_icon = f"{STATUS_COLORS['error']}❌{RESET}"
    elif warn_count > 0:
        status_icon = f"{STATUS_COLORS['warning']}⚠️{RESET}"
    else:
        status_icon = f"{STATUS_COLORS['ok']}✅{RESET}"

    elapsed_str = f"{elapsed:.0f}s" if elapsed < 120 else f"{elapsed/60:.0f}m{elapsed%60:.0f}s"

    print(f"\n{status_icon} #{index} {date} {time_str} ({elapsed_str})")
    print(f"   총 {total}개 스텝: "
          f"{STATUS_COLORS['ok']}{ok_count}✅{RESET} "
          f"{STATUS_COLORS['warning']}{warn_count}⚠️{RESET} "
          f"{STATUS_COLORS['error']}{err_count}❌{RESET} "
          f"{STATUS_COLORS['skipped']}{skip_count}⏭️{RESET}")

    # 각 스텝 상세
    steps = run.get("steps", {})
    for step_name, step_data in steps.items():
        status = step_data.get("status", "?")
        msg = step_data.get("message", "")
        elapsed_s = step_data.get("elapsed_seconds")
        color = STATUS_COLORS.get(status, "")
        icon = {"ok": "✅", "warning": "⚠️", "error": "❌", "skipped": "⏭️"}.get(status, "❓")
        time_str = f" ({elapsed_s:.0f}s)" if elapsed_s else ""
        print(f"   {color}{icon} {step_name}: {msg}{time_str}{RESET}")


def check_consecutive_failures(reports: list[dict], threshold: int = 3) -> list:
    """연속 실패 감지: 특정 스텝이 threshold회 이상 연속 실패"""
    failures = {}
    for run in reports:
        steps = run.get("steps", {})
        for step_name, step_data in steps.items():
            status = step_data.get("status", "")
            if status == "error":
                if step_name not in failures:
                    failures[step_name] = {"count": 0, "last_date": run.get("date", "?")}
                failures[step_name]["count"] += 1
                failures[step_name]["last_date"] = run.get("date", "?")
            else:
                # 연속 실패 끊김 → 카운트 리셋
                if step_name in failures and status == "ok":
                    del failures[step_name]

    return {k: v for k, v in failures.items() if v["count"] >= threshold}


def main():
    parser = argparse.ArgumentParser(
        description="Blogdex Sync Report Parser"
    )
    parser.add_argument(
        "--last", "-n", type=int, default=10,
        help="표시할 최근 실행 수 (기본: 10)"
    )
    parser.add_argument(
        "--failures", action="store_true",
        help="실패한 실행만 표시"
    )
    parser.add_argument(
        "--watch", "-f", action="store_true",
        help="파일 끝에서 대기하며 새 리포트 감시"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Raw JSON 출력"
    )
    parser.add_argument(
        "--consecutive", type=int, metavar="N", default=3,
        help="연속 실패 임계값 (기본: 3)"
    )
    args = parser.parse_args()

    reports = load_reports(REPORT_PATH)

    if not reports:
        sys.exit(0)

    if args.json:
        selected = reports[-args.last:]
        print(json.dumps(selected, ensure_ascii=False, indent=2))
        sys.exit(0)

    # ── 연속 실패 감지 ──
    consecutive_fails = check_consecutive_failures(reports, args.consecutive)
    if consecutive_fails:
        print(f"\n{'=' * 55}")
        print(f"  🚨 연속 실패 감지 ({args.consecutive}회 이상)")
        print(f"{'=' * 55}")
        for step, info in sorted(consecutive_fails.items()):
            print(f"  ❌ {step}: {info['count']}회 연속 실패 (마지막: {info['last_date']})")
        print()

    # ── 필터링 ──
    if args.failures:
        reports = [r for r in reports
                   if r.get("summary", {}).get("error", 0) > 0]

    selected = reports[-args.last:]

    if not selected:
        print("조건에 맞는 실행 없음")
        sys.exit(0)

    # ── 출력 ──
    print(f"\n{'=' * 55}")
    print(f"  Blogdex Sync Report ({len(selected)} runs / {len(reports)} total)")
    print(f"  File: {REPORT_PATH}")
    print(f"{'=' * 55}")

    for i, run in enumerate(reversed(selected), 1):
        print_run_header(run, len(reports) - selected.index(run))

    # ── watch 모드 ──
    if args.watch:
        try:
            last_size = REPORT_PATH.stat().st_size
            while True:
                time.sleep(2)
                current_size = REPORT_PATH.stat().st_size
                if current_size > last_size:
                    with open(REPORT_PATH, "r", encoding="utf-8") as f:
                        f.seek(last_size)
                        new_lines = f.readlines()
                    for line in new_lines:
                        if line.strip():
                            run = json.loads(line)
                            print_run_header(run, "new")
                    last_size = current_size
        except KeyboardInterrupt:
            print("\n종료")


if __name__ == "__main__":
    main()
