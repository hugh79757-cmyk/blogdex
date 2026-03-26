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


# CSV에서 가져온 실제 스팸 URL 일부 (색인 검사용)
KNOWN_SPAM_SAMPLES = [
    "https://foodwater.tistory.com/entry/%EC%A4%91%EA%B0%9C%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%20%E3%80%90%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%3A%40evcomu%F0%9F%91%A8%F0%9F%8F%BE%E2%80%8D%E2%9D%A4%EF%B8%8F%E2%80%8D%F0%9F%91%A8%F0%9F%8F%BE%E3%80%91%20%EC%9D%B8%ED%84%B0%EB%84%B7%EC%98%A4%EC%85%98%ED%8C%8C%EB%9D%BC%EB%8B%A4%EC%9D%B4%EC%8A%A4%EA%B2%8C%EC%9E%84%20%EC%B2%B4%ED%97%98",
    "https://foodwater.tistory.com/entry/%EC%84%AF%EB%8B%A4%EC%82%AC%EC%9D%B4%ED%8A%B8%EA%B0%9C%EB%B0%9C%EC%B2%B4%ED%97%98%E2%98%85%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%F0%9F%91%A8%F0%9F%8F%BC%E2%80%8D%F0%9F%92%BB%40evcomu%F0%9F%A7%8E%F0%9F%8F%BB%E2%80%8D%E2%99%82%EF%B8%8F%EC%84%AF%EB%8B%A4%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%9E%84%EB%8C%80",
    "https://foodwater.tistory.com/entry/%EA%B0%80%EB%B0%A9%EB%8F%84%EB%A7%A4%20%E3%80%90%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%3A%40evcomu%F0%9F%91%A9%F0%9F%8F%BE%E2%80%8D%E2%9D%A4%EF%B8%8F%E2%80%8D%F0%9F%92%8B%E2%80%8D%F0%9F%91%A9%F0%9F%8F%BF%E3%80%91%20%EA%B0%80%EB%B0%A9%EB%8F%84%EB%A7%A4%EC%82%AC%EC%9D%B4%ED%8A%B8%20%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8",
    "https://foodwater.tistory.com/entry/%EC%B9%B4%EC%A7%80%EB%85%B8%20%EB%B2%95%20%E3%80%90%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%3A%40evcomu%F0%9F%9A%A5%E3%80%91%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%EB%B1%85%EC%BB%A4%20%EC%9D%B4%EB%B2%A4%ED%8A%B8",
    "https://foodwater.tistory.com/entry/%ED%85%94%EB%A0%88%EA%B7%B8%EB%9E%A8%F0%9F%A7%98%F0%9F%8F%BD%E2%80%8D%E2%99%80%EF%B8%8F%40evcomu%F0%9F%9A%91%EB%AC%B4%EC%84%A4%EC%B9%98%EB%B0%94%EB%91%91%EC%9D%B4%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%E2%9C%93%EB%AC%B4%EC%84%A4%EC%B9%98%EB%B0%94%EB%91%91%EC%9D%B4%EC%A0%9C%EC%9E%91%F0%9F%A7%91%F0%9F%8F%BF%E2%80%8D%F0%9F%A6%BD%E2%80%8D%E2%9E%A1%EF%B8%8F%EB%B6%84%EC%84%9D",
    "https://foodwater.tistory.com/2qB40whuVQV+cq+AF2r4eBwzZZkARbLsaJaeD0ypPpxFJPUjH+ZsTFxB+H1GWC3",
    "https://foodwater.tistory.com/CElwL5/yOrTEXYo3RhAT9rc89Px+AIpytTupmp9Ldmsn3CfBjabnjzItzYzS6nI",
    "https://foodwater.tistory.com/bIQH5GoCjsAV7f9gmLXrBT5pkya651nJSdTVHt5jVQ1ksfDWmR1fVvA3Bxr+ffM",
    "https://foodwater.tistory.com/Vxzgzoaz6xfDrT3AilmdTJ8QtIMLezaicO0tUkHOfWWxVpSnp+hEHcwItQqZ9Xp",
    "https://foodwater.tistory.com/entry/%EC%8A%AC%EB%A1%AF%EA%B2%8C%EC%9E%84%EB%B6%84%EC%96%91%20%EC%8A%AC%EB%A1%AF%EA%B2%8C%EC%9E%84%EC%82%AC%EC%9D%B4%ED%8A%B8%20%EC%8A%AC%EB%A1%AF%EA%B2%8C%EC%9E%84%EC%95%8C%ED%8C%90%EB%A7%A4%20%EC%8A%AC%EB%A1%AF%EA%B2%8C%EC%9E%84%EC%9E%84%EB%8C%80%20%EC%8A%AC%EB%A1%AF%EA%B2%8C%EC%9E%84%EC%A0%9C%EC%9E%91%20%EC%8A%AC%EB%A1%AF%EB%B6%84%EC%96%91%20%EC%8A%AC%EB%A1%AF%EC%82%AC%EC%9D%B4%ED%8A%B8%20%EC%8A%AC%EB%A1%AF%EC%82%AC%EC%9D%B4%ED%8A%B8%20%EC%A0%9C%EC%9E%91%20%EC%8A%AC%EB%A1%AF%EC%82%AC%EC%9D%B4%ED%8A%B8api%20%EC%8A%AC%EB%A1%AF%EC%82%AC%EC%9D%B4%ED%8A%B8api%EB%B6%84%EC%96%91",
    "https://foodwater.tistory.com/entry/%EB%B0%94%EB%91%91%EC%9D%B4%EA%B2%8C%EC%9E%84%ED%8C%90%EB%A7%A4%20%EB%B0%94%EB%91%91%EC%9D%B4%EA%B2%8C%EC%9E%84%ED%8C%90%EB%A7%A4%ED%99%80%EB%8D%A4%EC%86%94%EB%A3%A8%EC%85%98%EA%B0%9C%EB%B0%9C%20%EB%B0%94%EB%91%91%EC%9D%B4%EA%B2%8C%EC%9E%84%ED%8F%AC%EC%BB%A4%EB%B0%94%EC%B9%B4%EB%9D%BC%20%EB%B0%94%EB%91%91%EC%9D%B4%EA%B2%8C%EC%9E%84%ED%95%A0%EB%A7%8C%ED%95%9C%EA%B3%B3%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%A3%B0%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%A7%9E%EA%B3%A0%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%A7%A4%EC%9E%A5%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%AC%B4%EC%84%A4%EC%B9%98%EA%B0%9C%EB%B0%9C%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%AC%B4%EC%84%A4%EC%B9%98%EA%B0%9C%EB%B0%9C%ED%8F%AC%EC%BB%A4%EA%B2%8C%EC%9E%84%EA%B0%9C%EB%B0%9C%20%EB%B0%94%EB%91%91%EC%9D%B4%EB%B0%B1%ED%99%94%EC%A0%90",
    "https://foodwater.tistory.com/entry/%EC%B9%B4%EC%A7%80%EB%85%B8%20%EA%B2%8C%EC%9E%84%20%EC%A3%BC%EC%82%AC%EC%9C%84%20%E3%80%90%ED%85%94%EB%A0%88%3A%40evcomu%F0%9F%9B%AC%E3%80%91%20%EC%9B%B9%EC%82%AC%EC%9D%B4%ED%8A%B8%EA%B2%AC%EC%A0%81%20%EC%B2%B4%ED%97%98",
    "https://foodwater.tistory.com/entry/%ED%99%80%EB%8D%A4%EC%9D%B4%EB%9E%80%20%ED%99%80%EB%8D%A4%EC%9E%84%EB%8C%80%20%ED%99%80%EB%8D%A4%EC%A0%84%EB%9E%B5%20%ED%99%80%EB%8D%A4%EC%A0%9C%EC%9E%91%20%ED%99%80%EB%8D%A4%EC%A0%9C%EC%9E%91%ED%99%80%EB%8D%A4%EC%9E%84%EB%8C%80%20%ED%99%80%EB%8D%A4%EC%A1%B4%20%ED%99%80%EB%8D%A4%EC%A3%BC%EC%86%8C%20%ED%99%80%EB%8D%A4%EC%B2%9C%EA%B5%AD%20%ED%99%80%EB%8D%A4%EC%B2%B4%ED%81%AC%20%ED%99%80%EB%8D%A4%EC%B4%9D%ED%8C%90",
    "https://foodwater.tistory.com/entry/dior%20%EA%B0%80%EB%B0%A9%20%E3%80%90%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80%3Adodococo.com%F0%9F%A6%B6%F0%9F%8F%BE%E3%80%91%20dior%EA%B0%80%EA%B2%A9%20%EC%84%B8%EB%B6%80%20%EC%A0%95%EB%B3%B4",
    "https://foodwater.tistory.com/entry/%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%EC%A1%B0%EC%9E%91%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%EC%B4%9D%ED%8C%90%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%ED%99%80%EB%8D%A4%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%ED%99%88%ED%8E%98%EC%9D%B4%EC%A7%80%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%BD%94%EB%A6%AC%EC%95%84%20%EC%B9%B4%EC%A7%80%EB%85%B8%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%EC%BF%A0%ED%8F%B0%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%ED%86%A0%ED%86%A0%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%ED%8F%AC%EC%BB%A4%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%ED%94%84%EB%A1%9C%EA%B7%B8%EB%9E%A8%20%EC%97%90%EB%B3%BC%EB%A3%A8%EC%85%98%20%ED%95%B4%ED%82%B9",
    "https://foodwater.tistory.com/entry/%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EB%B2%B3%ED%94%BC%EC%8A%A4%ED%8A%B8%EB%86%80%EA%B2%80%EC%86%8C%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EB%B9%84%EC%9A%A9%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EB%B9%84%EC%9A%A9%EB%86%80%EA%B2%80%EC%86%8C%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EB%B9%84%EC%BD%94%EB%A6%AC%EC%95%84%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%83%A4%EC%98%A4%EB%AF%B8%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%87%BC%EB%AF%B8%EB%8D%94%EB%B2%B3%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%9C%84%EB%8B%89%EC%8A%A4%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%9C%84%EB%8B%89%EC%8A%A4%EB%86%80%EA%B2%80%EC%86%8C%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%9C%A0%EB%8B%8888%20%ED%86%A0%ED%86%A0%EC%82%AC%EC%9D%B4%ED%8A%B8%EC%A0%9C%EC%9E%91%EC%9C%A0%EB%8B%8888%EB%86%80%EA%B2%80%EC%86%8C",
]


