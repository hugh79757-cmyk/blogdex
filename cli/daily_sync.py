#!/usr/bin/env python3
"""Blogdex 일일 자동 동기화 파이프라인
매일 1회 실행: GSC 스냅샷 + GA4 페이지뷰 수집 → D1 업로드 → sync_log 기록 → 텔레그램 알림
"""

import os
import sys
import re
import json
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 경로 설정
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR.parent / ".env")  # 루트 .env (Bing, OpenAI 등)
load_dotenv(PROJECT_DIR / ".env")          # cli/.env (텔레그램 등)

from config import API_URL, API_KEY
from google_auth import get_credentials
from googleapiclient.discovery import build

# 로깅 설정
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"daily_sync_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# API 설정
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
SNAPSHOT_DIR = PROJECT_DIR / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# 텔레그램 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# GSC 사이트 목록
SITES = [
    "https://5.informationhot.kr/",
    "https://65.informationhot.kr/",
    "https://informationhot.kr/",
    "https://kuta.informationhot.kr/",
    "https://stock.informationhot.kr/",
    "https://ud.informationhot.kr/",
    "https://techpawz.com/",
    "https://issue.techpawz.com/",
    "https://2.techpawz.com/",
    "https://info.techpawz.com/",
    "https://zodiac.techpawz.com/",
    "https://rotcha.kr/",
    "https://hotissue.rotcha.kr/",
    "https://travel.rotcha.kr/",
    "https://mimdiomcat.tistory.com/",
    "https://foodwater.tistory.com/",
    "https://achaanstree.tistory.com/",
]

# GA4 속성
GA4_PROPERTIES = {
    "407313218": "techpawz.com",
    "502482181": "info.techpawz.com",
    "521925869": "biz.techpawz.com",
    "440341812": "funstaurant.techpawz.com",
    "407323015": "rotcha.kr",
    "520232186": "hotissue.rotcha.kr",
    "446560416": "kay.rotcha.kr",
    "407690954": "ji.rotcha.kr",
    "422161800": "hero.rotcha.kr",
    "428914171": "ri.rotcha.kr",
    "430520851": "ro.rotcha.kr",
    "449396830": "no.rotcha.kr",
    "437300791": "5.informationhot.kr",
    "502932448": "65.informationhot.kr",
    "519652505": "informationhot.kr",
    "469316517": "kuta.informationhot.kr",
    "490284742": "ud.informationhot.kr",
    "518365064": "stock.informationhot.kr",
    "518766137": "8.informationhot.kr",
    "510545640": "issuetwinkle-tv.informationhot.kr",
    "520033547": "simprotection.informationhot.kr",
    "520495436": "tv-show.informationhot.kr",
    "489950024": "mimdiomcat.tistory.com",
    "407673873": "achaanstree.tistory.com",
    "407723312": "foodwater.tistory.com",
}

# Bing Webmaster API 키 (계정별)
BING_KEYS = []
for suffix in ["", "_2", "_3"]:
    key = os.getenv(f"BING_API_KEY{suffix}")
    account = os.getenv(f"BING_ACCOUNT{suffix}")
    if key and "여기" not in key:
        BING_KEYS.append({"account": account or f"account{suffix}", "api_key": key})


def api_post(path, data):
    try:
        r = requests.post(f"{API_URL}{path}", headers=HEADERS, json=data, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"API POST {path} 실패: {e}")
        return {"error": str(e)}


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("텔레그램 설정 없음, 알림 스킵")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        log.error(f"텔레그램 전송 실패: {e}")


