#!/usr/bin/env python3
"""
Blogdex: 특정 키워드에 최적인 블로그 찾기
사용법: python find_best_blog.py 자격증
        python find_best_blog.py 자격증 90
"""
import sys
import json
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange, FilterExpression,
    Filter, OrderBy
)
from google_auth import get_credentials
from api import get
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# ── 실제 매핑 (perf.py, gsc.py, ga4_pageviews.py에서 가져옴) ──

GSC_SITES = [
    "https://5.informationhot.kr/",
    "https://65.informationhot.kr/",
    "https://informationhot.kr/",
    "https://kuta.informationhot.kr/",
    "https://stock.informationhot.kr/",
    "https://ud.informationhot.kr/",
    "https://techpawz.com/",
    "https://issue.techpawz.com/",
    "https://2.techpawz.com/",
    "https://rotcha.kr/",
    "https://hotissue.rotcha.kr/",
    "https://travel.rotcha.kr/",
    "https://info.techpawz.com/",
]

GA4_PROPERTIES = {
    "407313218": "techpawz.com",
    "502482181": "info.techpawz.com",
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
    "407673873": "achaanstree.tistory.com",
    "407723312": "foodwater.tistory.com",
}



def cmd_new():
    """새 글 발행 최적 블로그 추천 (D1 기반)"""
    if len(sys.argv) < 3:
        console.print("[yellow]사용법: python find_best_blog.py new <키워드>[/]")
        console.print("  예: python find_best_blog.py new 삼성생명 고객센터")
        return

    keyword = " ".join(sys.argv[2:])
    console.print(f"\n[bold]새 글 발행 분석: '{keyword}'[/]\n")

    # 1. 블로그 목록
    blogs = get("/blogs")
    blog_map = {b["id"]: b for b in blogs}

    # 2. 전체 글에서 블로그별 총 글 수
    all_posts = get("/posts/search", params={"q": ""})
    if isinstance(all_posts, dict):
        all_posts = all_posts.get("results", [])

    blog_total = {}
    for p in all_posts:
        bid = p.get("blog_id")
        blog_total[bid] = blog_total.get(bid, 0) + 1

    # 3. 키워드 관련 기존 글 조회
    related = get("/posts/search", params={"q": keyword})
    if isinstance(related, dict):
        related = related.get("results", [])

    blog_related = {}
    blog_titles = {}
    for p in related:
        bid = p.get("blog_id")
        blog_related[bid] = blog_related.get(bid, 0) + 1
        if bid not in blog_titles:
            blog_titles[bid] = []
        blog_titles[bid].append(p.get("title", ""))

    # 4. 키워드 단어별 검색 → 토픽 연관성
    words = [w for w in keyword.split() if len(w) >= 2]

    blog_topic_hits = {}
    for word in words:
        wr = get("/posts/search", params={"q": word})
        if isinstance(wr, dict):
            wr = wr.get("results", [])
        for p in wr:
            bid = p.get("blog_id")
            blog_topic_hits[bid] = blog_topic_hits.get(bid, 0) + 1

    console.print(f"[cyan]'{keyword}' 관련 기존 글: {len(related)}건[/]")
    if related:
        for bid, cnt in sorted(blog_related.items(), key=lambda x: -x[1]):
            bname = blog_map.get(bid, {}).get("name", "?")
            console.print(f"  {bname}: {cnt}건")
    console.print()

    # 5. 점수 계산
    scored = []
    for b in blogs:
        bid = b["id"]
        total = blog_total.get(bid, 0)
        related_cnt = blog_related.get(bid, 0)
        topic_hits = blog_topic_hits.get(bid, 0)

        # 토픽 연관성: 관련 단어가 많이 있으면 좋음
        topic_score = min(topic_hits, 50) * 3

        # 블로그 규모: 글이 많으면 도메인 권위 높음 (체감 감소)
        size_score = min(total, 500) * 0.1

        # 카니발리제이션 패널티: 제목 유사도까지 고려
        titles_in_blog = blog_titles.get(bid, [])
        # 키워드 단어가 제목에 모두 포함된 글 수 (높은 유사도)
        high_sim = 0
        for t in titles_in_blog:
            t_lower = t.lower()
            if all(w.lower() in t_lower for w in words):
                high_sim += 1

        if related_cnt == 0:
            cannibal_penalty = 0
            cannibal_label = "없음"
        elif high_sim >= 2:
            cannibal_penalty = high_sim * 40 + related_cnt * 10
            cannibal_label = f"[bold red]유사 {high_sim}건 — 리라이트 추천[/]"
        elif high_sim == 1:
            cannibal_penalty = 30 + related_cnt * 5
            cannibal_label = f"유사 1건 + 관련 {related_cnt}건"
        elif related_cnt <= 3:
            cannibal_penalty = related_cnt * 8
            cannibal_label = f"{related_cnt}건 (클러스터 가능)"
        else:
            cannibal_penalty = related_cnt * 15
            cannibal_label = f"{related_cnt}건 [bold red]포화 위험[/]"

        # 빈 블로그 패널티: 글이 너무 적으면 감점
        empty_penalty = max(0, (20 - total)) * 2 if total < 20 else 0

        final_score = topic_score + size_score - cannibal_penalty - empty_penalty

        scored.append({
            "blog_id": bid,
            "name": b["name"],
            "platform": b["platform"],
            "total_posts": total,
            "related": related_cnt,
            "topic_hits": topic_hits,
            "cannibal_label": cannibal_label,
            "score": final_score,
            "high_sim": high_sim,
        })

    # 유사 글 2건 이상인 블로그는 분리
    rewrite_candidates = [s for s in scored if s.get("high_sim", 0) >= 2]
    scored = [s for s in scored if s.get("high_sim", 0) < 2]
    scored.sort(key=lambda x: x["score"], reverse=True)

    # 리라이트 추천 먼저 표시
    if rewrite_candidates:
        console.print(Panel(
            "\n".join([
                f"[bold red]'{keyword}' 유사 글이 이미 있는 블로그:[/]\n"] +
                [f"  [cyan]{s['name']}[/] — 유사 {s['high_sim']}건, 신규 발행보다 기존 글 업데이트 추천"
                 for s in rewrite_candidates] +
                ["\n  아래는 [bold]신규 발행 시[/] 추천 블로그입니다."]
            ),
            title="⚠ 리라이트 우선 추천", width=80
        ))
        console.print()

    # 6. 랭킹 테이블
    table = Table(title=f"'{keyword}' 새 글 발행 추천", box=box.ROUNDED, expand=True)
    table.add_column("순위", width=4)
    table.add_column("블로그", style="cyan", width=30)
    table.add_column("플랫폼", style="dim", width=10)
    table.add_column("총 글수", justify="right", width=7)
    table.add_column("연관 글", justify="right", width=7)
    table.add_column("토픽 적합", justify="right", style="green", width=8)
    table.add_column("중복 위험", width=20)
    table.add_column("점수", justify="right", style="bold", width=6)

    for i, s in enumerate(scored[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
        table.add_row(
            medal,
            s["name"],
            s["platform"],
            str(s["total_posts"]),
            str(s["related"]),
            str(s["topic_hits"]),
            s["cannibal_label"],
            f"{s['score']:.0f}",
        )

    console.print(table)

    # 7. 1위 상세
    top = scored[0]
    lines = [f"[bold cyan]{top['name']}[/] 추천\n"]
    lines.append(f"  토픽 연관 글 {top['topic_hits']}건으로 주제 적합성 높음")
    lines.append(f"  블로그 규모 {top['total_posts']}건")
    if top["related"] == 0:
        lines.append(f"  동일 키워드 글 없음 → [bold green]카니발리제이션 위험 없음[/]")
    elif top["related"] <= 2:
        lines.append(f"  동일 키워드 글 {top['related']}건 → 내부링크로 클러스터 구성 가능")
    else:
        lines.append(f"  [bold red]동일 키워드 글 {top['related']}건 → 기존 글 업데이트 검토 필요[/]")

    # 중복 제목 표시
    top_titles = blog_titles.get(top["blog_id"], [])
    if top_titles:
        lines.append(f"\n[bold]기존 유사 글:[/]")
        for t in top_titles[:5]:
            lines.append(f"  • {t[:60]}")

    console.print(Panel("\n".join(lines), title="추천 결과", width=80))

    # 포화 경고
    saturated = [s for s in scored if s["related"] >= 3]
    if saturated:
        console.print(f"\n[bold red]⚠ 포화 블로그 ({len(saturated)}개):[/]")
        for s in saturated:
            console.print(f"  {s['name']}: '{keyword}' 관련 {s['related']}건 — 신규 발행보다 기존 글 리라이트 추천")


def run():
    if len(sys.argv) < 2:
        console.print("[yellow]사용법: python find_best_blog.py <키워드> [일수][/]")
        console.print("  예: python find_best_blog.py 자격증")
        console.print("  예: python find_best_blog.py 자격증 90")
        return

    keyword = sys.argv[1]
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    console.print(f"\n[bold]'{keyword}' 키워드 — 최적 블로그 분석 ({days}일)[/]\n")

    creds = get_credentials()
    blog_scores = {}  # domain → {gsc_clicks, gsc_impressions, gsc_ctr, gsc_position, ga4_views, db_posts, ...}

    # ────────────────────────────────────────────
    # 1. Search Console: 키워드별 노출/클릭/순위
    # ────────────────────────────────────────────
    console.print("[cyan]1. Search Console 분석...[/]")
    service = build("searchconsole", "v1", credentials=creds)
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    for site_url in GSC_SITES:
        domain = site_url.replace("https://", "").rstrip("/")
        try:
            resp = service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    "startDate": start_str,
                    "endDate": end_str,
                    "dimensions": ["query"],
                    "dimensionFilterGroups": [{
                        "filters": [{
                            "dimension": "query",
                            "operator": "contains",
                            "expression": keyword,
                        }]
                    }],
                    "rowLimit": 500,
                }
            ).execute()
            rows = resp.get("rows", [])
            clicks = sum(r["clicks"] for r in rows)
            impressions = sum(r["impressions"] for r in rows)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            positions = [r["position"] for r in rows]
            avg_pos = sum(positions) / len(positions) if positions else 99

            top_queries = sorted(rows, key=lambda x: x["impressions"], reverse=True)[:5]
            top_kw = [f"{r['keys'][0]} ({r['impressions']}노출)" for r in top_queries]

            if domain not in blog_scores:
                blog_scores[domain] = {}
            blog_scores[domain]["gsc_clicks"] = clicks
            blog_scores[domain]["gsc_impressions"] = impressions
            blog_scores[domain]["gsc_ctr"] = ctr
            blog_scores[domain]["gsc_position"] = avg_pos
            blog_scores[domain]["gsc_keywords"] = len(rows)
            blog_scores[domain]["top_queries"] = top_kw

            status = f"클릭 {clicks}, 노출 {impressions}" if impressions > 0 else "데이터 없음"
            console.print(f"  {domain}: {status}")

        except Exception as e:
            console.print(f"  [red]{domain}: {e}[/]")

    # ────────────────────────────────────────────
    # 2. GA4: 키워드 포함 페이지의 조회수 + 광고 수익
    # ────────────────────────────────────────────
    console.print("\n[cyan]2. GA4 분석 (조회수 + 광고수익)...[/]")
    ga4_client = BetaAnalyticsDataClient(credentials=creds)

    for prop_id, domain in GA4_PROPERTIES.items():
        try:
            request = RunReportRequest(
                property=f"properties/{prop_id}",
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                dimensions=[Dimension(name="pageTitle")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="totalAdRevenue"),
                ],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="pageTitle",
                        string_filter=Filter.StringFilter(
                            match_type=Filter.StringFilter.MatchType.CONTAINS,
                            value=keyword,
                            case_sensitive=False,
                        ),
                    )
                ),
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
                limit=50,
            )
            response = ga4_client.run_report(request=request)

            total_views = 0
            total_sessions = 0
            total_revenue = 0.0
            top_pages = []

            for row in response.rows:
                title = row.dimension_values[0].value
                views = int(row.metric_values[0].value)
                sessions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value)
                total_views += views
                total_sessions += sessions
                total_revenue += revenue
                if len(top_pages) < 3:
                    top_pages.append(f"{title[:40]} ({views}뷰)")

            if domain not in blog_scores:
                blog_scores[domain] = {}
            blog_scores[domain]["ga4_views"] = total_views
            blog_scores[domain]["ga4_sessions"] = total_sessions
            blog_scores[domain]["ga4_revenue"] = total_revenue
            blog_scores[domain]["ga4_top_pages"] = top_pages

            if total_views > 0:
                console.print(f"  {domain}: {total_views}뷰, ${total_revenue:.2f}")

        except Exception as e:
            err_msg = str(e)[:50]
            if "403" not in err_msg and "not found" not in err_msg.lower():
                console.print(f"  [dim]{domain}: {err_msg}[/]")

    # ────────────────────────────────────────────
    # 3. D1: 키워드 관련 기존 글 수
    # ────────────────────────────────────────────
    console.print("\n[cyan]3. D1 기존 글 확인...[/]")
    posts = get("/posts/search", params={"q": keyword})
    if isinstance(posts, dict):
        posts = posts.get("results", [])

    blog_post_counts = {}
    for p in posts:
        bname = p.get("blog_name", "unknown")
        blog_post_counts[bname] = blog_post_counts.get(bname, 0) + 1

    console.print(f"  '{keyword}' 관련 기존 글: {len(posts)}건")
    for bname, cnt in sorted(blog_post_counts.items(), key=lambda x: x[1], reverse=True):
        console.print(f"    {bname}: {cnt}건")

    # ────────────────────────────────────────────
    # 4. 종합 점수 계산 및 랭킹
    # ────────────────────────────────────────────
    console.print(f"\n[bold]═══ '{keyword}' 최적 블로그 랭킹 ═══[/]\n")

    scored = []
    for domain, data in blog_scores.items():
        gsc_imp = data.get("gsc_impressions", 0)
        gsc_clicks = data.get("gsc_clicks", 0)
        gsc_ctr = data.get("gsc_ctr", 0)
        gsc_pos = data.get("gsc_position", 99)
        ga4_views = data.get("ga4_views", 0)
        ga4_rev = data.get("ga4_revenue", 0)
        gsc_kw_count = data.get("gsc_keywords", 0)

        # 이미 노출이 있으면 해당 도메인이 유리
        exposure_score = gsc_imp * 2 + gsc_clicks * 10
        # 조회수가 있으면 트래픽 기반 신뢰도
        traffic_score = ga4_views * 3
        # 광고 수익이 있으면 수익성 검증
        revenue_score = ga4_rev * 1000
        # 순위가 좋으면 (낮을수록 좋음) 보너스
        position_bonus = max(0, (30 - gsc_pos) * 10) if gsc_pos < 30 else 0
        # 키워드 다양성 (관련 키워드가 많으면 주제 적합성 높음)
        diversity_bonus = gsc_kw_count * 5

        total_score = exposure_score + traffic_score + revenue_score + position_bonus + diversity_bonus

        if total_score > 0:
            scored.append({
                "domain": domain,
                "score": total_score,
                "gsc_impressions": gsc_imp,
                "gsc_clicks": gsc_clicks,
                "gsc_ctr": gsc_ctr,
                "gsc_position": gsc_pos,
                "gsc_keywords": gsc_kw_count,
                "ga4_views": ga4_views,
                "ga4_revenue": ga4_rev,
                "top_queries": data.get("top_queries", []),
                "top_pages": data.get("ga4_top_pages", []),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)

    if not scored:
        console.print(f"[yellow]'{keyword}' 관련 데이터가 있는 블로그가 없습니다.[/]")
        return

    # 메인 랭킹 테이블
    table = Table(title=f"'{keyword}' 블로그 적합도 랭킹", box=box.ROUNDED, expand=True)
    table.add_column("순위", style="bold", width=4)
    table.add_column("블로그", style="cyan", width=28)
    table.add_column("GSC 노출", justify="right", style="white", width=8)
    table.add_column("GSC 클릭", justify="right", style="green", width=8)
    table.add_column("CTR", justify="right", style="yellow", width=6)
    table.add_column("평균순위", justify="right", style="magenta", width=6)
    table.add_column("GA4 뷰", justify="right", style="bold green", width=8)
    table.add_column("광고수익", justify="right", style="bold red", width=8)
    table.add_column("점수", justify="right", style="bold white", width=8)

    for i, s in enumerate(scored[:15], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i)
        table.add_row(
            medal,
            s["domain"],
            f"{s['gsc_impressions']:,}",
            str(s["gsc_clicks"]),
            f"{s['gsc_ctr']:.1f}%",
            f"{s['gsc_position']:.1f}" if s["gsc_position"] < 99 else "-",
            f"{s['ga4_views']:,}" if s["ga4_views"] > 0 else "-",
            f"${s['ga4_revenue']:.2f}" if s["ga4_revenue"] > 0 else "-",
            f"{s['score']:.0f}",
        )

    console.print(table)

    # 1위 상세 분석
    top = scored[0]
    detail_lines = [
        f"[bold cyan]{top['domain']}[/] 이(가) '{keyword}' 포스팅에 가장 적합합니다.\n",
        f"[bold]근거:[/]",
        f"  • 구글에서 '{keyword}' 관련 키워드 [bold]{top['gsc_keywords']}개[/] 노출 중",
        f"  • 최근 {days}일간 노출 [bold]{top['gsc_impressions']:,}회[/], 클릭 [bold]{top['gsc_clicks']}회[/]",
    ]
    if top["gsc_position"] < 99:
        detail_lines.append(f"  • 평균 검색 순위: [bold]{top['gsc_position']:.1f}위[/]")
    if top["ga4_views"] > 0:
        detail_lines.append(f"  • GA4 조회수: [bold]{top['ga4_views']:,}뷰[/]")
    if top["ga4_revenue"] > 0:
        detail_lines.append(f"  • 광고 수익: [bold red]${top['ga4_revenue']:.2f}[/]")
    if top["top_queries"]:
        detail_lines.append(f"\n[bold]노출 키워드:[/]")
        for q in top["top_queries"][:5]:
            detail_lines.append(f"  → {q}")
    if top["top_pages"]:
        detail_lines.append(f"\n[bold]인기 페이지:[/]")
        for p in top["top_pages"][:3]:
            detail_lines.append(f"  → {p}")

    console.print(Panel("\n".join(detail_lines), title="추천 결과", width=80))

    # 기존 글 정보
    if blog_post_counts:
        console.print(f"\n[dim]참고: '{keyword}' 관련 기존 글 — {', '.join(f'{k}({v}건)' for k,v in blog_post_counts.items())}[/]")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "new":
        cmd_new()
    else:
        run()
