import pickle
import sys
from googleapiclient.discovery import build
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

ACCOUNTS = [
    {
        "name": "twinssn",
        "creds_path": "/Users/twinssn/Projects/blogdex/credentials/ADSENSE_CREDENTIALS_1twinssn.json",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_1_twinssn.pickle",
        "domains": ["rotcha.kr", "techpawz.com"],
    },
    {
        "name": "informationhot",
        "creds_path": "/Users/twinssn/Projects/blogdex/credentials/ADSENSE_CREDENTIALS_2informationhot.json",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_2_informationhot.pickle",
        "domains": ["informationhot.kr"],
    },
    {
        "name": "aikorea24",
        "creds_path": "/Users/twinssn/Projects/blogdex/credentials/ADSENSE_CREDENTIALS_3aikorea24.json",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_3_aikorea24.pickle",
        "domains": ["aikorea24.kr"],
    },
]

def get_token(token_path):
    with open(token_path, "rb") as f:
        return pickle.load(f)

def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    from datetime import datetime, timedelta
    end   = datetime.now()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")

    table = Table(title=f"애드센스 수익 요약 (최근 {days}일)", box=box.ROUNDED, expand=True)
    table.add_column("계정",   style="cyan",       width=15)
    table.add_column("사이트", style="white",       width=25)
    table.add_column("노출",   justify="right", style="white",      width=10)
    table.add_column("클릭",   justify="right", style="yellow",     width=8)
    table.add_column("CTR",    justify="right", style="yellow",     width=8)
    table.add_column("수익($)", justify="right", style="bold green", width=10)
    table.add_column("RPM($)", justify="right", style="blue",       width=8)

    grand_revenue = 0.0

    for acct in ACCOUNTS:
        try:
            creds = get_token(acct["token_path"])
            service = build("adsense", "v2", credentials=creds)

            # 계정 목록
            accounts = service.accounts().list().execute()
            acct_id = accounts["accounts"][0]["name"]

            # 사이트별 리포트
            resp = service.accounts().reports().generate(
                account=acct_id,
                dateRange="CUSTOM",
                startDate_year=int(start_str[:4]),
                startDate_month=int(start_str[5:7]),
                startDate_day=int(start_str[8:10]),
                endDate_year=int(end_str[:4]),
                endDate_month=int(end_str[5:7]),
                endDate_day=int(end_str[8:10]),
                dimensions=["DOMAIN_NAME"],
                metrics=["PAGE_VIEWS", "AD_REQUESTS", "CLICKS", "AD_REQUESTS_CTR", "ESTIMATED_EARNINGS", "PAGE_VIEWS_RPM"],
                orderBy=["-ESTIMATED_EARNINGS"],
            ).execute()

            rows = resp.get("rows", [])
            if not rows:
                table.add_row(acct["name"], "(데이터 없음)", "-", "-", "-", "-", "-")
                continue

            for row in rows:
                cells = row["cells"]
                domain   = cells[0]["value"]
                views    = cells[1]["value"]
                clicks   = cells[3]["value"]
                ctr      = cells[4]["value"]
                earnings = float(cells[5]["value"])
                rpm      = cells[6]["value"]
                grand_revenue += earnings
                table.add_row(
                    acct["name"], domain,
                    f"{int(views):,}", clicks,
                    f"{float(ctr)*100:.2f}%",
                    f"${earnings:.2f}", rpm
                )

        except Exception as e:
            table.add_row(acct["name"], "오류", "-", "-", "-", "-", str(e)[:40])

    console.print(table)
    console.print(f"\n[bold]총 수익: ${grand_revenue:.2f}[/bold]")

if __name__ == "__main__":
    run()