def main():
    print("=" * 60)
    print(f"  스팸 URL 색인 상태 정밀 검사")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    print("  인증 완료\n")

    indexed_urls = []
    not_indexed_urls = []
    error_urls = []

    for i, url in enumerate(KNOWN_SPAM_SAMPLES, 1):
        decoded = unquote(url)
        if len(decoded) > 60:
            display = decoded[:60] + "..."
        else:
            display = decoded

        try:
            result = service.urlInspection().index().inspect(
                body={"inspectionUrl": url, "siteUrl": SITE_URL}
            ).execute()
            idx = result.get("inspectionResult", {}).get("indexStatusResult", {})
            verdict = idx.get("verdict", "?")
            coverage = idx.get("coverageState", "?")

            if verdict == "PASS":
                print(f"  {i:2d}. [색인됨]  {display}")
                indexed_urls.append(url)
            else:
                print(f"  {i:2d}. [미색인]  {display}")
                print(f"       상태: {coverage}")
                not_indexed_urls.append(url)
        except Exception as e:
            err = str(e)[:80]
            print(f"  {i:2d}. [오류]    {display}")
            print(f"       {err}")
            error_urls.append(url)

    print(f"\n{'=' * 60}")
    print(f"  결과 요약")
    print(f"{'=' * 60}")
    print(f"  검사: {len(KNOWN_SPAM_SAMPLES)}개")
    print(f"  색인됨: {len(indexed_urls)}개  <-- 이것들이 문제!")
    print(f"  미색인: {len(not_indexed_urls)}개")
    print(f"  오류: {len(error_urls)}개")

    if indexed_urls:
        print(f"\n  !! 아직 구글에 색인된 스팸 URL {len(indexed_urls)}개:")
        for url in indexed_urls:
            print(f"    {unquote(url)[:80]}")
        print(f"\n  >> GSC 웹 콘솔에서 이 URL들의 삭제를 요청하세요:")
        print(f"     https://search.google.com/search-console/removals")
    else:
        print(f"\n  >> 검사한 스팸 URL은 모두 색인에서 제거된 상태입니다.")
        print(f"     시간이 지나면 나머지도 자동 제거됩니다.")


if __name__ == "__main__":
    main()
