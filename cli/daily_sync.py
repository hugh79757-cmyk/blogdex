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
from monitor import SyncMonitor, check_data_quality

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
    "https://tv-show.informationhot.kr/",
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
    "https://kbo.rotcha.kr/",
    "https://apt.informationhot.kr/",
    "https://apply.informationhot.kr/",
    "https://tax.informationhot.kr/",
    "https://rent.informationhot.kr/",
    "https://brand.informationhot.kr/",
    "https://senior.informationhot.kr/",
    "https://laptop.informationhot.kr/",
    "https://appliance.informationhot.kr/",
    "https://interior.informationhot.kr/",
    "https://baby.informationhot.kr/",
    "https://beauty.informationhot.kr/",
    "https://camping.informationhot.kr/",
    "https://fitness.informationhot.kr/",
    "https://health.informationhot.kr/",
    "https://kitchen.informationhot.kr/",
    "https://pet.informationhot.kr/",
    "https://pick.informationhot.kr/",
    "https://rank.informationhot.kr/",
    "https://tour.techpawz.com/",
    "https://betguide.informationhot.kr/",
    "https://fsched.informationhot.kr/",
    "https://fstats.informationhot.kr/",
    "https://kboplayer.informationhot.kr/",
    "https://kboschedule.informationhot.kr/",
    "https://kboteam.informationhot.kr/",
    "https://proto.informationhot.kr/",
    "https://protostats.informationhot.kr/",
    "https://protoking.informationhot.kr/",
    "https://6.informationhot.kr/",
    "https://7.informationhot.kr/",
    "https://8.informationhot.kr/",
    "https://adventure.techpawz.com/",
    "https://airlines.techpawz.com/",
    "https://airports.techpawz.com/",
    "https://bus.techpawz.com/",
    "https://cruise.techpawz.com/",
    "https://culture.techpawz.com/",
    "https://daytrips.techpawz.com/",
    "https://deals.techpawz.com/",
    "https://dining.techpawz.com/",
    "https://dividend.techpawz.com/",
    "https://esim.techpawz.com/",
    "https://etf.techpawz.com/",
    "https://eurail.techpawz.com/",
    "https://ferry.techpawz.com/",
    "https://finance.techpawz.com/",
    "https://flights.techpawz.com/",
    "https://foodtour.techpawz.com/",
    "https://heritage.aikorea24.kr/",
    "https://ipo.techpawz.com/",
    "https://keyword.aikorea24.kr/",
    "https://keywords.rotcha.kr/",
    "https://michelin.techpawz.com/",
    "https://multiday.techpawz.com/",
    "https://nature.techpawz.com/",
    "https://phototour.techpawz.com/",
    "https://sector.techpawz.com/",
    "https://tours.techpawz.com/",
    "https://trains.techpawz.com/",
    "https://transfers.techpawz.com/",
    "https://visa.techpawz.com/",
    "https://visafree.techpawz.com/",
    "https://walking.techpawz.com/",
    "https://watersports.techpawz.com/",
    "https://simprotection.informationhot.kr/",
    "https://biz.techpawz.com/",
    "https://persona.aikorea24.kr/",
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
    "502880375": "2.techpawz.com",
    "520459800": "travel.rotcha.kr",
    "518592752": "zodiac.techpawz.com",
    "515574149": "issue.techpawz.com",
    "502581984": "info.techpawz.com",
    "524828505": "cert.aikorea24.kr",
    "524509961": "aikorea24.kr",
    "529715626": "apt.informationhot.kr",
    "529752187": "apply.informationhot.kr",
    "529742117": "tax.informationhot.kr",
    "529720369": "rent.informationhot.kr",
    "529762700": "brand.informationhot.kr",
    "531060035": "appliance.informationhot.kr",
    "531030542": "baby.informationhot.kr",
    "531081565": "betguide.informationhot.kr",
    "531028860": "fitness.informationhot.kr",
    "531076492": "fsched.informationhot.kr",
    "531068628": "fstats.informationhot.kr",
    "531082954": "interior.informationhot.kr",
    "531090148": "kboplayer.informationhot.kr",
    "531090946": "kboschedule.informationhot.kr",
    "531013822": "kboteam.informationhot.kr",
    "531055987": "laptop.informationhot.kr",
    "531068343": "proto.informationhot.kr",
    "531013823": "protostats.informationhot.kr",
    "531027923": "senior.informationhot.kr",
    "531077897": "achaanstree.tistory.com",
    "531027450": "compare.rotcha.kr",
    "531086518": "deal.rotcha.kr",
    "531071264": "ev.rotcha.kr",
    "531035058": "foodwater.tistory.com",
    "531022174": "guide.rotcha.kr",
    "531050852": "kbo.rotcha.kr",
    "531035059": "mimdiomcat.tistory.com",
    "531059838": "sports.rotcha.kr",
    "531012250": "tco.rotcha.kr",
    "531007356": "tour.techpawz.com",
    "531057733": "tour1.rotcha.kr",
    "531027528": "tour2.rotcha.kr",
    "531059839": "tour3.rotcha.kr",
    "531050452": "travel1.rotcha.kr",
    "531063285": "travel2.rotcha.kr",
    "531145374": "6.informationhot.kr",
    "531063843": "7.informationhot.kr",
    "531123457": "adventure.techpawz.com",
    "531065834": "bus.techpawz.com",
    "531006370": "cruise.techpawz.com",
    "531065835": "culture.techpawz.com",
    "531054102": "daytrips.techpawz.com",
    "531065294": "deals.techpawz.com",
    "531047182": "dining.techpawz.com",
    "531081619": "dividend.techpawz.com",
    "531050510": "etf.techpawz.com",
    "531123458": "ferry.techpawz.com",
    "531118185": "finance.techpawz.com",
    "531167909": "foodtour.techpawz.com",
    "531138757": "heritage.aikorea24.kr",
    "531064331": "ipo.techpawz.com",
    "531129334": "keyword.aikorea24.kr",
    "531142752": "keywords.rotcha.kr",
    "531139671": "multiday.techpawz.com",
    "531055811": "nature.techpawz.com",
    "531161435": "sector.techpawz.com",
    "531012256": "transfers.techpawz.com",
    "531135786": "visafree.techpawz.com",
    "531135787": "walking.techpawz.com",
    "531139672": "watersports.techpawz.com",
    "531035921": "airlines.techpawz.com",
    "531044776": "airports.techpawz.com",
    "531068317": "esim.techpawz.com",
    "531065272": "flights.techpawz.com",
    "531066288": "michelin.techpawz.com",
    "531081222": "tours.techpawz.com",
    "531082945": "trains.techpawz.com",
    "531039430": "visa.techpawz.com",
    "543474092": "eurail.techpawz.com",
    "543510271": "phototour.techpawz.com",
    "543441626": "rank.informationhot.kr",
    "543364949": "protoking.informationhot.kr",
    "543475157": "pick.informationhot.kr",
    "543483108": "pet.informationhot.kr",
    "543505819": "kitchen.informationhot.kr",
    "543536240": "health.informationhot.kr",
    "543471477": "camping.informationhot.kr",
    "543478347": "beauty.informationhot.kr",
    "538315250": "persona.aikorea24.kr",
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



