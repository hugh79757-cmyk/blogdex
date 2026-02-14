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
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)

    summary = Table(title=f"전체 블로그 퍼포먼스 (최근 {days}일)", box=box.SIMPLE_HEAVY, expand=True)
    summary.add_column("블로그", style="cyan", width=20)
    summary.add_column("조회수", justify="right", style="bold green", width=10)
    summary.add_column("세션", justify="right", style="yellow", width=8)
    summary.add_column("TOP 글", style="white", no_wrap=False)


    for prop in PROPERTIES:
        try:
            request = RunReportRequest(
                property=prop["id"],
                dimensions=[Dimension(name="pageTitle")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                ],
                date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
                order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
                limit=5
            )
            response = client.run_report(request)

            total_views = sum(int(row.metric_values[0].value) for row in response.rows)
            total_sessions = sum(int(row.metric_values[1].value) for row in response.rows)
            top_title = response.rows[0].dimension_values[0].value[:35] if response.rows else "-"

            summary.add_row(
                prop["name"],
                f"{total_views:,}",
                f"{total_sessions:,}",
                top_title
            )
        except Exception as e:
            summary.add_row(prop["name"], "오류", "", str(e)[:35])

    console.print(summary)

if __name__ == "__main__":
    run()

