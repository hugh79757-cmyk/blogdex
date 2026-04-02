"""
Google Indexing API - URL 제출 도구
사용법:
  python index_submit.py                  # 모든 사이트 사이트맵에서 최신 URL 제출
  python index_submit.py --site rotcha.kr # 특정 사이트만
  python index_submit.py --url https://rotcha.kr/some-page  # 단일 URL
  python index_submit.py --dry           # 실제 제출 없이 대상만 확인
"""
import argparse
import json
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from google_auth import get_credentials
from googleapiclient.discovery import build

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
log = logging.getLogger("index_submit")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"index_submit_{datetime.now():%Y-%m-%d}.log"),
    ],
)

INDEXING_API_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"
QUOTA_PER_DAY = 200

# daily_sync.py와 동일한 사이트 목록
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
    "https://fitness.informationhot.kr/",
    "https://tour.techpawz.com/",
    "https://betguide.informationhot.kr/",
    "https://fsched.informationhot.kr/",
    "https://fstats.informationhot.kr/",
    "https://kboplayer.informationhot.kr/",
    "https://kboschedule.informationhot.kr/",
    "https://kboteam.informationhot.kr/",
    "https://proto.informationhot.kr/",
    "https://protostats.informationhot.kr/",
]


def fetch_sitemap_urls(site_url, max_urls=5):
    """사이트맵에서 최신 URL을 가져온다"""
    urls = []
    sitemap_candidates = [
        site_url.rstrip("/") + "/sitemap.xml",
        site_url.rstrip("/") + "/sitemap-index.xml",
    ]

    for sitemap_url in sitemap_candidates:
        try:
            resp = requests.get(sitemap_url, timeout=10)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # sitemap index인 경우 모든 서브 사이트맵에서 URL 수집
            sitemaps = root.findall("s:sitemap/s:loc", ns)
            if sitemaps:
                combined_root = None
                for sm in sitemaps:
                    sub_url = sm.text
                    # /en/ 사이트맵 스킵, /ko/ 우선
                    if "/en/" in sub_url:
                        continue
                    try:
                        sub_resp = requests.get(sub_url, timeout=10)
                        if sub_resp.status_code == 200:
                            root = ET.fromstring(sub_resp.content)
                            combined_root = root
                            break
                    except Exception:
                        pass
                # /ko/ 못 찾으면 첫 번째라도
                if combined_root is None:
                    try:
                        sub_resp = requests.get(sitemaps[0].text, timeout=10)
                        if sub_resp.status_code == 200:
                            root = ET.fromstring(sub_resp.content)
                    except Exception:
                        pass

            # URL 추출 (lastmod 기준 최신순)
            url_entries = []
            for url_elem in root.findall("s:url", ns):
                loc = url_elem.find("s:loc", ns)
                lastmod = url_elem.find("s:lastmod", ns)
                if loc is not None and loc.text:
                    mod_date = lastmod.text if lastmod is not None else "1970-01-01"
                    url_entries.append((loc.text, mod_date))

            # 카테고리/태그/인덱스/리스트 페이지 제외, 실제 콘텐츠만
            SKIP_PATTERNS = ["/categories", "/tags", "/en/", "/page/", "/search/"]
            def is_content_url(u):
                path = u.replace(site_url.rstrip("/"), "").rstrip("/")
                if not path or path == "/posts":
                    return False
                if any(p in u for p in SKIP_PATTERNS):
                    return False
                return True
            filtered = [(u, d) for u, d in url_entries if is_content_url(u)]
            # 콘텐츠가 없으면 홈페이지라도 포함
            if not filtered:
                filtered = url_entries
            filtered.sort(key=lambda x: x[1], reverse=True)
            urls = [u[0] for u in filtered[:max_urls]]

            if urls:
                break
        except Exception as e:
            log.debug(f"사이트맵 {sitemap_url} 실패: {e}")
            continue

    return urls


def submit_urls(creds, urls, dry_run=False):
    """Indexing API로 URL 제출"""
    from google.auth.transport.requests import Request as AuthRequest

    creds.refresh(AuthRequest())
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    results = {"success": 0, "error": 0, "errors": []}

    for url in urls:
        if dry_run:
            log.info(f"  [DRY] {url}")
            results["success"] += 1
            continue

        body = {
            "url": url,
            "type": "URL_UPDATED",
        }

        try:
            resp = requests.post(INDEXING_API_URL, headers=headers, json=body, timeout=10)
            if resp.status_code == 200:
                log.info(f"  OK: {url}")
                results["success"] += 1
            elif resp.status_code == 429:
                log.warning(f"  쿼터 초과 - 제출 중단")
                results["quota_exceeded"] = True
                return results
            else:
                error_msg = resp.text[:200]
                log.warning(f"  FAIL ({resp.status_code}): {url} - {error_msg}")
                results["error"] += 1
                results["errors"].append({"url": url, "status": resp.status_code, "msg": error_msg})
        except Exception as e:
            log.error(f"  ERROR: {url} - {e}")
            results["error"] += 1
            results["errors"].append({"url": url, "msg": str(e)})

    return results


def run(site_filter=None, single_url=None, dry_run=False, max_per_site=5):
    creds = get_credentials()
    total_submitted = 0

    if single_url:
        log.info(f"단일 URL 제출: {single_url}")
        result = submit_urls(creds, [single_url], dry_run)
        total_submitted = result["success"]
    else:
        sites = SITES
        if site_filter:
            sites = [s for s in SITES if site_filter in s]
            if not sites:
                log.error(f"'{site_filter}'와 매칭되는 사이트 없음")
                return

        log.info(f"대상 사이트: {len(sites)}개, 사이트당 최대 {max_per_site}개 URL")

        for site_url in sites:
            name = site_url.replace("https://", "").rstrip("/")

            if total_submitted >= QUOTA_PER_DAY:
                log.warning(f"일일 쿼터 {QUOTA_PER_DAY}건 도달, 중단")
                break

            urls = fetch_sitemap_urls(site_url, max_urls=max_per_site)
            if not urls:
                log.info(f"  {name}: 사이트맵 URL 없음, 홈페이지만 제출")
                urls = [site_url]

            remaining = QUOTA_PER_DAY - total_submitted
            urls = urls[:remaining]

            log.info(f"{name}: {len(urls)}개 URL 제출")
            result = submit_urls(creds, urls, dry_run)
            total_submitted += result["success"]
            if result.get("quota_exceeded"):
                log.warning("일일 쿼터 초과, 나머지 사이트 스킵")
                break

    log.info(f"\n완료: {total_submitted}건 제출" + (" (DRY RUN)" if dry_run else ""))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Indexing API URL 제출")
    parser.add_argument("--site", help="특정 사이트만 (예: rotcha.kr)")
    parser.add_argument("--url", help="단일 URL 제출")
    parser.add_argument("--dry", action="store_true", help="실제 제출 없이 대상만 확인")
    parser.add_argument("--max", type=int, default=5, help="사이트당 최대 URL 수 (기본 5)")
    args = parser.parse_args()

    run(site_filter=args.site, single_url=args.url, dry_run=args.dry, max_per_site=args.max)
