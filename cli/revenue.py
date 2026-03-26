"""
revenue.py — 전체 블로그에서 애드센스 수익 TOP 글 조회
사용법:
    python revenue.py          # 최근 30일, TOP 30
    python revenue.py 7        # 최근 7일
    python revenue.py 30 50    # 최근 30일, TOP 50
"""
import sys
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange, OrderBy
)
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

PROPERTIES = [
    {"id": "properties/437300791", "name": "5.informationhot.kr"},
    {"id": "properties/502482181", "name": "info.techpawz.com"},
    {"id": "properties/437320334", "name": "Hugh7973"},
    {"id": "properties/521925869", "name": "biz.techpawz.com"},
    {"id": "properties/469316517", "name": "kuta.informationhot.kr"},
    {"id": "properties/490284742", "name": "유디 인포메이션핫"},
    {"id": "properties/502390201", "name": "5.informationhot.kr (2)"},
    {"id": "properties/502932448", "name": "65.informationhot.kr"},
    {"id": "properties/510545640", "name": "이슈반짝 TV"},
    {"id": "properties/518365064", "name": "stock"},
    {"id": "properties/518766137", "name": "8.informationhot.kr"},
    {"id": "properties/519652505", "name": "informationhot"},
    {"id": "properties/520033547", "name": "simprotection"},
    {"id": "properties/520495436", "name": "tv-show"},
]


def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    all_pages = []

    with console.status("[bold cyan]GA4 데이터 수집 중...") as status:
        for prop in PROPERTIES:
            status.update(f"[bold cyan]{prop['name']} 조회 중...")
            try:
                request = RunReportRequest(
                    property=prop["id"],
                    dimensions=[
                        Dimension(name="pagePath"),
                        Dimension(name="pageTitle"),
                    ],
                    metrics=[
                        Metric(name="screenPageViews"),
                        Metric(name="totalAdRevenue"),
                        Metric(name="publisherAdClicks"),
                        Metric(name="publisherAdImpressions"),
                    ],
                    date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="totalAdRevenue"), desc=True)],
                    limit=20,
                )
                response = client.run_report(request)

                for row in response.rows:
                    revenue = float(row.metric_values[1].value)
                    if revenue <= 0:
                        continue
                    all_pages.append({
                        "blog": prop["name"],
                        "path": row.dimension_values[0].value,
                        "title": row.dimension_values[1].value,
                        "views": int(row.metric_values[0].value),
                        "revenue": revenue,
                        "clicks": int(row.metric_values[2].value),
                        "impressions": int(row.metric_values[3].value),
                    })
            except Exception as e:
                console.print(f"[red]✗ {prop['name']}: {e}[/red]")

    # 수익 내림차순 정렬
    all_pages.sort(key=lambda x: x["revenue"], reverse=True)
    all_pages = all_pages[:top_n]

    if not all_pages:
        console.print("[yellow]수익 데이터가 없습니다.[/yellow]")
        return

    # 결과 출력 — 제목 중심, 리스트 형태
    console.print()
    console.rule(f"[bold]애드센스 수익 TOP {len(all_pages)} (최근 {days}일)[/bold]")
    console.print()

    total_revenue = 0
    total_views = 0

    for i, page in enumerate(all_pages, 1):
        rpm = (page["revenue"] / page["views"] * 1000) if page["views"] > 0 else 0
        ctr = (page["clicks"] / page["impressions"] * 100) if page["impressions"] > 0 else 0
        total_revenue += page["revenue"]
        total_views += page["views"]

        # 제목에서 사이트명 제거 (보통 " - 사이트명" 형태)
        title = page["title"]
        for suffix in [" - 꾸따로그", " - informationhot", " - biz.techpawz",
                       " - 이슈반짝", " - stock", " - simprotection", " - tv-show",
                       " - Hugh7973", " - 유디 인포메이션핫"]:
            title = title.replace(suffix, "")

        console.print(
            f"[bold white]{i:>2}.[/bold white] "
            f"[bold red]${page['revenue']:.2f}[/bold red]  "
            f"[green]{page['views']:>5,}PV[/green]  "
            f"[blue]RPM ${rpm:.1f}[/blue]  "
            f"[magenta]클릭 {page['clicks']}[/magenta]  "
            f"[dim]CTR {ctr:.1f}%[/dim]"
        )
        console.print(
            f"    [bold]{title}[/bold]"
        )
        console.print(
            f"    [dim cyan]{page['blog']}[/dim cyan] [dim]{page['path']}[/dim]"
        )
        console.print()

    # 구분선
    console.rule("[bold]요약[/bold]")
    console.print()

    # 블로그별 수익 요약
    blog_stats = {}
    for page in all_pages:
        if page["blog"] not in blog_stats:
            blog_stats[page["blog"]] = {"revenue": 0, "views": 0, "count": 0}
        blog_stats[page["blog"]]["revenue"] += page["revenue"]
        blog_stats[page["blog"]]["views"] += page["views"]
        blog_stats[page["blog"]]["count"] += 1

    summary = Table(title="블로그별 수익 요약", box=box.SIMPLE, expand=False)
    summary.add_column("블로그", style="cyan")
    summary.add_column("수익($)", justify="right", style="bold red")
    summary.add_column("PV", justify="right", style="green")
    summary.add_column("RPM($)", justify="right", style="blue")
    summary.add_column("글 수", justify="right", style="yellow")

    for blog, stats in sorted(blog_stats.items(), key=lambda x: x[1]["revenue"], reverse=True):
        rpm = (stats["revenue"] / stats["views"] * 1000) if stats["views"] > 0 else 0
        summary.add_row(
            blog,
            f"{stats['revenue']:.2f}",
            f"{stats['views']:,}",
            f"{rpm:.1f}",
            str(stats["count"]),
        )

    console.print(summary)

    grand_rpm = (total_revenue / total_views * 1000) if total_views > 0 else 0
    console.print(
        f"\n[bold]합계: 수익 ${total_revenue:.2f} | "
        f"PV {total_views:,} | "
        f"평균 RPM ${grand_rpm:.1f}[/bold]\n"
    )


if __name__ == "__main__":
    run()
