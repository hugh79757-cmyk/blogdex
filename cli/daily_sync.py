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
# stdout/stderr 안전 처리 (대시보드 원격 실행 시 fd 없을 수 있음)
try:
    sys.stdout.fileno()
except (OSError, AttributeError):
    import io as _io
    _fallback_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fallback.log")
    _fh = open(_fallback_log, "a", encoding="utf-8")
    sys.stdout = _fh
    sys.stderr = _fh



# 프로젝트 경로 설정
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR.parent / ".env")  # 루트 .env (Bing, OpenAI 등)
load_dotenv(PROJECT_DIR / ".env")          # cli/.env (텔레그램 등)

# aikorea24 네이버 API 키 로드
_env_sh = "/Users/twinssn/Projects/aikorea24/api_test/.env.sh"
if os.path.exists(_env_sh):
    with open(_env_sh) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                if _line.startswith("export "):
                    _line = _line[7:]
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

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
    "https://aikorea24.kr/",
    "https://cert.aikorea24.kr/",
    "https://tour1.rotcha.kr/",
    "https://travel1.rotcha.kr/",
    "https://travel2.rotcha.kr/",
    "https://tour2.rotcha.kr/",
    "https://tour3.rotcha.kr/",
    "https://tco.rotcha.kr/",
    "https://deal.rotcha.kr/",
    "https://compare.rotcha.kr/",
    "https://guide.rotcha.kr/",
    "https://ev.rotcha.kr/",
    "https://sports.rotcha.kr/",
]

# 도메인 속성: 서브도메인 데이터를 한번에 조회 (403 우회)
DOMAIN_PROPERTIES = {
    "sc-domain:techpawz.com": [
        "dividend.techpawz.com",
        "etf.techpawz.com",
        "sector.techpawz.com",
        "ipo.techpawz.com",
        "finance.techpawz.com",
    ],
    "sc-domain:informationhot.kr": [
        "senior.informationhot.kr",
    ],
}

