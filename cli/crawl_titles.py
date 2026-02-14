#!/usr/bin/env python3
"""
타이틀 추출기 - 통합 사이트맵 버전 (티스토리 + 워드프레스 + 일반)
결과 CSV는 /Users/twinssn/Projects/blogdex/cli/coupang_data/ 에 저장
"""

import asyncio
import httpx
import re
import csv
import os
from urllib.parse import urlparse

OUTPUT_DIR = "/Users/twinssn/Projects/blogdex/cli/collected_titles"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CONCURRENT = 10
TIMEOUT = 15

SKIP_PATTERNS = [
    '/category/', '/tag/', '/author/', '/page/',
    '/feed', '/rss', '/wp-json/', '/wp-content/',
    '/search/', '/archive/', '/attachment/',
    '.jpg', '.png', '.gif', '.pdf', '.css', '.js'
]

SITEMAP_PATHS = [
    '/sitemap.xml',
    '/wp-sitemap.xml',
    '/sitemap_index.xml',
    '/post-sitemap.xml',
    '/sitemap-posts.xml',
]


async def fetch_sitemap(client, url):
    try:
        r = await client.get(url)
        if r.status_code == 200 and '<?xml' in r.text[:100]:
            return r.text
    except:
        pass
    return None


async def get_urls_from_sitemap(base_url):
    base_url = base_url.rstrip('/')
    all_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as c:
        sitemap_content = None
        for path in SITEMAP_PATHS:
            url = base_url + path
            print(f"  확인 중: {path}", end="")
            content = await fetch_sitemap(c, url)
            if content:
                sitemap_content = content
                print(" OK")
                break
            print(" X")
        
        if not sitemap_content:
            print("  사이트맵을 찾을 수 없습니다.")
            return []
        
        if '<sitemapindex' in sitemap_content or '<sitemap>' in sitemap_content:
            print(f"\n  [인덱스 사이트맵 감지]")
            sub_sitemaps = re.findall(r'<loc>([^<]+\.xml[^<]*)</loc>', sitemap_content)
            post_sitemaps = [s for s in sub_sitemaps if any(k in s.lower() for k in ['post', 'entry', 'article', 'blog'])]
            if not post_sitemaps:
                post_sitemaps = [s for s in sub_sitemaps if not any(k in s.lower() for k in ['category', 'tag', 'author', 'page'])]
            
            print(f"  하위 사이트맵 {len(post_sitemaps)}개 처리 중...")
            for sub_url in post_sitemaps:
                sub_content = await fetch_sitemap(c, sub_url)
                if sub_content:
                    urls = re.findall(r'<loc>([^<]+)</loc>', sub_content)
                    urls = [u for u in urls if not u.endswith('.xml')]
                    all_urls.extend(urls)
                    print(f"    {sub_url.split('/')[-1]}: {len(urls)}개")
        else:
            all_urls = re.findall(r'<loc>([^<]+)</loc>', sitemap_content)
            all_urls = [u for u in all_urls if not u.endswith('.xml')]
    
    filtered = []
    for url in all_urls:
        url_lower = url.lower()
        if any(p in url_lower for p in SKIP_PATTERNS):
            continue
        path = urlparse(url).path
        if path in ['', '/', '/index.html', '/index.php']:
            continue
        filtered.append(url)
    
    filtered = list(dict.fromkeys(filtered))
    print(f"\n  총 {len(filtered)}개 포스트 URL 발견")
    return filtered


def clean_title(t):
    if not t:
        return ""
    for sep in [' - ', ' | ', ' :: ', ' - ', ' - ', ' : ', ' >> ']:
        if sep in t:
            parts = t.split(sep)
            t = max(parts, key=len)
    return t.strip()


