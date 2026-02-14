import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    if len(sys.argv) < 2:
        console.print("[yellow]사용법: python gsc_detail.py <사이트URL> [일수][/]")
        console.print("예: python gsc_detail.py rotcha.kr 30")
        return

    site_input = sys.argv[1]
    if not site_input.startswith("http"):
        site_input = "https://" + site_input + "/"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    # 1. 키워드 분석
    response = service.searchanalytics().query(
        siteUrl=site_input,
        body={
            "startDate": start_str,
            "endDate": end_str,
            "dimensions": ["query"],
            "rowLimit": 25,
            "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]
        }
    ).execute()

    rows = response.get("rows", [])

    table = Table(title=f"{site_input} 키워드 분석 ({days}일)", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("키워드", style="white", width=30)
    table.add_column("클릭", justify="right", style="bold green", width=6)
    table.add_column("노출", justify="right", style="cyan", width=8)
    table.add_column("CTR", justify="right", style="yellow", width=7)
    table.add_column("순위", justify="right", style="magenta", width=6)
    table.add_column("진단", style="red", width=20)

    for row in rows:
        keyword = row["keys"][0]
        clicks = int(row["clicks"])
        impressions = int(row["impressions"])
        ctr = row["ctr"] * 100
        position = row["position"]

        # 진단
        diagnosis = ""
        if position <= 10 and ctr < 3:
            diagnosis = "CTR 개선 필요!"
        elif 10 < position <= 20:
            diagnosis = "1페이지 진입 가능"
        elif position <= 10 and ctr >= 3:
            diagnosis = "양호"
        elif impressions > 50 and clicks == 0:
            diagnosis = "타이틀 변경 필요"

        table.add_row(
            keyword[:30],
            str(clicks),
            str(impressions),
            f"{ctr:.1f}%",
            f"{position:.1f}",
            diagnosis
        )

    console.print(table)

    # 2. 페이지 분석
    response2 = service.searchanalytics().query(
        siteUrl=site_input,
        body={
            "startDate": start_str,
            "endDate": end_str,
            "dimensions": ["page"],
            "rowLimit": 15,
            "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]
        }
    ).execute()

    rows2 = response2.get("rows", [])

    table2 = Table(title=f"\n{site_input} 페이지별 성과", box=box.SIMPLE_HEAVY, expand=True)
    table2.add_column("페이지", style="white", width=45)
    table2.add_column("클릭", justify="right", style="bold green", width=6)
    table2.add_column("노출", justify="right", style="cyan", width=8)
    table2.add_column("CTR", justify="right", style="yellow", width=7)
    table2.add_column("순위", justify="right", style="magenta", width=6)

    for row in rows2:
        page = row["keys"][0].replace(site_input, "/")
        table2.add_row(
            page[:45],
            str(int(row["clicks"])),
            str(int(row["impressions"])),
            f"{row['ctr']*100:.1f}%",
            f"{row['position']:.1f}"
        )

    console.print(table2)

if __name__ == "__main__":
    run()

