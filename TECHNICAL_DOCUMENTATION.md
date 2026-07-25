# Blogdex 기술 문서 (v0.2.0)

> **프로젝트**: 블로그 통합 관리 도구 — 14개 블로그, 5,208개 글 관리  
> **GitHub**: N/A (로컬 프로젝트)  
> **작성일**: 2026-06-07

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [데이터베이스 스키마](#3-데이터베이스-스키마)
4. [API 레이어 (Cloudflare Workers)](#4-api-레이어-cloudflare-workers)
5. [CLI 도구 상세](#5-cli-도구-상세)
6. [토큰/인증 설정 상세](#6-토큰인증-설정-상세)
7. [대시보드 (React)](#7-대시보드-react)
8. [운영/배포](#8-운영배포)
9. [데드코드 레포트](#9-데드코드-레포트)
10. [부록: 파일 인벤토리](#10-부록-파일-인벤토리)

---

## 1. 프로젝트 개요

**Blogdex**는 다수의 블로그(WordPress, Blogger, Hugo, Astro)에서 글을 수집하고, Google Search Console(GSC) / Google Analytics 4(GA4) / Google AdSense 데이터를 집계하여 통합 대시보드에서 관리하는 시스템입니다.

### 주요 기능

| 기능 | 설명 | 담당 파일 |
|------|------|-----------|
| 블로그 글 수집 | WordPress/Blogger/Hugo/Astro 사이트맵 → D1 | `sync_wordpress.py`, `sync_blogger.py`, `sync_hugo.py`, `sync_astro.py` |
| 키워드 중복 검사 | 기존 포스트 중복 확인 | `check.py` |
| GSC 트래픽 분석 | Search Console 키워드/클릭/노출 | `gsc.py`, `gsc_detail.py`, `gsc_backfill.py`, `gsc_trend.py`, `gsc_snapshot.py` |
| GA4 성능 조회 | 페이지뷰/세션/광고수익 | `ga4_pageviews.py`, `perf.py`, `revenue.py` |
| 애드센스 수익 | AdSense 수익 집계 | `adsense.py`, `adsense_trend.py` |
| 글쓰기 기회 분석 | 수익 점수 기반 키워드 추천 | `analyze.py` |
| 타이틀 관리 | 타이틀 수집/매칭/상태 관리 | `titles.py`, `crawl_titles.py`, `find_best_blog.py` |
| AI 타이틀 생성 | GPT-4o-mini로 CTR 높은 타이틀 생성 | `ai_title.py` |
| 쿠팡 파트너스 | CSV 임포트/수익 분석 | `coupang.py` |
| 일일 동기화 | GSC+GA4+Bing+쿠팡+노인복지 뉴스 자동 수집 | `daily_sync.py` |
| 대시보드 | React 기반 시각화 | `dashboard/` |

### 도메인 네트워크

4개의 루트 도메인 아래에 약 80+ 서브도메인 운영:

| 루트 도메인 | 서브도메인 수 | 주요 카테고리 |
|-------------|---------------|--------------|
| `rotcha.kr` | 15 | 여행, 스포츠, 할인, 가이드, EV |
| `techpawz.com` | 10 | 금융(ETF, 배당, IPO), 여행(크루즈, 관광), IT |
| `informationhot.kr` | 12 | 정보, 주식, 부동산, 세금, 브랜드, 시니어 |
| `aikorea24.kr` | 2 | AI, 자격증 |

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Workers                        │
│  ┌─────────────────────┐  ┌──────────────────────────────┐ │
│  │   blogdex-api       │  │   blogdex-hub (hub-worker)   │ │
│  │   (메인 API 서버)    │  │   (사이트 네트워크 뷰)        │ │
│  │   src/index.js      │  │   src/index.js               │ │
│  └────────┬────────────┘  └────────┬─────────────────────┘ │
│           │                        │                       │
│  ┌────────▼────────────────────────▼──────────────────────┐ │
│  │              D1 Database (blogdex_db)                   │ │
│  │   SQLite-based, 16개 테이블                             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │ HTTPS + X-API-Key
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Python CLI (cli/)                               │
│  각종 스크립트: sync, analyze, adsense, coupang, etc.       │
│  인증: Google OAuth 2.0 pickle 토큰                         │
│  외부 API: GSC, GA4, AdSense, Naver, Bing, OpenAI, Telegram│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              React Dashboard (dashboard/)                    │
│   Vite + React 19 + Recharts + Axios                        │
│   http://localhost:5173                                     │
└─────────────────────────────────────────────────────────────┘
```

### API 통신 흐름

1. **CLI 스크립트** → `api.py` (HTTP) → `blogdex-api.workers.dev` → D1
2. **대시보드** → Axios → `blogdex-api.workers.dev` → D1
3. **blogdex-hub** (`hub-worker`) → D1 → HTML 사이트맷 렌더링 (서브도메인 목록 조회용)

### API Key 인증

모든 요청은 `X-API-Key` 헤더 필요 — `BLOGDEX_API_KEY` 환경변수 (config.py: `os.environ.get`) 및 Worker secret (env.BLOGDEX_API_KEY)에서 로드

---

## 3. 데이터베이스 스키마

### 마이그레이션 시스템 (v0.2.0 신규)

이전: 4개의 분리된 `schema*.sql` 파일을 수동 적용 → 현재: 버전 순서 마이그레이션 시스템

| 파일 | 설명 |
|------|------|
| `worker/migrations/000_migrations_table.sql` | `_migrations` 추적 테이블 (bootstrap) |
| `worker/migrations/001_initial.sql` | blogs, my_posts, collected_titles, performance |
| `worker/migrations/002_gsc_coupang.sql` | gsc_daily, gsc_keywords, coupang_revenue + indexes |
| `worker/migrations/003_ga4_sync.sql` | ga4_pageviews (**★ 최초 CREATE TABLE 정의**) + sync_log + indexes |
| `worker/migrations/004_bing_tables.sql` | bing_daily, bing_keywords + indexes |

> **발견된 문제**: `ga4_pageviews` 테이블은 기존 4개 스키마 파일 중 어디에도 CREATE TABLE이 없었음 — 코드에서만 `INSERT OR REPLACE` 사용. `003_ga4_sync.sql`에서 최초로 정의.

### 적용 방법

```bash
# Bash migrator
./worker/migrate.sh                    # production
./worker/migrate.sh --env preview      # preview

# Python migrator
python cli/db_migrate.py

# API (관리자 전용, DISABLE_ADMIN=true로 차단 가능)
curl -X POST https://blogdex-api.workers.dev/admin/migrate \
  -H "X-API-Key: $BLOGDEX_API_KEY" \
  -d '{"migration":"005_fix","sql":"CREATE TABLE IF NOT EXISTS ..."}'
```

### 전체 테이블 목록 (13개)

| 테이블 | 설명 | 마이그레이션 |
|--------|------|-------------|
| `blogs` | 블로그 등록 정보 | 001 |
| `my_posts` | 수집된 포스트 | 001 |
| `collected_titles` | 수집된 타이틀 (경쟁사 분석) | 001 |
| `performance` | 포스트별 성능 | 001 |
| `gsc_daily` | GSC 일별 요약 | 002 |
| `gsc_keywords` | GSC 키워드별 데이터 | 002 |
| `coupang_revenue` | 쿠팡 파트너스 수익 | 002 |
| `ga4_pageviews` | GA4 페이지뷰 + 수익 **★ 누락 복구** | 003 |
| `sync_log` | 동기화 로그 | 003 |
| `bing_daily` | Bing 일별 요약 | 004 |
| `bing_keywords` | Bing 키워드별 데이터 | 004 |
| `_migrations` | 마이그레이션 추적 (bootstrap) | 000 |
| `site_exposure` | 사이트 노출 추적 (Worker inline) | — |

> `news` 테이블은 `aikorea24-db` (별도 D1)에 있으므로 blogdex_db 마이그레이션에서 제외됨.

```
blogs ──1:N── my_posts ──1:N── performance
                        └──1:N── gsc_keywords (via page URL)
                                └──M:N── gsc_daily (via site+date)

collected_titles (standalone)

ga4_pageviews (site+date+page)
coupang_revenue (date+sub_id)
news (standalone)
bing_daily / bing_keywords (site+date)
```

---

## 4. API 레이어 (Cloudflare Workers)

### 4.1 blogdex-api (`worker/src/index.js`)

메인 REST API 서버. D1에 직접 접근.

#### 엔드포인트 목록

| Method | Path | 설명 |
|--------|------|------|
| GET | `/scout?q=키워드` | 네이버 블로그 검색 프록시 + 수집 타이틀 저장 |
| GET | `/blogs` | 블로그 목록 |
| POST | `/blogs` | 블로그 등록 |
| POST | `/posts` | 포스트 배치 저장 |
| POST | `/posts/update-urls` | 포스트 URL 일괄 업데이트 |
| GET | `/posts/search?q=&blog_id=` | 포스트 검색 (키워드 LIKE) |
| POST | `/titles` | 타이틀 배치 저장 |
| GET | `/titles/search?q=` | 타이틀 검색 (발행 블로그 매칭 포함) |
| PUT | `/titles/status` | 타이틀 상태 업데이트 |
| GET | `/titles/stats` | 타이틀 상태 통계 |
| GET | `/titles/sources` | 타이틀 출처 목록 |
| GET | `/titles/filter?status=&page=&source=` | 타이틀 필터 조회 (페이지네이션) |
| GET | `/titles/detail/:id` | 타이틀 상세 |
| POST | `/titles/match` | 타이틀 → 발행 블로그 매칭 |
| POST | `/titles/recommend` | 타이틀 최적 블로그 추천 |
| PUT | `/titles/bulk-status` | 타이틀 상태 일괄 변경 |
| POST | `/performance` | 성능 데이터 저장 |
| GET | `/performance?days=` | 성능 데이터 조회 |
| POST | `/gsc/daily` | GSC 일별 데이터 저장 |
| GET | `/gsc/daily?days=&site=` | GSC 일별 조회 |
| GET | `/gsc/sites?days=` | GSC 사이트별 요약 |
| POST | `/gsc/keywords` | GSC 키워드 저장 |
| GET | `/gsc/keywords?days=` | GSC 키워드 조회 (블로그명 매칭 포함) |
| GET | `/gsc/keywords/trend?q=&days=` | 키워드 트렌드 |
| POST | `/coupang` | 쿠팡 수익 저장 |
| GET | `/coupang/summary?days=` | 쿠팡 일별/합계 |
| GET | `/coupang/by-sub?days=` | 쿠팡 서브ID별 |
| POST | `/ga4/pageviews` | GA4 페이지뷰 저장 |
| GET | `/dashboard/summary?days=` | 대시보드 요약 통계 |
| GET | `/analysis/rewrite-targets` | CTR=0인 리라이트 대상 |
| GET | `/analysis/top-pages` | GA4 TOP 페이지 |
| GET | `/analysis/seo-opportunity` | GA4 있음/GSC 없음 기회 |
| GET | `/analysis/blog-efficiency` | 블로그별 PV/페이지 효율 |
| GET | `/analysis/rpm-ranking` | RPM 랭킹 |
| GET | `/analysis/revenue-summary` | 수익 요약 (오늘/어제/7일/이번달) |
| POST | `/bing/daily` | Bing 일별 저장 |
| POST | `/bing/keywords` | Bing 키워드 저장 |

#### API 특이사항

- **CORS**: `ALLOWED_ORIGINS` allowlist 기반 — `["localhost:5173", "localhost:5174"]` + 미허용 origin은 403
- **인증**: `X-API-Key` — `env.BLOGDEX_API_KEY` (Worker secret, 하드코딩 제거됨)
- **보안 응답 헤더**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`
- **요청 크기 제한**: `content-length > 1MB → 413 Payload too large`
- **에러 메시지**: `e.message` → `"Internal server error"` + `console.error(e)` (클라이언트에 스택 노출 방지)
- **JSON 응답**: `JSON.stringify(data, null, 2)`로 예쁜 출력
- **D1 batch 제한**: 한 번에 최대 100개 처리, 100 초과시 분할

### 4.2 blogdex-hub (`hub-worker/src/index.js`)

사이트 네트워크 조회용 허브 서버.

- `rotcha.kr/sites` — rotcha.kr 네트워크의 15개 서브도메인 & 최신 5개 글
- `techpawz.com/sites` — techpawz.com 네트워크 (10개)
- `informationhot.kr/sites` — informationhot.kr 네트워크 (12개)
- `aikorea24.kr/sites` — aikorea24.kr 네트워크 (2개)
- `robots.txt` 동적 생성
- `sitemap.xml` 동적 생성

#### 라우팅

각 루트 도메인은 `wrangler.toml`의 `[[routes]]` 패턴으로 매핑:

| 패턴 | Zone ID |
|------|---------|
| `rotcha.kr/sites` | `5cb878722c6bed8eecb2f2741bdefa29` |
| `techpawz.com/sites` | `91b519df79982e30bc52e28822a86fe2` |
| `informationhot.kr/sites` | `76d0599a7e05203168fd8fe1cfae4bd4` |
| `aikorea24.kr/sites` | `a6d9e75032c8cefe316b06d46a90a431` |

---

## 5. CLI 도구 상세

### 5.1 공통 모듈

#### `cli/config.py` (v0.2.0 리팩터)
```python
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
API_URL = "https://blogdex-api.hugh79757.workers.dev"
API_KEY = os.environ.get("BLOGDEX_API_KEY")  # ← 하드코딩 제거
PUBLISH_CONFIG = os.environ.get("BLOGDEX_PUBLISH_CONFIG", str(PROJECT_ROOT / "publish_config.yaml"))
CSV_DIR = os.environ.get("BLOGDEX_CSV_DIR", str(PROJECT_ROOT / "sitemap-title"))
```
- `BLOGDEX_API_KEY` 누락 시 `RuntimeError`
- `PUBLISH_CONFIG` / `CSV_DIR` 누락 시 `warnings.warn()` (경고, 진행은 계속)

#### `cli/api.py`
공통 HTTP 래퍼 — `get()` / `post()` 메서드 제공. 모든 요청에 `X-API-Key` 헤더 자동 첨부.

#### `cli/sync_utils.py`
중복 방지 유틸리티:
- `get_existing_posts(blog_id)` — DB 기존 포스트 제목 Set 로드
- `save_new_posts(all_posts, existing, name)` — 신규만 필터링 후 100개씩 배치 저장

### 5.2 주요 CLI 스크립트

#### `check.py` — 키워드 중복 검사
```
python check.py <키워드>
```
- Workers API `GET /posts/search?q=키워드` 호출
- 결과를 Rich 테이블로 표시
- 결과 0건 → "[bold green]쓴 적 없음! 새로운 주제입니다"

#### `analyze.py` — 수익 기반 글쓰기 기회 분석
```
python analyze.py [일수=30]
```
1. GSC 스냅샷 디렉토리(`snapshots/`)에서 최근 N일치 키워드 집계
2. 내 포스트 제목 로딩 (`GET /posts/search`)
3. 수집 타이틀 로딩 (`GET /titles/search`)
4. **수익 점수 = 예상월클릭 × 가중치** 계산:
   - 고가치 패턴(추천/비교/가격/후기 등): x3.0
   - 중간: x1.0
   - 저가치(뜻/의미/영어로 등): x0.3
   - 이미 작성: x0.1 패널티
   - 수집 타이틀 있음: x1.3 가중
   - 순위 5~20위: x1.5 가중
5. 새 글 기회 / 기존 글 개선 각각 TOP 테이블 출력

#### `coupang.py` — 쿠팡 파트너스 수익 분석
```
python coupang.py import [파일]     # CSV 임포트
python coupang.py summary            # 수익 요약
python coupang.py match              # GSC 키워드 매칭
```
- CSV 컬럼 자동 감지 (날짜/클릭/주문/수익)
- 로컬 JSON(`coupang_history.json`)에 누적 저장

#### `ga4_pageviews.py` — GA4 페이지뷰 + 광고수익
```
python ga4_pageviews.py [일수=30]
```
- 25개 GA4 속성에서 페이지뷰/세션/광고수익 수집
- 로컬 스냅샷 저장 + Workers D1 업로드

#### `daily_sync.py` — 일일 자동 동기화 (v0.2.0 리팩터)
```
python daily_sync.py [--skip-gsc --skip-ga4 --skip-coupang --skip-bing --skip-senior]
```
**아키텍처**: 태스크 러너 패턴 — 각 동기화 단계가 `run_task()`로 격리되어 실행되며, 한 단계가 실패해도 나머지는 계속 진행됩니다.

**실행 순서:**
1. **GSC 동기화** (`@retry(3, 5s)`) — 87개 사이트 GSC 데이터 → 스냅샷 + D1
2. **GA4 페이지뷰** (`@retry(3, 5s)`) — 61개 GA4 속성 수집
3. **Bing 동기화** — Bing Webmaster API → `bing_daily` / `bing_keywords`
4. **노인복지 뉴스** — 네이버 뉴스 10개 쿼리 검색
5. **포스트 동기화** — Hugo/Astro/WordPress/Blogger 동기화
6. **Indexing API** — Google Indexing API URL 제출
7. **쿠팡 수익** — Workers API 호출
8. **SyncMonitor 저장** — JSONL 리포트 저장 → `logs/sync_report.jsonl`

**재시도**: `@retry` 데코레이터 — 3회, exponential backoff (5초 → 10초 → 20초), GSC/GA4에 적용
**에러 격리**: 각 태스크는 `run_task()` 래퍼로 try/except 격리
**모니터링**: `SyncMonitor` 클래스가 각 스텝의 상태/소요시간 기록, 실패 시 즉시 Telegram 알림

#### `cli/monitor.py` — SyncMonitor (v0.2.0 신규)
```python
from monitor import SyncMonitor, check_data_quality
monitor = SyncMonitor(pipeline_name="Blogdex Daily Sync")
monitor.record("gsc", "ok", "87사이트 수집 완료", {"count": 1234})
monitor.send_daily_report()   # Telegram + Console 요약
monitor.save_report()         # logs/sync_report.jsonl (JSONL 형식)
```

| 기능 | 설명 |
|------|------|
| `record(step, status, msg, data)` | 스텝 결과 기록 + 실패 시 즉시 Telegram 알림 |
| `send_daily_report()` | 일일 종합 리포트 (Telegram HTML + Console plain) |
| `save_report()` | JSONL 파일 저장 (로그 파싱/분석 가능) |
| `check_data_quality(monitor, step, count)` | 수집 건수가 `EXPECTED_MINIMUMS` 미만이면 warning/error |

**데이터 품질 기준**:
| 스텝 | 최소 기대치 | 초과 시 |
|------|------------|---------|
| gsc | 50건 | warning / error(0건) |
| ga4 | 30건 | warning / error(0건) |
| bing | 5건 | warning |
| coupang | 1건 | warning |
| senior | 1건 | warning |

**즉시 알림**: 에러 발생 시 지체 없이 Telegram 전송 (`🚨 [Blogdex] gsc 실패: ...`)

#### `scripts/parse_sync_report.py` — JSONL 리포트 리더 (v0.2.0 신규)
```
python scripts/parse_sync_report.py           # 최근 10회
python scripts/parse_sync_report.py --last 7  # 최근 7회
python scripts/parse_sync_report.py --watch   # tail -f 모드
python scripts/parse_sync_report.py --consecutive 3  # 연속 실패 감지
```

#### `gsc.py` — Search Console 전체 요약
```
python gsc.py [일수=30]
```
- sc-domain(도메인 속성)과 URL 속성 중복 제외 필터링
- 사이트별 클릭/노출/CTR/순위 요약

#### `gsc_detail.py` — 사이트별 상세 GSC 분석
```
python gsc_detail.py <사이트URL> [일수=30]
```
- 키워드 분석 TOP 25 + CTR 진단
- 페이지별 성과 TOP 15

#### `gsc_trend.py` — 신생 블로그 노출 추이
```
python gsc_trend.py [필터=-hugo]
```
- 2주전/1주전/어제 3시점 노출/클릭 비교
- 추세 화살표 표시 (▲ ▼ ─)

#### `adsense.py` — 애드센스 수익 요약
```
python adsense.py [일수=7]
```
- 3개 계정(twinssn/informationhot/aikorea24) AdSense API 연동
- 사이트별 노출/클릭/CTR/수익/RPM

#### `local_api.py` — 로컬 Flask API 서버
```
python local_api.py
# Flask on port 5001
```
- Kiwi 형태소 분석기로 키워드 추출
- 경쟁사 타이틀 크롤링

---

## 6. 토큰/인증 설정 상세

### 6.1 토큰/인증 파일 인벤토리

| 파일 | 용도 | 위치 | 포맷 | 만료/갱신 |
|------|------|------|------|-----------|
| `token_1_twinssn.pickle` | Google OAuth (twinssn 계정) | `credentials/` | pickle (OAuth2Credentials) | 1시간, refresh_token 자동 갱신 |
| `token_2_informationhot.pickle` | Google OAuth (informationhot) | `credentials/` | pickle | 1시간 |
| `token_3_aikorea24.pickle` | Google OAuth (aikorea24) | `credentials/` | pickle | 1시간 |
| `adsense_token_1_twinssn.pickle` | AdSense 전용 (twinssn) | `credentials/` | pickle | 1시간 |
| `adsense_token_2_informationhot.pickle` | AdSense 전용 (informationhot) | `credentials/` | pickle | 1시간 |
| `adsense_token_3_aikorea24.pickle` | AdSense 전용 (aikorea24) | `credentials/` | pickle | 1시간 |
| `google_token.pickle` | 구형 단일 토큰 (확인 필요) | `cli/` | pickle | 1시간 |
| `client_secret_hugh7973.json` | Google OAuth 클라이언트 시크릿 (메인) | `cli/` | JSON | 영구 |
| `client_secret_540....json` | Google OAuth 클라이언트 시크릿 (백업) | `credentials/` | JSON | 영구 |
| `ADSENSE_CREDENTIALS_1twinssn.json` | AdSense OAuth 클라이언트 시크릿 (twinssn) | `credentials/` | JSON | 영구 |
| `ADSENSE_CREDENTIALS_2informationhot.json` | AdSense OAuth 클라이언트 시크릿 (informationhot) | `credentials/` | JSON | 영구 |
| `ADSENSE_CREDENTIALS_3aikorea24.json` | AdSense OAuth 클라이언트 시크릿 (aikorea24) | `credentials/` | JSON | 영구 |
| `cli/.env` | 텔레그램 봇 토큰, Bing API 키 | `cli/` | key=value | 영구 (수동 변경) |
| 루트 `.env` | OpenAI API 키 | 루트 | key=value | 영구 |
| `api_test/.env.sh` | 네이버 API 키 (aikorea24) | 외부 경로 | shell export | 영구 |

### 6.2 Google OAuth 인증 흐름

`google_auth.py`가 코어 OAuth 로직을 담당:

```
1. pickle 토큰 파일 존재? → deserialize → creds
2. creds 유효? → 사용
3. creds 만료 + refresh_token 있음? → refresh(Request()) → pickle 저장
4. creds 없음 or refresh 실패? → flow.run_local_server(port=0) → 새 토큰 → pickle 저장
```

**SCOPES** (6개):
- `analytics.readonly` — GA4 읽기
- `analytics.edit` — GA4 편집
- `webmasters` — Search Console
- `blogger.readonly` — Blogger 읽기
- `indexing` — Google Indexing API
- `siteverification` — 사이트 소유권 확인

**주의사항**:
- AdSense는 서로 다른 OAuth 자격증명(별도 클라이언트 시크릿) 사용
- `adsense.py`는 `adsense_token_*.pickle` 사용
- `ga4_pageviews.py`, `gsc*.py`, `revenue.py` 등은 `token_1_twinssn.pickle` 공유
- `daily_sync.py`는 `get_credentials()` 호출 (동일한 `token_1_twinssn.pickle` 사용)

### 6.3 토큰 파일별 권한 범위

| 토큰 | GA4 Read | GA4 Edit | GSC | Blogger | Indexing | SiteVer | AdSense |
|------|----------|----------|-----|---------|----------|---------|---------|
| `token_1` / `google_token.pickle` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `adsense_token_1` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `adsense_token_2` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `adsense_token_3` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 6.4 API 키 설정 요약

| 키 | 출처 | 사용처 | 보안 수준 |
|----|------|--------|----------|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | `.env.sh` (aikorea24) | `daily_sync.py` (노인복지), `worker/src/index.js` (스카우트) | Worker env vars |
| `OPENAI_API_KEY` | 루트 `.env` | `ai_title.py` | 환경변수 |
| `TELEGRAM_BOT_TOKEN` | `cli/.env` | `daily_sync.py` / `monitor.py` | 환경변수 |
| `BING_API_KEY` / `BING_API_KEY_2` / `BING_API_KEY_3` | `cli/.env` | `daily_sync.py` | 환경변수 |
| `BLOGDEX_API_KEY` | `cli/.env` / Worker secret | config.py → api.py → 모든 Workers API | ✅ **환경변수** (하드코딩 제거) |
| `BLOGDEX_PUBLISH_CONFIG` | `cli/.env` | config.py → publish 설정 경로 | 환경변수 |
| `BLOGDEX_CSV_DIR` | `cli/.env` | config.py → CSV 타이틀 디렉토리 | 환경변수 |

### 6.5 토큰 보안 평가 (v0.2.0 개선)

| 취약점 | v0.1.0 상태 | v0.2.0 상태 |
|--------|------------|------------|
| 토큰 포맷 | **pickle** (역직렬화 RCE 위험) | ✅ **JSON** (`Credentials.from_authorized_user_file`) |
| 토큰 저장 | 단순 덮어쓰기 | ✅ **원자적 쓰기** (tempfile → os.replace) + `fcntl.flock` 파일 잠금 |
| API 키 | **하드코딩** (`blogdex-secret-key` in config.py) | ✅ **환경변수** (`BLOGDEX_API_KEY` from os.environ/Worker secret) |
| CORS | `Access-Control-Allow-Origin: *` | ✅ **Allowlist** (localhost:5173, 5174) + 미허용 origin 403 |
| 에러 메시지 | `e.message` 노출 | ✅ `"Internal server error"` + 서버 로깅 |
| 요청 크기 | 제한 없음 | ✅ 1MB 제한 (413 Payload too large) |
| 응답 헤더 | 없음 | ✅ `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` |
| 비밀번호/토큰 파일 | `.gitignore` 불완전 | ✅ token 파일 + client secret + pickle bak 명시적 차단 |
| Naver 키 누수 | `has_id: true` 노출 | ✅ 제거됨 |
| 파일 잠금 | 없음 (갱신 경합) | ✅ `fcntl.flock` (LOCK_SH/LOCK_EX) |

### 6.6 토큰 갱신 구조 (v0.2.0)

```mermaid
CLI 스크립트 시작
  │
  ▼
google_auth.get_credentials()
  │
  ├─ pickle 파일 로드
  │
  ├─ creds.valid? ──Yes──▶ 사용
  │     │
  │     No
  │     ▼
  ├─ creds.expired + refresh_token? ──Yes──▶ creds.refresh(Request())
  │     │                                          │
  │     No                                         ▼
  │     ▼                                   pickle 저장 (갱신)
  └─ flow.run_local_server(port=0)
        │
        ▼
     새 토큰 → pickle 저장
```

---

## 7. 대시보드 (React)

### 7.1 기술 스택

| 항목 | 세부사항 |
|------|---------|
| 프레임워크 | React 19 |
| 빌드 도구 | Vite 7 |
| HTTP 클라이언트 | Axios 1.13 |
| 차트 | Recharts 3.7 |
| 언어 | JavaScript (JSX) |
| 라우팅 | **탭 기반** (SPA, React.lazy lazy loading) |

### 7.2 컴포넌트 구조 (v0.2.0 리팩터)

```
dashboard/src/
├── App.jsx                     (43줄)  ← 2003→43줄 (-98%)
├── api.js                      Axios 클라이언트 + VITE_BLOGDEX_API_KEY
├── hooks/
│   ├── useDashboardData.js     대시보드 4개 API 병렬 호출
│   └── useApiQuery.js          Generic fetch hook (loading/error/data/refetch)
├── pages/                      (13개, React.lazy 로딩)
│   ├── Dashboard.jsx           실제 API 데이터 기반 메인 대시보드
│   ├── RevenuePage.jsx         수익 분석 (완전 추출)
│   ├── CoachingPage.jsx        오늘의 코칭 (skeleton)
│   ├── OpportunityPage.jsx     수익 기회 (skeleton)
│   ├── TitleCollectPage.jsx    타이틀 수집 (skeleton)
│   ├── TitleManagePage.jsx     타이틀 관리 (skeleton)
│   ├── KeywordPage.jsx         키워드 (skeleton)
│   ├── SitePage.jsx            사이트별 (skeleton)
│   ├── RewritePage.jsx         리라이트 큐 (skeleton)
│   ├── KeywordCheckPage.jsx    키워드 체크 (skeleton)
│   ├── PublishPage.jsx         발행 배정 (skeleton)
│   ├── ScoutPage.jsx           스카우트 (skeleton)
│   └── SeniorPage.jsx          노인복지 (skeleton)
└── components/
    ├── TabNav.jsx              탭 네비게이션 (추출)
    ├── DataTable.jsx           재사용 가능 정렬 테이블 (+ useSortable)
    ├── StatCard.jsx            통계 카드 (추출)
    ├── LoadingSpinner.jsx      로딩 상태
    ├── ErrorMessage.jsx        에러 상태
    ├── DashboardLayout.jsx     레이아웃
    ├── RevenueChart.jsx        수익 차트 (data prop, empty state)
    ├── UserStats.jsx           실제 통계 (클릭/노출/CTR/블로그 수)
    └── RecentActivity.jsx      최근 활동
```

### 7.3 App.jsx (Shell, 43줄)

```javascript
import React, { useState, Suspense } from 'react';
import TabNav from './components/TabNav';
import LoadingSpinner from './components/LoadingSpinner';

const RevenuePage = React.lazy(() => import('./pages/RevenuePage'));
// ... 12개 lazy import ...
const PAGES = [CoachingPage, RevenuePage, ..., SeniorPage];

function App() {
  const [tab, setTab] = useState(0);
  const ActivePage = PAGES[tab];
  return (
    <div>
      <h1>Blogdex</h1>
      <TabNav activeTab={tab} onTabChange={setTab} />
      <Suspense fallback={<LoadingSpinner />}>
        <ActivePage />
      </Suspense>
    </div>
  );
}
```

### 7.4 useApiQuery — Generic Fetch Hook

```javascript
const { data, loading, error, refetch } = useApiQuery(
  '/gsc/keywords',
  { days: 30 },
  [days]      // deps → days 변경 시 auto-refetch
);
```

- **Parallel query**: `useDashboardData(days)` → 4개 API 병렬 호출 (`Promise.all`)
- **Auto-refetch**: deps 배열이 변경되면 자동 재요청
- **수동 갱신**: `refetch()` 호출로 강제 재요청
- **상태**: `loading` / `error` / `data` (null 체크 필요)

### 7.5 DataTable — 재사용 가능 정렬 테이블

```javascript
<DataTable
  columns={[
    { key: 'site', label: '사이트', render: (r) => <a href={...}>{r.site}</a> },
    { key: 'clicks', label: '클릭', align: 'right' },
    { key: 'impressions', label: '노출', align: 'right' },
  ]}
  data={data}
  sortable={true}
  onRowClick={(row) => handleClick(row)}
  emptyMessage="데이터 없음"
/>
```

### 7.6 데이터 흐름 (v0.2.0 변경)

- **Before**: `Dashboard.jsx` 100% Mock 데이터 (`Math.random()`)
- **After**: `useDashboardData` 훅이 4개 API 실시간 호출
  - `GET /dashboard/summary?days=N` → UserStats (클릭/노출/CTR/블로그/글 수/쿠팡 수익)
  - `GET /analysis/revenue-summary` → RevenueChart (daily_revenue → {date, rev, pv})
  - `GET /gsc/daily?days=N` → (reserved)
  - `GET /coupang/summary?days=N` → 쿠팡 수익 카드
- **Empty state**: RevenueChart는 `data.length === 0` → "데이터 없음" 표시
- **Loading state**: Suspense + LoadingSpinner
- **Error state**: ErrorMessage (에러 메시지 + 연결 안내)

---

## 8. 운영/배포

### 8.1 Workers 배포

```bash
# blogdex-api 배포 (BLOGDEX_API_KEY secret 필수)
cd worker
npx wrangler secret put BLOGDEX_API_KEY
npx wrangler deploy

# blogdex-hub 배포
cd hub-worker
npx wrangler deploy
```

### 8.2 Worker 보안 설정 (v0.2.0)

```bash
# CORS + Admin 설정
npx wrangler secret put BLOGDEX_API_KEY       # API 인증 키
npx wrangler secret put DISABLE_ADMIN          # "true"로 설정 시 /admin/* 엔드포인트 차단
```

### 8.3 Hugo 사이트 배포 (GA4 태그 삽입)

`deploy_ga4.sh` — 40+ Hugo 사이트 빌드 + Cloudflare Pages 배포 (단순 배치 스크립트)

### 8.4 로컬 개발 서버

```bash
./start.sh
# 또는
cd cli && source venv/bin/activate && python local_api.py &
cd dashboard && npm run dev
```

### 8.5 Cron 자동 설정 (v0.2.0)

```bash
# 대화형 crontab 설정 (Python/로그 경로 자동 감지)
bash scripts/setup_cron.sh

# dry-run 모드 (변경 없이 미리보기)
bash scripts/setup_cron.sh --dry-run

# 결과: crontab에 추가된 항목
# 0 1 * * * cd /path/to/blogdex && .../python3 cli/daily_sync.py >> logs/daily_sync.log 2>&1
```

- **중복 방지**: `# blogdex-daily-sync` 태그로 기존 항목 검사 (이미 있으면 스킵)
- **idempotent**: 여러 번 실행해도 안전
- **한국 시간**: 매일 01:00 UTC → 한국 10:00 실행

### 8.6 D1 마이그레이션 (v0.2.0)

```bash
# Bash migrator
./worker/migrate.sh                    # production
./worker/migrate.sh --env preview      # preview

# Python migrator
python cli/db_migrate.py
```

모든 CREATE TABLE에 `IF NOT EXISTS` 보장. `_migrations` 테이블이 적용 내역 추적.

### 8.7 Health Check (v0.2.0)

```bash
# 5개 항목 검사
python scripts/health_check.py
python scripts/health_check.py --verbose

# exit 0 = all pass, exit 1 = any fail (모니터링/CI 연동 가능)
```

**검사 항목**:
1. ✅ API 연결 (`GET /dashboard/summary` 200)
2. ✅ 환경변수 (`BLOGDEX_API_KEY`, 토큰 파일)
3. ✅ OAuth 토큰 파일 존재
4. ✅ 로그 파일 최신성 (25시간 이내)
5. ✅ D1 데이터 최신성 (`/gsc/daily` 오늘 데이터)

### 8.8 Logrotate (v0.2.0)

```bash
sudo cp scripts/logrotate.conf /etc/logrotate.d/blogdex
sudo sed -i '' "s|/PATH/TO/BLOGDEX|$(pwd)|g" /etc/logrotate.d/blogdex
```

- 일별 로그 로테이션, 30~90일 보관, 압축

### 8.9 환경변수 의존성 (v0.2.0)

| 경로 | 파일 | 주요 변수 |
|------|------|-----------|
| 루트 | `.env` | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `cli/` | `.env` | `BLOGDEX_API_KEY` (필수), `BLOGDEX_PUBLISH_CONFIG`, `BLOGDEX_CSV_DIR`, `TELEGRAM_*`, `BING_*` |
| `dashboard/` | `.env` | `VITE_BLOGDEX_API_KEY` (필수) |
| Worker secret | `wrangler secret` | `BLOGDEX_API_KEY` (필수) |
| `aikorea24/api_test/` | `.env.sh` | 네이버 API (노인복지) |

---

## 9. 데드코드 레포트

### 9.0 정리 도구 (v0.2.0 신규)

```bash
# 1. import 관계 분석 (안전 삭제 가능 여부)
python scripts/check_imports.py

# 2. 삭제 전 미리보기
bash scripts/cleanup_dead_code.sh --dry-run

# 3. 실제 삭제 (확인 후 진행)
bash scripts/cleanup_dead_code.sh

# 4. 일회성 스크립트 → cli/archive/ 로 이동
bash scripts/archive_scripts.sh
```

### 9.1 백업 파일 (cleanup_dead_code.sh 삭제 대상)
| `cli/google_token.pickle.bak.20260319` | ~2KB | 날짜별 토큰 백업 |
| `backup2.py` | ~10KB | 프로젝트 백업 스크립트 v2 |
| `backup3.py` | ~15KB | 프로젝트 백업 스크립트 v3 |
| `backup3 2.py` | ~15KB | backup3.py의 복사본 (파일명에 공백) |
| `backup_20260227_134358.txt` | ~? | 전체 코드 덤프 |
| `backup_20260228_085016.txt` | ~? | 전체 코드 덤프 |
| `backup_20260325_135408.txt` | ~? | 전체 코드 덤프 |

### 9.2 이전 스냅샷 중복

| 경로 | 설명 |
|------|------|
| `cli/snapshots_backup/` | snapshots/ 디렉토리의 완전한 복사본 (동일한 날짜 범위) |
| `cli/snapshots/empty_backup/` | 0건 데이터 스냅샷 (2026-02-12 ~ 03-15) |

### 9.3 일회성/실험적 스크립트

| 파일 | 설명 | 상태 |
|------|------|------|
| `cli/spam_cleanup.py` | tistory.com 스팸 URL 감지/삭제 | **일회성** — 스팸 정리 완료 후 불필요 |
| `cli/spam_cleanup2.py` | spam_cleanup.py의 변형 | **일회성** — 중복 |
| `cli/spam_inspect.py` | 스팸 URL 인스펙션 | **일회성** — 작업 완료 |
| `cli/ga4_inject.py` | Hugo 사이트 GA4 측정ID 삽입 | **일회성** — 이미 삽입 완료 |
| `cli/ga4_inject2.py` | ga4_inject.py 변형 | **일회성** — 중복 |
| `cli/ga4_audit.py` | GA4 속성 감사 | **일회성** — 감사 완료 |
| `cli/ga4_cleanup.py` | GA4 속성 정리 | **일회성** — 정리 완료 |
| `cli/ga4_measurement_ids.py` | GA4 측정ID 조회 | **일회성** |

### 9.4 작업 로그/결과 파일

| 파일 | 설명 | 상태 |
|------|------|------|
| `cli/deploy_ga4_result.txt` | GA4 배포 결과 로그 | **로그 — 보관 불필요** |
| `cli/deploy_v2_result.txt` | v2 배포 결과 | **로그** |
| `cli/deploy_v3_result.txt` | v3 배포 결과 | **로그** |
| `cli/ga4_audit_result.txt` | GA4 감사 결과 | **로그** |
| `cli/ga4_inject_result.txt` | GA4 인젝션 결과 | **로그** |
| `cli/ga4_inject2_result.txt` | GA4 인젝션2 결과 | **로그** |
| `cli/ga4_measurement_ids_result.txt` | 측정ID 조회 결과 | **로그** |
| `cli/redeploy_result.txt` | 재배포 결과 | **로그** |
| `cli/redeploy2_result.txt` | 재배포2 결과 | **로그** |
| `cli/backfill2.log` | GSC 백필 로그 | **로그** |
| `cli/spam_report.json` | 스팸 리포트 | **1회성 산출물** |
| `cli/spam_urls_for_removal.txt` | 삭제용 스팸 URL 목록 | **1회성 산출물** |

### 9.5 미사용/중복 기능 스크립트

| 파일 | 설명 | 상태 |
|------|------|------|
| `cli/gsc_snapshot.py` | GSC 스냅샷 수집 (gsc_backfill.py와 중복) | **중복** |
| `cli/gsc_backfill_pages.py` | GSC 페이지별 백필 | **실험적** |
| `cli/upload_snapshots.py` | 스냅샷 D1 업로드 (daily_sync.py가 대체) | **대체됨** |
| `cli/crawl_naver.py` | 네이버 크롤링 (daily_sync.py/sync_senior()가 대체) | **대체됨** |
| `cli/title.py` | 단일 파일 타이틀 도구 (titles.py와 중복) | **중복** |
| `cli/keyword_value.py` | 키워드 가치 분석 (analyze.py가 대체) | **대체됨** |
| `cli/revenue.py` | GA4 수익 TOP 글 (ga4_pageviews.py + perf.py와 중복) | **중복** |
| `cli/summary.py` | 전체 현황 요약 (dashboard/summary API가 대체) | **대체됨** |
| `cli/list_gsc.py` | GSC 사이트 목록 (gsc.py가 대체) | **대체됨** |
| `cli/list_ga4.py` | GA4 속성 목록 (일회성 조회) | **일회성** |
| `cli/verify.py` | API 연결 확인 (개발용) | **개발용** |
| `cli/daily_sync.py.patch` | 패치 파일 | **잔여물** |

### 9.6 대시보드 데드코드

| 항목 | 설명 |
|------|------|
| `Dashboard.jsx` | **Mock 데이터**만 사용 — 실제 API 연동 없음 |
| `DashboardLayout.jsx` | 미사용 컴포넌트 (App.jsx에서 사용하지 않음 가능성) |
| `RecentActivity.jsx` | Mock 데이터 전용 |
| `UserStats.jsx` | Mock 데이터 전용 |
| `App.jsx.bak`, `App.jsx.bak2` | 백업 파일 |

### 9.7 데드코드 정리 제안

**즉시 삭제 가능** (안전):
```
rm -rf cli/snapshots_backup/
rm -rf cli/snapshots/empty_backup/
rm -f cli/*.bak cli/*.bak.*
rm -f cli/*_result.txt
rm -f cli/*_log.txt cli/backfill*.log
rm -f cli/google_token.pickle.bak*
rm -f backup*.py backup*.txt
rm -f "backup3 2.py"
rm -f cli/daily_sync.py.patch
```

**검토 후 삭제** (다른 스크립트에서 import하는지 확인 필요):
- `cli/gsc_snapshot.py` — `gsc_backfill.py`로 대체
- `cli/revenue.py` — `ga4_pageviews.py` + `perf.py`로 커버
- `cli/title.py` — `titles.py`로 대체
- `cli/keyword_value.py` — `analyze.py`로 대체
- `cli/list_gsc.py`, `cli/list_ga4.py` — 일회성
- `cli/verify.py` — 개발용

**보존 권장** (참조/재사용 가능):
- `cli/spam_cleanup.py` — 유사 스팸 공격 대비 템플릿
- `cli/ga4_inject.py` — 신규 Hugo 사이트 GA4 설정 참조
- `cli/index_submit.py` — Google Indexing API 재사용 가능

---

## 10. 부록: 파일 인벤토리

### 프로젝트 루트

| 파일 | 용도 |
|------|------|
| `README.md` | 프로젝트 개요 문서 |
| `.gitignore` | Git 제외 패턴 |
| `requirements.txt` | Python 의존성 |
| `start.sh` | 로컬 API + 대시보드 시작 스크립트 |
| `backup2.py`, `backup3.py`, `backup3 2.py` | 코드 백업 스크립트 (데드코드) |
| `backup_*.txt` | 전체 코드 덤프 (데드코드) |

### `cli/` — Python CLI 도구 (핵심)

| 파일 | 용도 | 상태 |
|------|------|------|
| `config.py` | 환경설정 (API URL/KEY) | ✅ 활성 |
| `api.py` | HTTP API 래퍼 | ✅ 활성 |
| `google_auth.py` | Google OAuth 2.0 인증 | ✅ 활성 |
| `check.py` | 키워드 중복 검사 | ✅ 활성 |
| `analyze.py` | 수익 기반 글쓰기 기회 분석 | ✅ 활성 |
| `daily_sync.py` | 일일 자동 동기화 (GSC+GA4+Bing+쿠팡+뉴스+텔레그램) | ✅ 활성 |
| `ga4_pageviews.py` | GA4 페이지뷰 + 수익 수집 | ✅ 활성 |
| `gsc.py` | Search Console 전체 요약 | ✅ 활성 |
| `gsc_detail.py` | 사이트별 상세 GSC 분석 | ✅ 활성 |
| `gsc_backfill.py` | GSC 과거 스냅샷 백필 | ✅ 활성 |
| `gsc_trend.py` | 신생 블로그 노출 추이 | ✅ 활성 |
| `adsense.py` | 애드센스 수익 요약 | ✅ 활성 |
| `adsense_trend.py` | 애드센스 수익 추이 | ✅ 활성 |
| `coupang.py` | 쿠팡 파트너스 CSV 임포트/분석 | ✅ 활성 |
| `titles.py` | 타이틀 관리 (add/csv/list) | ✅ 활성 |
| `crawl_titles.py` | 사이트맵 기반 타이틀 추출 | ✅ 활성 |
| `ai_title.py` | AI 타이틀 생성 (GPT-4o-mini) | ✅ 활성 |
| `perf.py` | GA4 퍼포먼스 요약 | ✅ 활성 |
| `find_best_blog.py` | 키워드별 최적 블로그 추천 | ✅ 활성 |
| `rewrite_queue.py` | 리라이트 큐 (CTR 개선 대상) | ✅ 활성 |
| `register_blogs.py` | publish_config.yaml → D1 블로그 등록 | ✅ 활성 |
| `local_api.py` | 로컬 Flask API 서버 (Kiwi 분석기) | ✅ 활성 |
| `sync_utils.py` | sync 공통 유틸리티 | ✅ 활성 |
| `sync_wordpress.py` | WordPress 동기화 | ✅ 활성 |
| `sync_blogger.py` | Blogger 동기화 | ✅ 활성 |
| `sync_hugo.py` | Hugo 동기화 | ✅ 활성 |
| `sync_astro.py` | Astro 동기화 | ✅ 활성 |
| `deploy_ga4.sh` | Hugo 사이트 GA4 배포 스크립트 | ✅ 활성 |
| `summary.py` | 전체 현황 요약 | ⚠️ 대체됨 |
| `revenue.py` | GA4 수익 TOP 글 | ⚠️ 중복 |
| `gsc_snapshot.py` | GSC 스냅샷 수집 | ⚠️ 중복 |
| `upload_snapshots.py` | 스냅샷 D1 업로드 | ⚠️ 대체됨 |
| `spam_cleanup.py` | 스팸 URL 감지/삭제 | ❌ 일회성 |
| `spam_cleanup2.py` | 스팸 정리 변형 | ❌ 일회성 |
| `spam_inspect.py` | 스팸 인스펙션 | ❌ 일회성 |
| `ga4_inject.py` | GA4 측정ID 삽입 | ❌ 일회성 |
| `ga4_inject2.py` | GA4 인젝션 변형 | ❌ 일회성 |
| `ga4_audit.py` | GA4 감사 | ❌ 일회성 |
| `ga4_cleanup.py` | GA4 정리 | ❌ 일회성 |
| `ga4_measurement_ids.py` | 측정ID 조회 | ❌ 일회성 |
| `index_submit.py` | Google Indexing API | ❌ 일회성 |
| `keyword_value.py` | 키워드 가치 분석 | ❌ 대체됨 |
| `list_ga4.py` | GA4 속성 목록 | ❌ 일회성 |
| `list_gsc.py` | GSC 사이트 목록 | ❌ 대체됨 |
| `verify.py` | API 연결 확인 | ❌ 개발용 |
| `title.py` | 단일 타이틀 도구 | ❌ 중복 |
| `crawl_naver.py` | 네이버 크롤링 | ❌ 대체됨 |
| `gsc_backfill_pages.py` | 페이지별 GSC 백필 | ❌ 실험적 |

### `worker/` — Cloudflare Workers API 서버

| 파일 | 용도 |
|------|------|
| `src/index.js` | 메인 REST API (80+ 엔드포인트) |
| `wrangler.toml` | Workers 설정 (D1 바인딩) |
| `schema.sql` ~ `v4.sql` | D1 스키마 정의 |
| `package.json` | Node.js 의존성 (없음) |

### `hub-worker/` — 사이트 네트워크 허브

| 파일 | 용도 |
|------|------|
| `src/index.js` | 서브도메인 네트워크 조회 + HTML 렌더링 |
| `wrangler.toml` | Workers 설정 + 라우트 패턴 |

### `dashboard/` — React 대시보드

| 파일 | 용도 |
|------|------|
| `App.jsx` | Shell (43줄, React.lazy 12개 페이지) |
| `api.js` | Axios + `VITE_BLOGDEX_API_KEY` |
| `pages/` (13개) | 페이지 컴포넌트 (1개 완전추출 + 12개 skeleton) |
| `hooks/` (2개) | `useDashboardData`, `useApiQuery` |
| `components/` (9개) | TabNav, DataTable, StatCard, LoadingSpinner, ErrorMessage, DashboardLayout, RevenueChart, UserStats, RecentActivity |
| `index.html` | HTML 템플릿 |
| `vite.config.js` | Vite 설정 |
| `package.json` | React 19, Recharts, Axios |

### `credentials/` — 인증 정보

| 파일 | 용도 |
|------|------|
| 3개 `ADSENSE_CREDENTIALS_*.json` | AdSense OAuth 클라이언트 시크릿 |
| 1개 `client_secret_*.json` | Google OAuth 클라이언트 시크릿 (범용) |
| 3개 `token_*.json` | OAuth 토큰 (JSON 형식, pickle→JSON 마이그레이션 완료) |

### `scripts/` — 운영 도구 (v0.2.0)

| 파일 | 용도 |
|------|------|
| `cleanup_dead_code.sh` | 백업/로그/일회성 파일 삭제 |
| `archive_scripts.sh` | 일회성 스크립트 → cli/archive/ 이동 |
| `check_imports.py` | import 관계 분석 (안전 삭제 판정) |
| `setup_cron.sh` | crontab 자동 설정 |
| `health_check.py` | 5개 항목 시스템 건강 검사 |
| `logrotate.conf` | 로그 로테이션 설정 |
| `parse_sync_report.py` | JSONL 리포트 리더 + 연속 실패 감지 |

### `worker/migrations/` — D1 마이그레이션 (v0.2.0)

| 파일 | 용도 |
|------|------|
| `000_migrations_table.sql` | _migrations 추적 테이블 |
| `001_initial.sql ~ 004_bing_tables.sql` | 순차 마이그레이션 |
| `migrate.sh` | Bash 마이그레이터 |

### `logs/` — 런타임 로그 (v0.2.0)

| 파일 | 용도 |
|------|------|
| `daily_sync.log` | cron 실행 로그 |
| `sync_report.jsonl` | SyncMonitor 구조화 리포트 (JSONL) |

---

> **문서 버전**: v2.0 | **작성일**: 2026-06-07  
> **참고**: 본 문서는 코드 분석 기반으로 작성되었으며, 실제 동작과 차이가 있을 수 있습니다.
