#!/usr/bin/env python3
"""
Blogdex SyncMonitor — 구조화된 오류 추적 + 알림 모듈

사용법:
    from monitor import SyncMonitor, check_data_quality

    monitor = SyncMonitor(telegram_token="...", chat_id="...")
    monitor.record("gsc", "ok", "87사이트 수집 완료", {"count": 1234})
    monitor.record("ga4", "error", "API 타임아웃")
    monitor.send_daily_report()   # Telegram + console
    monitor.save_report()         # JSONL 파일

의존성: stdlib + requests (선택, Telegram 미사용시 불필요)
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

# ── 데이터 품질 기준 (예상 최소 수집 건수) ──
EXPECTED_MINIMUMS = {
    "gsc": 50,
    "ga4": 30,
    "bing": 5,
    "coupang": 1,
    "senior": 1,
}

# ── 리포트 파일 경로 ──
DEFAULT_REPORT_PATH = Path(__file__).parent.parent / "logs" / "sync_report.jsonl"


def check_data_quality(monitor: "SyncMonitor", step: str, count: int, expected_min: int = None):
    """
    데이터 품질 검사: 수집 건수가 예상치에 미달하면 경고/오류 기록.

    Args:
        monitor: SyncMonitor 인스턴스
        step: 스텝 이름 (예: "gsc", "ga4")
        count: 실제 수집 건수
        expected_min: 예상 최소 건수 (None이면 EXPECTED_MINIMUMS에서 조회)
    """
    if expected_min is None:
        expected_min = EXPECTED_MINIMUMS.get(step, 0)

    detail = f"수집 {count}건 (최소예상: {expected_min})"

    if count == 0:
        monitor.record(step, "error", f"{step}: {detail} — 데이터 없음, API 오류 가능성")
    elif count < expected_min:
        monitor.record(step, "warning", f"{step}: {detail} — 예상치보다 적음")
    else:
        monitor.record(step, "ok", f"{step}: {detail}")


class SyncMonitor:
    """
    동기화 파이프라인 모니터링.

    - 각 스텝의 성공/실패/경과 시간 기록
    - 실패 시 즉시 Telegram 알림
    - 종료 시 일일 리포트 전송
    - JSONL 파일로 영구 저장
    """

    def __init__(
        self,
        telegram_token: str = None,
        chat_id: str = None,
        report_path: str = None,
        pipeline_name: str = "Blogdex Daily Sync",
    ):
        self.results = {}
        self.step_times = {}
        self.start_time = datetime.now()
        self.pipeline_name = pipeline_name
        self.report_path = Path(report_path or DEFAULT_REPORT_PATH)

        # Telegram 설정 (선택)
        self.telegram_token = telegram_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        self._telegram_enabled = bool(self.telegram_token and self.chat_id)
        if not self._telegram_enabled:
            log.info("SyncMonitor: Telegram이 설정되지 않아 콘솔만 사용합니다.")

    # ── 스텝 기록 ────────────────────────────────────────────────────

    def record(self, step: str, status: str, message: str = "", data: dict = None):
        """
        스텝 실행 결과 기록.

        Args:
            step: 스텝 식별자 (예: "gsc", "ga4")
            status: "ok" | "warning" | "error" | "skipped"
            message: 사람이 읽을 수 있는 설명
            data: 추가 데이터 딕셔너리
        """
        elapsed = None
        if step in self.step_times:
            elapsed = (datetime.now() - self.step_times[step]).total_seconds()

        entry = {
            "status": status,
            "message": message,
            "data": data or {},
            "elapsed_seconds": elapsed,
            "timestamp": datetime.now().isoformat(),
        }
        self.results[step] = entry

        # 콘솔 출력
        icon = {"ok": "✅", "warning": "⚠️", "error": "❌", "skipped": "⏭️"}.get(status, "❓")
        elapsed_str = f" ({elapsed:.1f}초)" if elapsed else ""
        log.info(f"{icon} {step}: {message}{elapsed_str}")

        # 실패 시 즉시 알림
        if status == "error":
            self._send_immediate_alert(step, message)

    def start_step(self, step: str):
        """스텝 시작 시간 기록 (record()에서 elapsed 계산에 사용)"""
        self.step_times[step] = datetime.now()

    def total_elapsed(self) -> float:
        """전체 실행 시간 (초)"""
        return (datetime.now() - self.start_time).total_seconds()

    # ── Telegram 알림 ────────────────────────────────────────────────

    def _send_telegram(self, text: str):
        """로우레벨 Telegram 전송"""
        if not self._telegram_enabled:
            return
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
            }, timeout=10)
        except Exception as e:
            log.error(f"Telegram 전송 실패: {e}")

    def _send_immediate_alert(self, step: str, message: str):
        """실패 스텝 즉시 알림"""
        text = (
            f"🚨 <b>[Blogdex] {step} 실패</b>\n"
            f"{message}\n"
            f"{datetime.now():%Y-%m-%d %H:%M}"
        )
        self._send_telegram(text)

    # ── 일일 리포트 ──────────────────────────────────────────────────

    def send_daily_report(self, extra_lines: list = None):
        """
        일일 종합 리포트 전송 (Telegram + console).

        Args:
            extra_lines: 리포트 하단에 추가할 문자열 리스트
        """
        now = datetime.now()
        elapsed = self.total_elapsed()
        elapsed_str = f"{elapsed:.0f}초" if elapsed < 120 else f"{elapsed/60:.0f}분 {elapsed%60:.0f}초"

        STATUS_ICON = {"ok": "✅", "warning": "⚠️", "error": "❌", "skipped": "⏭️"}

        lines = [
            f"<b>📊 {self.pipeline_name} — {now.strftime('%Y-%m-%d')}</b>",
            "━" * 25,
        ]

        for step, r in self.results.items():
            icon = STATUS_ICON.get(r["status"], "❓")
            msg = r.get("message", "")
            elapsed_s = r.get("elapsed_seconds")
            time_str = f" ({elapsed_s:.0f}초)" if elapsed_s else ""
            lines.append(f"{icon} <b>{step}</b>: {msg}{time_str}")

        # 에러 요약
        errors = [(s, r) for s, r in self.results.items() if r["status"] == "error"]
        if errors:
            lines.append("")
            lines.append(f"<b>🚨 실패 ({len(errors)}개)</b>")
            for step, r in errors:
                lines.append(f"  ❌ {step}: {r.get('message', '')}")

        warnings = [(s, r) for s, r in self.results.items() if r["status"] == "warning"]
        if warnings:
            lines.append("")
            lines.append(f"<b>⚠️ 경고 ({len(warnings)}개)</b>")
            for step, r in warnings:
                lines.append(f"  ⚠️ {step}: {r.get('message', '')}")

        # 추가 라인
        if extra_lines:
            lines.extend(extra_lines)

        lines.extend(["", f"⏱ 총 소요: {elapsed_str}"])

        text = "\n".join(lines)

        # Telegram
        self._send_telegram(text)

        # Console fallback (plain text)
        print()
        print("=" * 55)
        print(f"  📊 {self.pipeline_name} — {now.strftime('%Y-%m-%d %H:%M')}")
        print("=" * 55)
        for step, r in self.results.items():
            icon = STATUS_ICON.get(r["status"], "❓")
            msg = r.get("message", "")
            elapsed_s = r.get("elapsed_seconds")
            time_str = f" ({elapsed_s:.0f}초)" if elapsed_s else ""
            print(f"  {icon} {step}: {msg}{time_str}")
        print(f"  ⏱ 총 소요: {elapsed_str}")
        print("=" * 55)

    # ── 영구 저장 ────────────────────────────────────────────────────

    def save_report(self, path: str = None):
        """
        JSONL 형식으로 리포트 저장 (한 줄 = 한 번의 실행).

        Args:
            path: 저장 경로 (기본: logs/sync_report.jsonl)
        """
        save_path = Path(path or self.report_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().isoformat(),
            "pipeline": self.pipeline_name,
            "elapsed_seconds": round(self.total_elapsed(), 1),
            "steps": self.results,
            "summary": {
                "total": len(self.results),
                "ok": sum(1 for r in self.results.values() if r["status"] == "ok"),
                "warning": sum(1 for r in self.results.values() if r["status"] == "warning"),
                "error": sum(1 for r in self.results.values() if r["status"] == "error"),
                "skipped": sum(1 for r in self.results.values() if r["status"] == "skipped"),
            },
        }

        with open(save_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(report, ensure_ascii=False, default=str) + "\n")

        log.info(f"리포트 저장: {save_path}")