async def get_titles(urls, max_pages):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    
    print(f"\n[타이틀 추출] 최대 {max_pages}개")
    
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as c:
        no = 0
        for i in range(0, min(len(urls), max_pages * 2), CONCURRENT):
            if no >= max_pages:
                break
            batch = urls[i:i+CONCURRENT]
            tasks = [c.get(u) for u in batch]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for u, r in zip(batch, responses):
                if no >= max_pages:
                    break
                if isinstance(r, Exception) or r.status_code != 200:
                    continue
                m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', r.text, re.I)
                if not m:
                    m = re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:title', r.text, re.I)
                if not m:
                    m = re.search(r'<title[^>]*>([^<]+)</title>', r.text, re.I)
                if m:
                    t = clean_title(m.group(1).strip())
                    if t and len(t) >= 3:
                        no += 1
                        results.append({'no': no, 'title': t, 'url': u})
                        print(f"\r  {no}개 완료", end="", flush=True)
            await asyncio.sleep(0.1)
    
    print(f"\n  완료: {len(results)}개")
    return results


async def crawl_homepage(base_url, max_depth=2):
    base_url = base_url.rstrip('/')
    domain = urlparse(base_url).netloc
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    visited = set()
    found_urls = []
    to_visit = [base_url]
    
    print(f"\n  [홈페이지 크롤링 모드] 깊이 {max_depth}")
    
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=headers) as c:
        for depth in range(max_depth):
            if not to_visit:
                break
            print(f"  깊이 {depth + 1}: {len(to_visit)}개 페이지 탐색 중...")
            next_visit = []
            for i in range(0, len(to_visit), CONCURRENT):
                batch = to_visit[i:i+CONCURRENT]
                tasks = [c.get(u) for u in batch if u not in visited]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for u, r in zip(batch, responses):
                    visited.add(u)
                    if isinstance(r, Exception) or r.status_code != 200:
                        continue
                    links = re.findall(r'href=["\']([^"\']+)["\']', r.text)
                    for link in links:
                        if link.startswith('/'):
                            link = base_url + link
                        elif not link.startswith('http'):
                            continue
                        if domain not in link:
                            continue
                        link_lower = link.lower()
                        if any(p in link_lower for p in SKIP_PATTERNS):
                            continue
                        path = urlparse(link).path
                        if path in ['', '/', '/index.html', '/index.php']:
                            continue
                        link = link.split('?')[0].split('#')[0]
                        if link not in visited and link not in found_urls:
                            found_urls.append(link)
                            if depth < max_depth - 1:
                                next_visit.append(link)
                await asyncio.sleep(0.1)
            to_visit = next_visit[:100]
    
    found_urls = list(dict.fromkeys(found_urls))
    print(f"  총 {len(found_urls)}개 포스트 URL 발견")
    return found_urls


async def run(url, max_pages=100):
    print(f"\n[대상] {url}")
    print(f"\n[사이트맵 검색]")
    
    urls = await get_urls_from_sitemap(url)
    if not urls:
        print("\n  [대안] 홈페이지 크롤링 시도...")
        urls = await crawl_homepage(url)
    if not urls:
        print("\n포스트를 찾을 수 없습니다.")
        return None

    total = len(urls)
    print(f"\n  총 {total}개 포스트 발견")
    
    results = await get_titles(urls, max_pages)
    if not results:
        print("\n타이틀을 추출할 수 없습니다.")
        return None
    
    domain = urlparse(url).netloc.replace('.', '_')
    filename = f"{domain}_titles.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 중복 파일명 처리
    if os.path.exists(filepath):
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(os.path.join(OUTPUT_DIR, f"{name}({counter}){ext}")):
            counter += 1
        filepath = os.path.join(OUTPUT_DIR, f"{name}({counter}){ext}")
    
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['No', 'Title', 'URL'])
        for r in results:
            w.writerow([r['no'], r['title'], r['url']])
    
    print(f"\n[저장완료] {filepath}")
    print(f"  → 대시보드 '타이틀 관리 > 등록/CSV' 탭에서 이 파일을 드래그하세요")
    return filepath


def main():
    print("=" * 55)
    print("  블로그 타이틀 추출기 (일반 사이트)")
    print("  결과: collected_titles/ 폴더")
    print("=" * 55)
    
    url = input("\n주소: ").strip()
    if not url:
        print("주소를 입력해주세요.")
        return
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    max_input = input("추출 개수 (기본 100): ").strip()
    max_pages = int(max_input) if max_input.isdigit() else 100
    
    asyncio.run(run(url, max_pages))


if __name__ == "__main__":
    main()
