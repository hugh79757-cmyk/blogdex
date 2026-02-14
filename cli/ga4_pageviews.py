"""GA4 API로 URL별 페이지뷰 + 광고수익 수집"""
import json
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from google_auth import get_credentials
from api import post
from rich.console import Console

console = Console()

PROPERTIES = {
    "407313218": "techpawz.com",
    "502482181": "info.techpawz.com",
    "437320334": "biz1.techpawz.com",
    "521925869": "biz.techpawz.com",
    "407323015": "rotcha.kr",
    "520232186": "hotissue.rotcha.kr",
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

def run(days=30):
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    all_data = []
    total_pv = 0
    total_rev = 0.0

    for prop_id, domain in PROPERTIES.items():
        console.print(f"  [cyan]{domain}[/] ...", end=" ")
        try:
            request = RunReportRequest(
                property=f"properties/{prop_id}",
                date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
                dimensions=[
                    Dimension(name="pagePath"),
                    Dimension(name="date"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="totalAdRevenue"),
                ],
                limit=10000,
            )
            response = client.run_report(request=request)
            count = 0
            site_pv = 0
            site_rev = 0.0
            for row in response.rows:
                path = row.dimension_values[0].value
                date = row.dimension_values[1].value
                date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                pageviews = int(row.metric_values[0].value)
                sessions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value)
                full_url = f"https://{domain}{path}"
                all_data.append({
                    "site": domain,
                    "date": date_fmt,
                    "page": full_url,
                    "pageviews": pageviews,
                    "sessions": sessions,
                    "revenue": round(revenue, 6),
                })
                site_pv += pageviews
                site_rev += revenue
                count += 1
            total_pv += site_pv
            total_rev += site_rev
            console.print(f"{count}건, {site_pv:,} PV, ${site_rev:.2f}")
        except Exception as e:
            console.print(f"[red]에러: {e}[/]")

    console.print(f"\n[bold]전체: {len(all_data)}건, {total_pv:,} PV, ${total_rev:.2f}[/]")

    backup = f"/Users/twinssn/Projects/blogdex/cli/snapshots/ga4_pageviews_{end_str}.json"
    with open(backup, "w") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    console.print(f"저장: {backup}")

    if all_data:
        try:
            batch_size = 500
            for i in range(0, len(all_data), batch_size):
                batch = all_data[i:i+batch_size]
                resp = post("/ga4/pageviews", {"data": batch})
            console.print(f"[bold green]D1 업로드 완료[/]")
        except Exception as e:
            console.print(f"[yellow]D1 업로드 실패: {e}[/]")

    return all_data

if __name__ == "__main__":
    run(days=30)
