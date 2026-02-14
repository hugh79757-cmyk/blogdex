import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

SITES = [
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

def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    # 전체 요약
    summary = Table(title=f"Search Console 전체 요약 ({days}일)", box=box.ROUNDED, expand=True)
    summary.add_column("사이트", style="cyan", width=30)
    summary.add_column("클릭", justify="right", style="bold green", width=8)
    summary.add_column("노출", justify="right", style="white", width=10)
    summary.add_column("CTR", justify="right", style="yellow", width=8)
    summary.add_column("평균순위", justify="right", style="magenta", width=8)

    total_clicks = 0
    total_impressions = 0

    for site_url in SITES:
        try:
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    "startDate": start_str,
                    "endDate": end_str,
                    "dimensions": ["query"],
                    "rowLimit": 1000,
                }
            ).execute()

            rows = response.get("rows", [])
            clicks = sum(r["clicks"] for r in rows)
            impressions = sum(r["impressions"] for r in rows)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            avg_pos = sum(r["position"] for r in rows) / len(rows) if rows else 0

            total_clicks += clicks
            total_impressions += impressions

            name = site_url.replace("https://", "").rstrip("/")
            summary.add_row(name, f"{clicks:,}", f"{impressions:,}", f"{ctr:.1f}%", f"{avg_pos:.1f}")

        except Exception as e:
            name = site_url.replace("https://", "").rstrip("/")
            summary.add_row(name, "-", "-", "-", str(e)[:20])

    console.print(summary)
    total_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    console.print(f"\n전체: 클릭 {total_clicks:,} | 노출 {total_impressions:,} | CTR {total_ctr:.1f}%")

if __name__ == "__main__":
    run()