def sync_bing():
    """Bing Webmaster API에서 키워드/트래픽 데이터 수집"""
    log.info("=== Bing 동기화 시작 ===")

    if not BING_KEYS:
        log.warning("Bing API 키 없음, 스킵")
        return {"status": "skipped", "row_count": 0}

    total_sites = 0
    total_keywords = 0
    all_daily = []
    all_keywords = []

    for bk in BING_KEYS:
        account = bk["account"]
        api_key = bk["api_key"]
        log.info(f"  계정: {account}")

        # 사이트 목록 조회
        try:
            r = requests.get(
                f"https://ssl.bing.com/webmaster/api.svc/json/GetUserSites?apikey={api_key}",
                timeout=15
            )
            sites = r.json().get("d", [])
        except Exception as e:
            log.error(f"  사이트 목록 실패: {e}")
            continue

        for site_info in sites:
            site_url = site_info.get("Url", "")
            name = site_url.replace("https://", "").replace("http://", "").rstrip("/")
            total_sites += 1

            # 트래픽 통계
            try:
                r = requests.get(
                    f"https://ssl.bing.com/webmaster/api.svc/json/GetRankAndTrafficStats?siteUrl={site_url}&apikey={api_key}",
                    timeout=15
                )
                stats = r.json().get("d", [])
                for s in stats[-7:]:  # 최근 7일치만
                    ts = int(re.search(r"\d+", s["Date"]).group()) / 1000
                    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    all_daily.append({
                        "site": name, "date": date_str, "source": "bing",
                        "clicks": s.get("Clicks", 0),
                        "impressions": s.get("Impressions", 0),
                    })
            except Exception as e:
                log.error(f"  {name} 트래픽: {e}")

            # 키워드 통계
            try:
                r = requests.get(
                    f"https://ssl.bing.com/webmaster/api.svc/json/GetQueryStats?siteUrl={site_url}&apikey={api_key}",
                    timeout=15
                )
                keywords = r.json().get("d", [])
                for kw in keywords[-100:]:  # 최근 100건
                    ts = int(re.search(r"\d+", kw["Date"]).group()) / 1000
                    date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    all_keywords.append({
                        "site": name, "date": date_str, "source": "bing",
                        "query": kw.get("Query", ""),
                        "clicks": kw.get("Clicks", 0),
                        "impressions": kw.get("Impressions", 0),
                        "ctr": round(kw.get("Clicks", 0) / max(kw.get("Impressions", 1), 1) * 100, 2),
                        "position": round(kw.get("AvgImpressionPosition", 0), 1),
                    })
                    total_keywords += 1
                log.info(f"    {name}: 키워드 {len(keywords[-100:])}건")
            except Exception as e:
                log.error(f"  {name} 키워드: {e}")

    # D1 업로드 — Bing 전용 테이블에 저장
    if all_daily:
        for i in range(0, len(all_daily), 100):
            batch = all_daily[i:i+100]
            api_post("/bing/daily", {"rows": batch})

    if all_keywords:
        for i in range(0, len(all_keywords), 30):
            batch = all_keywords[i:i+30]
            api_post("/bing/keywords", {"keywords": batch})

    log.info(f"Bing 완료: {total_sites}개 사이트, {total_keywords}개 키워드")

    return {
        "status": "ok", "date": datetime.now().strftime("%Y-%m-%d"),
        "sites": total_sites, "row_count": total_keywords
    }


def sync_gsc():
    """GSC 데이터 수집 → 로컬 스냅샷 + D1 업로드"""
    log.info("=== GSC 동기화 시작 ===")

    end = datetime.now() - timedelta(days=2)
    date_str = end.strftime("%Y-%m-%d")
    snapshot_file = SNAPSHOT_DIR / f"gsc_{date_str}.json"

    if snapshot_file.exists():
        log.info(f"{date_str} 스냅샷 이미 존재, 스킵")
        return {"status": "skipped", "date": date_str, "row_count": 0}

    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)

    snapshot = {"date": date_str, "collected_at": datetime.now().isoformat(), "sites": {}}
    total_clicks = 0
    total_impressions = 0
    total_keywords = 0
    d1_daily_rows = []
    d1_keyword_rows = []

    for site_url in SITES:
        name = site_url.replace("https://", "").rstrip("/")
        try:
            resp = service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    "startDate": date_str,
                    "endDate": date_str,
                    "dimensions": ["query", "page"],
                    "rowLimit": 500,
                }
            ).execute()

            rows = resp.get("rows", [])
            clicks = sum(r["clicks"] for r in rows)
            impressions = sum(r["impressions"] for r in rows)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0

            total_clicks += clicks
            total_impressions += impressions

            # D1 일별 요약
            d1_daily_rows.append({
                "site": name, "date": date_str,
                "clicks": clicks, "impressions": impressions,
                "ctr": round(ctr, 2)
            })

            # 키워드 데이터
            keywords = []
            sorted_rows = sorted(rows, key=lambda r: r["impressions"], reverse=True)[:100]
            for row in sorted_rows:
                kw = {
                    "query": row["keys"][0],
                    "page": row["keys"][1] if len(row["keys"]) > 1 else "",
                    "clicks": int(row["clicks"]),
                    "impressions": int(row["impressions"]),
                    "ctr": round(row["ctr"] * 100, 2),
                    "position": round(row["position"], 1)
                }
                keywords.append(kw)
                d1_keyword_rows.append({
                    "site": name, "date": date_str,
                    "query": kw["query"], "clicks": kw["clicks"],
                    "impressions": kw["impressions"],
                    "ctr": kw["ctr"], "position": kw["position"]
                })

            total_keywords += len(keywords)
            snapshot["sites"][name] = {
                "clicks": clicks, "impressions": impressions,
                "ctr": round(ctr, 2), "top_keywords": keywords
            }
            log.info(f"  {name}: 클릭 {clicks}, 노출 {impressions}, 키워드 {len(keywords)}")

        except Exception as e:
            snapshot["sites"][name] = {"error": str(e)}
            log.error(f"  {name}: {e}")

    snapshot["total"] = {
        "clicks": total_clicks, "impressions": total_impressions,
        "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2)
    }

    # 로컬 스냅샷 저장
    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    log.info(f"스냅샷 저장: {snapshot_file}")

    # D1 업로드
    if d1_daily_rows:
        for row in d1_daily_rows:
            api_post("/gsc/daily", row)

    if d1_keyword_rows:
        for i in range(0, len(d1_keyword_rows), 100):
            batch = d1_keyword_rows[i:i+100]
            api_post("/gsc/keywords", {"keywords": batch})

    log.info(f"GSC 완료: 클릭 {total_clicks}, 노출 {total_impressions}, 키워드 {total_keywords}")

    return {
        "status": "ok", "date": date_str,
        "clicks": total_clicks, "impressions": total_impressions,
        "row_count": total_keywords
    }


