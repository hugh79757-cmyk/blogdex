#!/usr/bin/env python3
"""
Blogdex 로컬 API 서버
- 경쟁사 타이틀 크롤링
- 결과를 Workers D1에 자동 저장
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
from flask_cors import CORS
import httpx
import re
import json
from urllib.parse import urlparse, unquote

app = Flask(__name__)
CORS(app)

API_URL = "https://blogdex-api.hugh79757.workers.dev"
API_KEY = "blogdex-secret-key"
TIMEOUT = 15
CONCURRENT = 10

SKIP_PATTERNS = [
    '/category/', '/tag/', '/author/', '/page/',
    '/feed', '/rss', '/wp-json/', '/wp-content/',
    '/search/', '/archive/', '/attachment/',
    '.jpg', '.png', '.gif', '.pdf', '.css', '.js'
]

SITEMAP_PATHS = [
    '/sitemap.xml', '/wp-sitemap.xml', '/sitemap_index.xml',
    '/post-sitemap.xml', '/sitemap-posts.xml',
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}


def clean_title(t):
    if not t:
        return ""
    for sep in [' - ', ' | ', ' :: ', ' : ', ' >> ']:
        if sep in t:
            parts = t.split(sep)
            t = max(parts, key=len)
    return t.strip()


def decode_naver_title(encoded):
    if not encoded:
        return ""
    title = unquote(encoded.replace('+', ' '))
    title = title.replace('&#39;', "'").replace('&amp;', '&')
    title = title.replace('&lt;', '<').replace('&gt;', '>')
    title = title.replace('&quot;', '"')
    return title.strip()


def safe_json_loads(text):
    cleaned = text.replace("\\'", "'")
    cleaned = re.sub(r'\\(?!["\\/bfnrtu])', '', cleaned)
    return json.loads(cleaned)


async def fetch_sitemap(client, url):
    try:
        r = await client.get(url)
        if r.status_code == 200 and '<?xml' in r.text[:100]:
            return r.text
    except:
        pass
    return None


async def get_sitemap_urls(base_url):
    base_url = base_url.rstrip('/')
    all_urls = []

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as c:
        sitemap_content = None
        for path in SITEMAP_PATHS:
            content = await fetch_sitemap(c, base_url + path)
            if content:
                sitemap_content = content
                break

        if not sitemap_content:
            return []

        if '<sitemapindex' in sitemap_content or '<sitemap>' in sitemap_content:
            sub_sitemaps = re.findall(r'<loc>([^<]+\.xml[^<]*)</loc>', sitemap_content)
            post_sitemaps = [s for s in sub_sitemaps if any(k in s.lower() for k in ['post', 'entry', 'article', 'blog'])]
            if not post_sitemaps:
                post_sitemaps = [s for s in sub_sitemaps if not any(k in s.lower() for k in ['category', 'tag', 'author', 'page'])]
            for sub_url in post_sitemaps:
                sub_content = await fetch_sitemap(c, sub_url)
                if sub_content:
                    urls = re.findall(r'<loc>([^<]+)</loc>', sub_content)
                    urls = [u for u in urls if not u.endswith('.xml')]
                    all_urls.extend(urls)
        else:
            all_urls = re.findall(r'<loc>([^<]+)</loc>', sitemap_content)
            all_urls = [u for u in all_urls if not u.endswith('.xml')]

    filtered = []
    for url in all_urls:
        if any(p in url.lower() for p in SKIP_PATTERNS):
            continue
        path = urlparse(url).path
        if path in ['', '/', '/index.html', '/index.php']:
            continue
        filtered.append(url)

    return list(dict.fromkeys(filtered))


async def crawl_homepage(base_url):
    base_url = base_url.rstrip('/')
    domain = urlparse(base_url).netloc
    visited = set()
    found = []
    to_visit = [base_url]

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as c:
        for depth in range(2):
            if not to_visit:
                break
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
                        if any(p in link.lower() for p in SKIP_PATTERNS):
                            continue
                        link = link.split('?')[0].split('#')[0]
                        path = urlparse(link).path
                        if path in ['', '/', '/index.html', '/index.php']:
                            continue
                        if link not in visited and link not in found:
                            found.append(link)
                            if depth < 1:
                                next_visit.append(link)
                await asyncio.sleep(0.1)
            to_visit = next_visit[:100]

    return list(dict.fromkeys(found))


async def extract_titles(urls, max_count):
    results = []
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as c:
        no = 0
        for i in range(0, min(len(urls), max_count * 2), CONCURRENT):
            if no >= max_count:
                break
            batch = urls[i:i+CONCURRENT]
            tasks = [c.get(u) for u in batch]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for u, r in zip(batch, responses):
                if no >= max_count:
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
                        results.append({'title': t, 'url': u})
            await asyncio.sleep(0.1)
    return results


async def crawl_naver(blog_id, max_count):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': f'https://blog.naver.com/{blog_id}'
    }
    results = []
    page = 1

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as c:
        # 총 개수 확인
        r = await c.get(f"https://blog.naver.com/PostTitleListAsync.naver?blogId={blog_id}&currentPage=1&countPerPage=1")
        data = safe_json_loads(r.text)
        total = int(data.get('totalCount', 0))

        while len(results) < max_count:
            r = await c.get(f"https://blog.naver.com/PostTitleListAsync.naver?blogId={blog_id}&currentPage={page}&countPerPage=30")
            if r.status_code != 200:
                break
            data = safe_json_loads(r.text)
            post_list = data.get('postList', [])
            if not post_list:
                break
            for post in post_list:
                if len(results) >= max_count:
                    break
                log_no = post.get('logNo', '')
                title = decode_naver_title(post.get('title', ''))
                if title and log_no:
                    results.append({
                        'title': title,
                        'url': f"https://blog.naver.com/{blog_id}/{log_no}"
                    })
            page += 1
            await asyncio.sleep(0.3)
            if page > 100:
                break

    return results, total


def save_to_d1(titles):
    """크롤링 결과를 Workers D1에 저장"""
    import requests
    batch = [{'title': t['title'], 'url': t.get('url', '')} for t in titles]
    try:
        r = requests.post(
            f"{API_URL}/titles",
            json={'titles': batch},
            headers={'X-API-Key': API_KEY, 'Content-Type': 'application/json'},
            timeout=30
        )
        return r.status_code == 200
    except:
        return False


@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    url = data.get('url', '').strip()
    max_count = int(data.get('max', 100))

    if not url:
        return jsonify({'error': 'URL 필요'}), 400

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        # 네이버 블로그 판별
        if 'blog.naver.com' in url:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            blog_id = path_parts[0] if path_parts and path_parts[0] else None
            if not blog_id:
                return jsonify({'error': '블로그 ID 추출 실패'}), 400

            results, total = asyncio.run(crawl_naver(blog_id, max_count))
            source = f"네이버 블로그 ({blog_id})"
            total_posts = total
        else:
            # 일반 사이트
            urls = asyncio.run(get_sitemap_urls(url))
            if not urls:
                urls = asyncio.run(crawl_homepage(url))
            if not urls:
                return jsonify({'error': '포스트를 찾을 수 없습니다', 'titles': [], 'total_posts': 0})

            total_posts = len(urls)
            results = asyncio.run(extract_titles(urls, max_count))
            domain = urlparse(url).netloc
            source = domain

        # D1에 저장
        saved = False
        if results:
            saved = save_to_d1(results)

        return jsonify({
            'source': source,
            'total_posts': total_posts,
            'crawled': len(results),
            'saved_to_db': saved,
            'titles': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'blogdex-local'})


if __name__ == '__main__':
    print("=" * 50)
    print("  Blogdex 로컬 API 서버")
    print("  http://localhost:5001")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5001, debug=False)