# GA4 속성
GA4_PROPERTIES = {
    "407313218": "techpawz.com",
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
    "502880375": "2.techpawz.com",
    "520459800": "travel.rotcha.kr",
    "518592752": "zodiac.techpawz.com",
    "515574149": "issue.techpawz.com",
    "502581984": "info.techpawz.com",
    "524828505": "cert.aikorea24.kr",
    "524509961": "aikorea24.kr",
    "407673873": "achaanstree.tistory.com",
    "407723312": "foodwater.tistory.com",
    "529365364": "tour1.rotcha.kr",
    "529354403": "travel1.rotcha.kr",
    "529351202": "travel2.rotcha.kr",
    "529355746": "tour2.rotcha.kr",
    "529368606": "tour3.rotcha.kr",
    "526695780": "sports.rotcha.kr",
    "529135373": "tco.rotcha.kr",
    "529150625": "deal.rotcha.kr",
    "529150626": "compare.rotcha.kr",
    "529158015": "guide.rotcha.kr",
    "529144463": "ev.rotcha.kr",
    "529144464": "dividend.techpawz.com",
    "529144841": "etf.techpawz.com",
    "529088575": "sector.techpawz.com",
    "529152161": "ipo.techpawz.com",
    "529142332": "finance.techpawz.com",
    "529715626": "apt.informationhot.kr",
    "529752187": "apply.informationhot.kr",
    "529742117": "tax.informationhot.kr",
    "529720369": "rent.informationhot.kr",
    "529762700": "brand.informationhot.kr",
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


def sync_senior():
    """노인복지 뉴스 수집 → D1 저장 + 브리핑 HTML 생성"""
    import urllib.request
    import urllib.parse
    from html import unescape
    import subprocess
    import time
    import httpx

    log.info("=== 노인복지 뉴스 수집 시작 ===")

    NAVER_ID = os.environ.get("NAVER_CLIENT_ID", "")
    NAVER_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")

    if not NAVER_ID or not NAVER_SECRET:
        log.error("네이버 API 키 없음")
        return {"status": "error", "row_count": 0}

    SENIOR_QUERIES = [
        "AI 노인 돌봄 서비스", "AI 시니어 디지털 교육", "AI 치매 예방 기술",
        "AI 고령자 복지 정책", "AI 요양 로봇 서비스", "노인 디지털 격차 해소",
        "독거노인 돌봄 정책", "기초연금 인상 변경", "노인 일자리 지원사업",
        "요양보호사 처우 개선",
    ]

    senior_kw = [
        "노인", "시니어", "고령", "돌봄", "치매", "요양", "실버", "어르신",
        "경로", "독거", "노후", "간병", "기초연금", "요양보호사", "복지관",
        "경로당", "노인복지", "장기요양", "노인학대", "치매안심", "노인일자리",
    ]
    skip_kw = ["부동산", "아파트", "분양", "주식", "증권", "코인"]

    def clean(text):
        if not text: return ""
        text = unescape(text)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # 1. 네이버 뉴스 수집
    results = []
    for q in SENIOR_QUERIES:
        encoded = urllib.parse.quote(q)
        url = f"https://openapi.naver.com/v1/search/news.json?query={encoded}&display=10&sort=date"
        req = urllib.request.Request(url, headers={
            "X-Naver-Client-Id": NAVER_ID,
            "X-Naver-Client-Secret": NAVER_SECRET,
        })
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            for item in data.get("items", []):
                title = clean(item["title"])
                desc = clean(item["description"])
                full = (title + " " + desc).lower()
                if any(s in full for s in skip_kw):
                    continue
                if not any(kw in full for kw in senior_kw):
                    continue
                results.append({
                    "title": title, "link": item["link"],
                    "description": desc[:200], "source": "네이버뉴스",
                    "category": "senior",
                    "pub_date": datetime.now().strftime("%Y-%m-%d"),
                })
        except Exception as e:
            log.error(f"  노인복지 '{q}' 실패: {e}")

    # 중복 제거
    seen = set()
    unique = []
    for r in results:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique.append(r)
    log.info(f"  수집: {len(unique)}건 (중복 제거 후)")

    # 2. D1 저장 (aikorea24-db)
    saved = 0
    if unique:
        try:
            env = os.environ.copy()
            env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
            for item in unique:
                title_escaped = item["title"].replace("'", "''")
                desc_escaped = item["description"].replace("'", "''")
                link_escaped = item["link"].replace("'", "''")
                cmd = (
                    f"INSERT OR IGNORE INTO news (title, link, description, source, category, pub_date) "
                    f"VALUES ('{title_escaped}', '{link_escaped}', '{desc_escaped}', "
                    f"'{item['source']}', 'senior', '{item['pub_date']}')"
                )
                r = subprocess.run(
                    ["npx", "wrangler", "d1", "execute", "aikorea24-db", "--remote", "--command", cmd],
                    capture_output=True, text=True,
                    cwd="/Users/twinssn/Projects/aikorea24", env=env, timeout=30,
                )
                if r.returncode == 0:
                    saved += 1
            log.info(f"  D1 저장: {saved}건")
        except Exception as e:
            log.error(f"  D1 저장 실패: {e}")

    # 3. 브리핑 HTML 생성
    try:
        env = os.environ.copy()
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")
        r = subprocess.run(
            ["/Users/twinssn/Projects/aikorea24/api_test/venv/bin/python3",
             "/Users/twinssn/Projects/aikorea24/api_test/senior_briefing.py"],
            capture_output=True, text=True, env=env, timeout=300,
        )
        if r.returncode == 0:
            log.info("  브리핑 HTML 생성 완료")
        else:
            log.error(f"  브리핑 생성 실패: {r.stderr[:200]}")
    except Exception as e:
        log.error(f"  브리핑 생성 실패: {e}")

    return {"status": "ok", "date": datetime.now().strftime("%Y-%m-%d"), "row_count": saved}


def sync_bing():
    """Bing Webmaster API에서 키워드/트래픽 데이터 수집"""
    log.info("=== Bing 동기화 시작 ===")

    if not BING_KEYS:
        log.warning("Bing API 키 없음, 스킵")
        return {"status": "skipped", "row_count": 0}

    total_sites = 0
    site_bing_stats = {}
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
                # 사이트별 클릭/노출 합산
                if name not in site_bing_stats:
                    site_bing_stats[name] = {"clicks": 0, "impressions": 0, "keywords": 0}
                for s in stats[-7:]:
                    site_bing_stats[name]["clicks"] += s.get("Clicks", 0)
                    site_bing_stats[name]["impressions"] += s.get("Impressions", 0)
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
                if name not in site_bing_stats:
                    site_bing_stats[name] = {"clicks": 0, "impressions": 0, "keywords": 0}
                site_bing_stats[name]["keywords"] = max(site_bing_stats[name]["keywords"], len(keywords[-100:]))
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
        "sites": total_sites, "row_count": total_keywords,
        "site_stats": site_bing_stats
    }


