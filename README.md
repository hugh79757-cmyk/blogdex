# Blogdex v0.1.0

블로그 통합 관리 도구 — 14개 블로그, 5,208개 글 관리 중

## 완료된 기능

v0.1.0 (2026-02-14)

- Cloudflare D1 데이터베이스 구축
- Cloudflare Workers API 프록시 배포
- 14개 블로그 등록 (WordPress 4, Blogger 5, Hugo 4, Astro 1)
- 5,208개 글 수집 완료
- 키워드 중복 체크 (check.py)
- GA4 퍼포먼스 조회 15개 속성 (perf.py)
- Google OAuth 인증 통합

## 예정 기능

- Search Console 연동 (키워드별 클릭/노출/순위)
- CSV 타이틀 대량 임포트
- 발행 블로그 추천
- 자동 동기화 (cron)

## 사용법

cd /Users/twinssn/Projects/blogdex/cli
source venv/bin/activate

# 블로그 글 수집
python sync_wordpress.py
python sync_blogger.py
python sync_hugo.py
python sync_astro.py

# 키워드 검색
python check.py 유심

# GA4 퍼포먼스 (기본 30일)
python perf.py
python perf.py 7

## 기술 스택

- DB: Cloudflare D1 (SQLite)
- API: Cloudflare Workers (Node.js)
- CLI: Python + Rich
- 인증: Google OAuth 2.0