def sync_ga4(days=3):
    """GA4 페이지뷰 수집 → D1 업로드"""
    log.info("=== GA4 동기화 시작 ===")

    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric

    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    all_data = []
    total_pv = 0
    total_rev = 0.0

    for prop_id, domain in GA4_PROPERTIES.items():
        try:
            request = RunReportRequest(
                property=f"properties/{prop_id}",
                date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
                dimensions=[Dimension(name="pagePath"), Dimension(name="date")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="totalAdRevenue"),
                ],
                limit=10000,
            )
            response = client.run_report(request=request)
            site_pv = 0
            site_rev = 0.0
            for row in response.rows:
                path = row.dimension_values[0].value
                date = row.dimension_values[1].value
                date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                pageviews = int(row.metric_values[0].value)
                sessions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value)
                all_data.append({
                    "site": domain, "date": date_fmt,
                    "page": f"https://{domain}{path}",
                    "pageviews": pageviews, "sessions": sessions,
                    "revenue": round(revenue, 6),
                })
                site_pv += pageviews
                site_rev += revenue
            total_pv += site_pv
            total_rev += site_rev
            log.info(f"  {domain}: {site_pv:,} PV, ${site_rev:.2f}")
        except Exception as e:
            log.error(f"  {domain}: {e}")

    # D1 업로드
    if all_data:
        for i in range(0, len(all_data), 500):
            batch = all_data[i:i+500]
            api_post("/ga4/pageviews", {"data": batch})

    log.info(f"GA4 완료: {len(all_data)}건, {total_pv:,} PV, ${total_rev:.2f}")

    return {
        "status": "ok", "date_range": f"{start_str}~{end_str}",
        "row_count": len(all_data), "total_pv": total_pv,
        "total_rev": round(total_rev, 2)
    }


def record_sync_log(source, result, site=None):
    """sync_log에 수집 결과 기록"""
    api_post("/sync/log", {
        "source": source,
        "site": site,
        "last_synced_at": datetime.now().isoformat(),
        "last_date_covered": result.get("date") or result.get("date_range"),
        "row_count": result.get("row_count", 0),
        "status": result.get("status", "ok"),
        "message": json.dumps({k: v for k, v in result.items() if k not in ("status", "row_count")}, ensure_ascii=False)
    })


def main():
    start_time = datetime.now()
    log.info("=" * 50)
    log.info("Blogdex 일일 동기화 시작")
    log.info("=" * 50)

    results = {}

    # GSC 동기화
    try:
        gsc_result = sync_gsc()
        results["gsc"] = gsc_result
        record_sync_log("gsc", gsc_result)
    except Exception as e:
        log.error(f"GSC 동기화 실패: {e}")
        results["gsc"] = {"status": "error", "message": str(e)}
        record_sync_log("gsc", {"status": "error", "row_count": 0, "date": "N/A"})

    # GA4 동기화
    try:
        ga4_result = sync_ga4(days=3)
        results["ga4"] = ga4_result
        record_sync_log("ga4", ga4_result)
    except Exception as e:
        log.error(f"GA4 동기화 실패: {e}")
        results["ga4"] = {"status": "error", "message": str(e)}
        record_sync_log("ga4", {"status": "error", "row_count": 0, "date": "N/A"})

    # Bing 동기화
    try:
        bing_result = sync_bing()
        results["bing"] = bing_result
        record_sync_log("bing", bing_result)
    except Exception as e:
        log.error(f"Bing 동기화 실패: {e}")
        results["bing"] = {"status": "error", "message": str(e)}
        record_sync_log("bing", {"status": "error", "row_count": 0, "date": "N/A"})

    # 소요 시간
    elapsed = (datetime.now() - start_time).total_seconds()
    log.info(f"완료: {elapsed:.1f}초 소요")

    # 텔레그램 알림
    gsc = results.get("gsc", {})
    ga4 = results.get("ga4", {})
    msg_lines = [
        "<b>📊 Blogdex 일일 리포트</b>",
        "",
        f"<b>GSC</b> ({gsc.get('date', 'N/A')})",
        f"  상태: {gsc.get('status', 'unknown')}",
    ]
    if gsc.get("status") == "ok":
        msg_lines.append(f"  클릭: {gsc.get('clicks', 0):,} | 노출: {gsc.get('impressions', 0):,}")

    msg_lines.extend([
        "",
        f"<b>GA4</b> ({ga4.get('date_range', 'N/A')})",
        f"  상태: {ga4.get('status', 'unknown')}",
    ])
    if ga4.get("status") == "ok":
        msg_lines.append(f"  PV: {ga4.get('total_pv', 0):,} | 수익: ${ga4.get('total_rev', 0):.2f}")

    msg_lines.extend(["", f"⏱ {elapsed:.1f}초 소요"])

    send_telegram("\n".join(msg_lines))
    log.info("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
