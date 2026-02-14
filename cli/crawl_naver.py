#!/usr/bin/env python3
"""
네이버 블로그 타이틀 추출기 - API 버전
결과 CSV는 collected_titles/ 폴더에 저장
"""

import asyncio
import httpx
import json
import csv
import os
import re
from urllib.parse import urlparse, unquote

OUTPUT_DIR = "/Users/twinssn/Projects/blogdex/cli/collected_titles"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_blog_id(url):
    parsed = urlparse(url)
    if 'blog.naver.com' in parsed.netloc:
        path_parts = parsed.path.strip('/').split('/')
        if path_parts and path_parts[0]:
            return path_parts[0]
    return None


def decode_title(encoded_title):
    if not encoded_title:
        return ""
    title = unquote(encoded_title.replace('+', ' '))
    title = title.replace('&#39;', "'").replace('&amp;', '&')
    title = title.replace('&lt;', '<').replace('&gt;', '>')
    title = title.replace('&quot;', '"')
    return title.strip()


def safe_json_loads(text):
    cleaned = text.replace("\\'", "'")
    cleaned = re.sub(r'\\(?!["\\/bfnrtu])', '', cleaned)
    return json.loads(cleaned)


async def get_posts_with_titles(blog_id, max_posts=1000):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': f'https://blog.naver.com/{blog_id}'
    }
    results = []
    current_page = 1

    print(f"\n[포스트 수집 중]")

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as c:
        while len(results) < max_posts:
            list_url = (
                f"https://blog.naver.com/PostTitleListAsync.naver"
                f"?blogId={blog_id}&currentPage={current_page}&countPerPage=30"
            )
            try:
                r = await c.get(list_url)
                if r.status_code != 200:
                    break
                data = safe_json_loads(r.text)
                post_list = data.get('postList', [])
                if not post_list:
                    break
                for post in post_list:
                    if len(results) >= max_posts:
                        break
                    log_no = post.get('logNo', '')
                    raw_title = post.get('title', '')
                    title = decode_title(raw_title)
                    url = f"https://blog.naver.com/{blog_id}/{log_no}"
                    add_date = post.get('addDate', '')
                    if title and log_no:
                        results.append({
                            'no': len(results) + 1,
                            'title': title,
                            'url': url,
                            'date': add_date
                        })
                print(f"\r  페이지 {current_page}... ({len(results)}개)", end="", flush=True)
                current_page += 1
                await asyncio.sleep(0.3)
                if current_page > 100:
                    break
            except Exception as e:
                print(f"\n  에러: {e}")
                break

    print(f"\n  완료: {len(results)}개")
    return results


async def run(url, max_posts=100):
    blog_id = extract_blog_id(url)
    if not blog_id:
        print("블로그 ID를 추출할 수 없습니다.")
        return None

    print(f"\n[대상] https://blog.naver.com/{blog_id}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': f'https://blog.naver.com/{blog_id}'
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as c:
        r = await c.get(
            f"https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={blog_id}&currentPage=1&countPerPage=1"
        )
        data = safe_json_loads(r.text)
        total = int(data.get('totalCount', 0))

    print(f"  총 {total}개 포스팅")

    results = await get_posts_with_titles(blog_id, max_posts)
    if not results:
        print("\n추출 실패")
        return None

    filename = f"naver_{blog_id}_titles.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    if os.path.exists(filepath):
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(OUTPUT_DIR, f"{name}({counter}){ext}")):
            counter += 1
        filepath = os.path.join(OUTPUT_DIR, f"{name}({counter}){ext}")

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['No', 'Title', 'URL', 'Date'])
        for r in results:
            w.writerow([r['no'], r['title'], r['url'], r.get('date', '')])

    print(f"\n[저장완료] {filepath}")
    print(f"  → 대시보드 '타이틀 관리 > 등록/CSV' 탭에서 이 파일을 드래그하세요")
    return filepath


def main():
    print("=" * 55)
    print("  네이버 블로그 타이틀 추출기")
    print("  결과: collected_titles/ 폴더")
    print("=" * 55)

    url = input("\n네이버 블로그 주소: ").strip()
    if not url:
        print("주소를 입력해주세요.")
        return
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    if 'blog.naver.com' not in url:
        print("네이버 블로그 주소가 아닙니다.")
        return

    max_input = input("추출 개수 (기본 100): ").strip()
    max_posts = int(max_input) if max_input.isdigit() else 100

    asyncio.run(run(url, max_posts))


if __name__ == "__main__":
    main()
