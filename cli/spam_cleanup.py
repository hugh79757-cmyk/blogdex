import os
import json
import pickle
import re
from datetime import datetime
from urllib.parse import unquote

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CREDENTIALS_FILE = "/Users/twinssn/Projects/blogdex/cli/client_secret_hugh7973.json"
TOKEN_FILE = "/Users/twinssn/Projects/blogdex/cli/google_token.pickle"
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/blogger.readonly",
]
SITE_URL = "https://foodwater.tistory.com/"
REPORT_DIR = "/Users/twinssn/Projects/blogdex/cli"

SPAM_KEYWORDS = [
    "evcomu", "텔레그램", "카지노", "섯다", "파라다이스", "게임소스", "dodococo",
    "dior", "중개사이트", "파워볼", "오션파라다이스", "클릭계열", "청룡카지노",
    "게임솔루션", "가방도매", "사이트제작", "사이트임대", "사이트개발", "복제",
    "토토", "슬롯", "바카라", "먹튀", "홀덤", "포커", "바둑이", "릴게임",
    "에볼루션", "도박", "배팅", "총판", "알판매", "알공급", "파싱",
    "레플리카", "명품", "louisvuitton", "loewe", "fendi", "홍콩명품",
    "성인커뮤니티", "성피", "유흥사이트", "리버싱", "경마",
]


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return creds


def is_spam_url(url):
    decoded = unquote(url).lower()
    for kw in SPAM_KEYWORDS:
        if kw.lower() in decoded:
            return True
    path = url.replace("https://foodwater.tistory.com/", "")
    if not path.startswith("entry/") and not path.startswith("category/") and not path.startswith("m/") and not path.startswith("manage") and not path.startswith("api"):
        if len(path) > 30 and re.search(r'[A-Za-z0-9+/]{20,}', path):
            return True
    return False


def resolve_site_url(service):
    global SITE_URL
    try:
        sites = service.sites().list().execute()
        site_list = [s["siteUrl"] for s in sites.get("siteEntry", [])]
        print(f"  등록된 사이트: {site_list}")
        if SITE_URL not in site_list:
            for candidate in ["sc-domain:foodwater.tistory.com"] + site_list:
                if "foodwater" in candidate:
                    SITE_URL = candidate
                    print(f"  >> SITE_URL: {SITE_URL}")
                    return
    except Exception as e:
        print(f"  사이트 목록 조회 실패: {e}")


def scan_search_analytics(service):
    print("\n" + "=" * 60)
    print("[1] Search Analytics 스팸 스캔")
    print("=" * 60)

    spam_urls = set()
    spam_queries = []

    print("\n  URL 스캔 중...")
    try:
        resp = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate": "2025-11-01",
                "endDate": "2026-03-05",
                "dimensions": ["page"],
                "rowLimit": 25000,
            }
        ).execute()
        rows = resp.get("rows", [])
        total = len(rows)
        for row in rows:
            url = row["keys"][0]
            if is_spam_url(url):
                spam_urls.add(url)
        print(f"  전체 URL: {total}개, 스팸: {len(spam_urls)}개")
    except Exception as e:
        print(f"  URL 스캔 오류: {e}")

    print("\n  검색어 스캔 중...")
    try:
        resp = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate": "2025-11-01",
                "endDate": "2026-03-05",
                "dimensions": ["query"],
                "rowLimit": 25000,
            }
        ).execute()
        rows = resp.get("rows", [])
        for row in rows:
            q = row["keys"][0]
            for kw in SPAM_KEYWORDS:
                if kw.lower() in q.lower():
                    spam_queries.append({
                        "query": q,
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                    })
                    break
        print(f"  스팸 검색어: {len(spam_queries)}개")
        if spam_queries:
            top = sorted(spam_queries, key=lambda x: x["impressions"], reverse=True)[:10]
            for q in top:
                print(f"    \"{q['query'][:50]}\" (노출:{q['impressions']}, 클릭:{q['clicks']})")
    except Exception as e:
        print(f"  검색어 스캔 오류: {e}")

    return spam_urls, spam_queries


