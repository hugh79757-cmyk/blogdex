import pickle
import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

ACCOUNTS = [
    {
        "name": "twinssn",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_1_twinssn.pickle",
    },
    {
        "name": "informationhot",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_2_informationhot.pickle",
    },
    {
        "name": "aikorea24",
        "token_path": "/Users/twinssn/Projects/blogdex/credentials/token_3_aikorea24.pickle",
    },
]

def get_creds(token_path):
    with open(token_path, "rb") as f:
        return pickle.load(f)

def fetch_revenue(service, acct_id, start, end):
    """기간별 도메인 수익 딕셔너리 반환 {domain: earnings}"""
    try:
        resp = service.accounts().reports().generate(
            account=acct_id,
            dateRange="CUSTOM",
            startDate_year=start.year, startDate_month=start.month, startDate_day=start.day,
            endDate_year=end.year,   endDate_month=end.month,   endDate_day=end.day,
            dimensions=["DOMAIN_NAME"],
            metrics=["ESTIMATED_EARNINGS", "PAGE_VIEWS", "CLICKS"],
            orderBy=["-ESTIMATED_EARNINGS"],
        ).execute()
        result = {}
        for row in resp.get("rows", []):
            domain   = row["cells"][0]["value"]
            earnings = float(row["cells"][1]["value"])
            views    = int(row["cells"][2]["value"])
            clicks   = int(row["cells"][3]["value"])
            result[domain] = {"earnings": earnings, "views": views, "clicks": clicks}
        return result
    except Exception as e:
        return {}

def run():
    today = datetime.now().date()

    # 3개 구간 정의
    periods = [
        {"label": "최근 7일",   "start": today - timedelta(days=7),  "end": today - timedelta(days=1)},
        {"label": "7~14일전",   "start": today - timedelta(days=14), "end": today - timedelta(days=8)},
        {"label": "14~21일전",  "start": today - timedelta(days=21), "end": today - timedelta(days=15)},
    ]

    # 계정별 × 기간별 데이터 수집
    all_data = {}  # {domain: [p0_earnings, p1_earnings, p2_earnings]}

    for acct in ACCOUNTS:
        try:
            creds   = get_creds(acct["token_path"])
            service = build("adsense", "v2", credentials=creds)
            acct_id = service.accounts().list().execute()["accounts"][0]["name"]

            for i, p in enumerate(periods):
                data = fetch_revenue(service, acct_id,
                                     datetime.combine(p["start"], datetime.min.time()),
                                     datetime.combine(p["end"],   datetime.min.time()))
                for domain, vals in data.items():
                    if domain not in all_data:
                        all_data[domain] = {"acct": acct["name"], "periods": [{}, {}, {}]}
                    all_data[domain]["periods"][i] = vals

        except Exception as e:
            console.print(f"[red]{acct['name']} 오류: {e}[/red]")

    # 최근 7일 수익 기준 정렬, 0인 것 제외
    sorted_domains = sorted(
        [(d, v) for d, v in all_data.items() if any(v["periods"][i].get("earnings", 0) > 0 for i in range(3))],
        key=lambda x: x[1]["periods"][0].get("earnings", 0),
        reverse=True
    )

    table = Table(title="애드센스 수익 추이 비교", box=box.ROUNDED, expand=True)
    table.add_column("계정",         style="dim",         width=13)
    table.add_column("도메인",       style="cyan",        width=28)
    table.add_column("14~21일전($)", justify="right", style="white",      width=13)
    table.add_column("7~14일전($)",  justify="right", style="yellow",     width=13)
    table.add_column("최근 7일($)",  justify="right", style="bold green", width=13)
    table.add_column("추이",         justify="center",                    width=6)

    total = [0.0, 0.0, 0.0]

    for domain, v in sorted_domains:
        p2 = v["periods"][2].get("earnings", 0)
        p1 = v["periods"][1].get("earnings", 0)
        p0 = v["periods"][0].get("earnings", 0)
        total[2] += p2
        total[1] += p1
        total[0] += p0

        if p0 > p1:
            trend = "[green]▲[/green]"
        elif p0 < p1:
            trend = "[red]▼[/red]"
        else:
            trend = "─"

        table.add_row(
            v["acct"], domain,
            f"${p2:.2f}", f"${p1:.2f}", f"${p0:.2f}",
            trend
        )

    console.print(table)
    console.print(
        f"\n[bold]총 수익: "
        f"14~21일전 ${total[2]:.2f} | "
        f"7~14일전 ${total[1]:.2f} | "
        f"최근 7일 ${total[0]:.2f}[/bold]"
    )

    # 성장률
    if total[1] > 0:
        growth = (total[0] - total[1]) / total[1] * 100
        color = "green" if growth >= 0 else "red"
        console.print(f"[{color}]전주 대비 성장률: {growth:+.1f}%[/{color}]")

if __name__ == "__main__":
    run()