def sync_gsc():
    """GSC 데이터 수집 → 로컬 스냅샷 + D1 업로드"""
    log.info("=== GSC 동기화 시작 ===")

    end = datetime.now() - timedelta(days=3)
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
                    "query": kw["query"], "page": kw["page"],
                    "clicks": kw["clicks"],
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

    # === 도메인 속성으로 서브도메인 데이터 수집 ===
    for domain_prop, subdomains in DOMAIN_PROPERTIES.items():
        try:
            resp = service.searchanalytics().query(
                siteUrl=domain_prop,
                body={
                    "startDate": date_str,
                    "endDate": date_str,
                    "dimensions": ["query", "page"],
                    "rowLimit": 5000,
                }
            ).execute()
            all_rows = resp.get("rows", [])

            for subdomain in subdomains:
                sub_rows = [r for r in all_rows if subdomain in r.get("keys", ["", ""])[1]]
                clicks = sum(r["clicks"] for r in sub_rows)
                impressions = sum(r["impressions"] for r in sub_rows)
                ctr = (clicks / impressions * 100) if impressions > 0 else 0

                total_clicks += clicks
                total_impressions += impressions

                d1_daily_rows.append({
                    "site": subdomain, "date": date_str,
                    "clicks": clicks, "impressions": impressions,
                    "ctr": round(ctr, 2)
                })

                keywords = []
                sorted_rows = sorted(sub_rows, key=lambda r: r["impressions"], reverse=True)[:100]
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
                        "site": subdomain, "date": date_str,
                        "query": kw["query"], "page": kw["page"],
                        "clicks": kw["clicks"],
                        "impressions": kw["impressions"],
                        "ctr": kw["ctr"], "position": kw["position"]
                    })

                total_keywords += len(keywords)
                snapshot["sites"][subdomain] = {
                    "clicks": clicks, "impressions": impressions,
                    "ctr": round(ctr, 2), "top_keywords": keywords
                }
                log.info(f"  {subdomain} (via {domain_prop}): 클릭 {clicks}, 노출 {impressions}, 키워드 {len(keywords)}")

        except Exception as e:
            log.error(f"  {domain_prop}: {e}")
            for subdomain in subdomains:
                snapshot["sites"][subdomain] = {"error": str(e)}

    # 스냅샷 total 업데이트
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
        for i in range(0, len(d1_daily_rows), 100):
            batch = d1_daily_rows[i:i+100]
            api_post("/gsc/daily", {"data": batch})

    if d1_keyword_rows:
        for i in range(0, len(d1_keyword_rows), 100):
            batch = d1_keyword_rows[i:i+100]
            api_post("/gsc/keywords", {"data": batch})

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

    # 노인복지 뉴스 수집 + 브리핑
    try:
        senior_result = sync_senior()
        results["senior"] = senior_result
        record_sync_log("senior", senior_result)
    except Exception as e:
        log.error(f"노인복지 수집 실패: {e}")
        results["senior"] = {"status": "error", "message": str(e)}
        record_sync_log("senior", {"status": "error", "row_count": 0, "date": "N/A"})


    # 포스트 동기화 (Hugo/Astro/WordPress/Blogger)
    try:
        from sync_hugo import run as sync_hugo_posts
        from sync_astro import run as sync_astro_posts
        from sync_wordpress import run as sync_wordpress_posts
        from sync_blogger import run as sync_blogger_posts

        log.info("포스트 동기화 시작 (Hugo/Astro/WordPress/Blogger)")
        sync_hugo_posts()
        sync_astro_posts()
        sync_wordpress_posts()
        sync_blogger_posts()
        results["posts"] = {"status": "ok"}
        record_sync_log("posts", {"status": "ok", "row_count": 0, "date": datetime.now().strftime("%Y-%m-%d")})
        log.info("포스트 동기화 완료")
    except Exception as e:
        log.error(f"포스트 동기화 실패: {e}")
        results["posts"] = {"status": "error", "message": str(e)}
        record_sync_log("posts", {"status": "error", "row_count": 0, "date": "N/A"})

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

    # 색인 현황 추가
    try:
        import glob
        gsc_files = sorted(glob.glob(str(SNAPSHOT_DIR / "gsc_2026-*.json")))[-7:]
        gsc_sites = {}
        for sf in gsc_files:
            sd = json.load(open(sf))
            for sname, sinfo in sd.get("sites", {}).items():
                if sname not in gsc_sites:
                    gsc_sites[sname] = {"impressions": 0}
                gsc_sites[sname]["impressions"] += sinfo.get("impressions", 0)

        bing_stats = results.get("bing", {}).get("site_stats", {})

        all_s = sorted(set(list(gsc_sites.keys()) + list(bing_stats.keys())))
        ok_count = 0
        no_count = 0
        no_sites = []
        for s in all_s:
            g = gsc_sites.get(s, {}).get("impressions", 0)
            b = bing_stats.get(s, {}).get('keywords', 0)
            if g > 0 or b > 0:
                ok_count += 1
            else:
                no_count += 1
                no_sites.append(s)

        bing_total_clk = sum(v.get("clicks", 0) for v in bing_stats.values())
        bing_total_imp = sum(v.get("impressions", 0) for v in bing_stats.values())

        msg_lines.extend([
            "",
            f"<b>🔍 Bing</b>",
            f"  클릭: {bing_total_clk:,} | 노출: {bing_total_imp:,} | 사이트: {len(bing_stats)}개",
            "",
            f"<b>📋 색인 현황</b> (GSC+Bing)",
            f"  확인: {ok_count}개 | 미확인: {no_count}개 | 전체: {len(all_s)}개",
        ])
        if no_sites:
            msg_lines.append(f"  미확인: {', '.join(no_sites[:10])}")
            if len(no_sites) > 10:
                msg_lines.append(f"  ...외 {len(no_sites)-10}개")
    except Exception as e:
        log.error(f"색인 현황 생성 실패: {e}")

    msg_lines.extend(["", f"⏱ {elapsed:.1f}초 소요"])

    send_telegram("\n".join(msg_lines))
    log.info("텔레그램 알림 전송 완료")


if __name__ == "__main__":
    main()