def check_sitemaps(service):
    print("\n" + "=" * 60)
    print("[2] 사이트맵 점검")
    print("=" * 60)
    try:
        resp = service.sitemaps().list(siteUrl=SITE_URL).execute()
        sitemaps = resp.get("sitemap", [])
        if sitemaps:
            for sm in sitemaps:
                print(f"  {sm['path']}")
                print(f"    제출: {sm.get('lastSubmitted', 'N/A')}, 경고: {sm.get('warnings', 0)}, 오류: {sm.get('errors', 0)}")
        else:
            print("  등록된 사이트맵 없음")
    except Exception as e:
        print(f"  오류: {e}")


def inspect_urls(service, urls, max_count=10):
    print("\n" + "=" * 60)
    print(f"[3] URL 색인 상태 검사 (샘플 {max_count}개)")
    print("=" * 60)

    indexed = 0
    not_indexed = 0
    sample = list(urls)[:max_count]

    for i, url in enumerate(sample, 1):
        display = unquote(url)[:70]
        try:
            result = service.urlInspection().index().inspect(
                body={"inspectionUrl": url, "siteUrl": SITE_URL}
            ).execute()
            idx = result.get("inspectionResult", {}).get("indexStatusResult", {})
            verdict = idx.get("verdict", "?")
            coverage = idx.get("coverageState", "?")
            if verdict == "PASS":
                print(f"  {i}. [색인됨] {display}")
                indexed += 1
            else:
                print(f"  {i}. [미색인: {coverage}] {display}")
                not_indexed += 1
        except Exception as e:
            print(f"  {i}. [오류] {display}")
            print(f"       {str(e)[:80]}")

    print(f"\n  색인: {indexed}개, 미색인: {not_indexed}개")
    return indexed


def save_reports(all_spam_urls, spam_queries):
    print("\n" + "=" * 60)
    print("[4] 보고서 저장")
    print("=" * 60)

    json_path = os.path.join(REPORT_DIR, "spam_report.json")
    report = {
        "date": datetime.now().isoformat(),
        "total_spam_urls": len(all_spam_urls),
        "spam_urls": sorted([unquote(u) for u in all_spam_urls]),
        "spam_queries_count": len(spam_queries),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  {json_path}")

    txt_path = os.path.join(REPORT_DIR, "spam_urls_for_removal.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for url in sorted(all_spam_urls):
            f.write(url + "\n")
    print(f"  {txt_path} ({len(all_spam_urls)}개)")


def print_guide(total):
    print("\n" + "=" * 60)
    print("[5] 조치 가이드")
    print("=" * 60)
    print(f"""
  스팸 URL 총 {total}개 발견

  이 URL들은 이미 404이므로 구글이 재크롤링하면 자연 제거됩니다.
  빠른 제거를 원하면 아래 절차를 따르세요:

  1. GSC 웹 콘솔 > 삭제 메뉴:
     https://search.google.com/search-console/removals

     '새 요청' > '임시로 URL 삭제' > '이 접두사로 시작하는 URL만 삭제'

  2. 보안 문제 확인:
     https://search.google.com/search-console/security-issues

  3. 수동 조치 확인:
     https://search.google.com/search-console/manual-actions

  4. 티스토리 계정 보안:
     - 카카오 비밀번호 변경 + 2FA 활성화
     - 관리자 목록 확인
     - 의심 플러그인/코드 제거
""")


def main():
    print("=" * 60)
    print(f"  GSC 스팸 분석 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    print("  인증 완료 (기존 토큰 사용)")

    resolve_site_url(service)

    spam_urls, spam_queries = scan_search_analytics(service)
    check_sitemaps(service)

    if spam_urls:
        inspect_urls(service, spam_urls, max_count=10)

    save_reports(spam_urls, spam_queries)
    print_guide(len(spam_urls))


if __name__ == "__main__":
    main()