def api_get(path, params=None):
    try:
        r = requests.get(f"{API_URL}{path}", headers=HEADERS, params=params, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"API GET {path} 실패: {e}")
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


# ══════════════════════════════════════════════════════════════
#  태스크 러너 — 재시도 + 예외 격리
# ══════════════════════════════════════════════════════════════

import functools
import time as _time


def retry(max_attempts=3, delay_seconds=5):
    """
    재시도 데코레이터 — exponential backoff 적용.
    네트워크 요청이 많은 태스크(GSC, GA4)에 사용.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        wait = delay_seconds * (2 ** (attempt - 1))
                        log.warning(
                            f"[RETRY] {func.__name__} ({attempt}/{max_attempts}) "
                            f"실패: {e}. {wait:.0f}초 후 재시도..."
                        )
                        _time.sleep(wait)
                    else:
                        log.error(
                            f"[RETRY] {func.__name__} 최종 실패 "
                            f"({max_attempts}/{max_attempts}): {e}"
                        )
                        raise
            raise last_exception  # type: ignore
        return wrapper
    return decorator


def run_task(name: str, fn, *args, **kwargs) -> dict:
    """
    태스크 실행 래퍼 — 예외를 결과 dict로 변환하여 격리.
    실패해도 다음 태스크가 계속 실행됩니다.

    Returns:
        dict: {"status": "ok"|"error"|"skipped", ...}
    """
    try:
        log.info(f"─" * 40)
        log.info(f"▶ {name} 시작")
        result = fn(*args, **kwargs)
        log.info(f"✅ {name} 완료")
        return result
    except Exception as e:
        log.error(f"❌ {name} 실패: {e}")
        return {"status": "error", "message": str(e)}


def skip_task() -> dict:
    """--skip 플래그로 스킵된 태스크의 결과"""
    return {"status": "skipped"}


# ══════════════════════════════════════════════════════════════


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


@retry(max_attempts=3, delay_seconds=5)
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


@retry(max_attempts=3, delay_seconds=5)
def sync_ga4(days=3):
    """GA4 페이지뷰 수집 → D1 업로드"""
    log.info("=== GA4 동기화 시작 ===")

    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
    from google.analytics.admin import AnalyticsAdminServiceClient

    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    admin = AnalyticsAdminServiceClient(credentials=creds)

    # KRW→USD 환율 (고정, 2026-06 기준)
    KRW_PER_USD = 1350.0

    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    all_data = []
    total_pv = 0
    total_rev_usd = 0.0

    for prop_id, domain in GA4_PROPERTIES.items():
        try:
            # 속성 통화 확인
            prop = admin.get_property(name=f"properties/{prop_id}")
            currency = prop.currency_code
            to_usd = 1.0 / KRW_PER_USD if currency == "KRW" else 1.0

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
            site_rev_usd = 0.0
            for row in response.rows:
                path = row.dimension_values[0].value
                date = row.dimension_values[1].value
                date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                pageviews = int(row.metric_values[0].value)
                sessions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value) * to_usd
                all_data.append({
                    "site": domain, "date": date_fmt,
                    "page": f"https://{domain}{path}",
                    "pageviews": pageviews, "sessions": sessions,
                    "revenue": round(revenue, 6),
                })
                site_pv += pageviews
                site_rev_usd += revenue
            total_pv += site_pv
            total_rev_usd += site_rev_usd
            log.info(f"  {domain}: {site_pv:,} PV, ${site_rev_usd:.4f}")
        except Exception as e:
            log.error(f"  {domain}: {e}")

    # D1 업로드
    if all_data:
        for i in range(0, len(all_data), 500):
            batch = all_data[i:i+500]
            api_post("/ga4/pageviews", {"data": batch})

    log.info(f"GA4 완료: {len(all_data)}건, {total_pv:,} PV, ${total_rev_usd:.4f}")

    return {
        "status": "ok", "date_range": f"{start_str}~{end_str}",
        "row_count": len(all_data), "total_pv": total_pv,
        "total_rev": round(total_rev_usd, 6)
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
    """
    Blogdex 일일 동기화 메인 엔트리포인트.

    각 태스크는 run_task()로 격리되어 실행됩니다.
    한 태스크가 실패해도 나머지 태스크는 계속 실행됩니다.
    --skip-* 플래그로 개별 태스크를 생략할 수 있습니다.
    """
    start_time = datetime.now()
    log.info("=" * 50)
    log.info("Blogdex 일일 동기화 시작")
    log.info("=" * 50)

    # ── 모니터 초기화 ──
    monitor = SyncMonitor(pipeline_name="Blogdex Daily Sync")
    log.info(f"SyncMonitor: Telegram={'활성' if monitor._telegram_enabled else '비활성'}")

    # ── CLI 플래그 파싱 ──
    skip_gsc     = "--skip-gsc" in sys.argv
    skip_ga4     = "--skip-ga4" in sys.argv
    skip_bing    = "--skip-bing" in sys.argv
    skip_coupang = "--skip-coupang" in sys.argv
    skip_senior  = "--skip-senior" in sys.argv

    # ── 태스크 실행 (각각 독립적, 실패 격리) ──
    # run_task 내에서 monitor.record() 호출

    def _run_sync_task(step_name: str, fn, *args, **kwargs):
        """run_task + monitor 연동 래퍼"""
        monitor.start_step(step_name)
        result = run_task(step_name, fn, *args, **kwargs)
        status = result.get("status", "error")
        msg = result.get("message", "")
        record_sync_log(step_name, result)
        # 데이터 품질 검사 (count 필드가 있으면)
        count = result.get("row_count", None)
        if count is not None and status == "ok":
            check_data_quality(monitor, step_name, count)
        elif status == "ok":
            monitor.record(step_name, "ok", msg, result)
        elif status == "skipped":
            monitor.record(step_name, "skipped", "건너뜀")
        else:
            monitor.record(step_name, "error", msg, result)
        return result

    _run_sync_task("gsc",    sync_gsc)        if not skip_gsc     else None
    _run_sync_task("ga4",    sync_ga4, 3)      if not skip_ga4     else None
    _run_sync_task("bing",   sync_bing)        if not skip_bing    else None
    _run_sync_task("senior", sync_senior)      if not skip_senior  else None

    # 포스트 동기화 (Hugo/Astro/WordPress/Blogger)
    def sync_posts():
        from sync_hugo import run as sync_hugo_posts
        from sync_astro import run as sync_astro_posts
        from sync_wordpress import run as sync_wordpress_posts
        from sync_blogger import run as sync_blogger_posts
        sync_hugo_posts()
        sync_astro_posts()
        sync_wordpress_posts()
        sync_blogger_posts()
        return {"status": "ok", "row_count": 0}
    _run_sync_task("posts", sync_posts)

    # Google Indexing API 제출
    def sync_indexing():
        from index_submit import run as run_indexing
        run_indexing(max_per_site=3)
        return {"status": "ok", "row_count": 0}
    _run_sync_task("indexing", sync_indexing)

    # 쿠팡
    monitor.start_step("coupang")
    if not skip_coupang:
        cp_result = api_get("/coupang/summary", {"days": 1})
        if "error" in cp_result:
            monitor.record("coupang", "error", cp_result.get("error", "조회 실패"))
        else:
            total = cp_result.get("total", {})
            rev = total.get("revenue", 0)
            orders = total.get("orders", 0)
            monitor.record("coupang", "ok", f"₩{rev:,.0f} ({orders}건)", cp_result)
    else:
        monitor.record("coupang", "skipped", "건너뜀")

    # ── 소요 시간 ──
    elapsed = datetime.now() - start_time
    log.info(f"완료: {elapsed.total_seconds():.1f}초 소요")

    # ── 리포트 전송 + 저장 ──
    monitor.send_daily_report()
    monitor.save_report()


# NOTE: send_telegram_report() has been replaced by SyncMonitor.send_daily_report().
# See cli/monitor.py for the new implementation.


if __name__ == "__main__":
    main()
