"""GSC 스냅샷 과거 90일치 백필"""
import json
import os
import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console

console = Console()

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"

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


def fetch_day(service, date_str):
    """하루치 GSC 데이터 수집"""
    snapshot = {
        "date": date_str,
        "collected_at": datetime.now().isoformat(),
        "sites": {}
    }
    total_clicks = 0
    total_impressions = 0

    for site_url in SITES:
        name = site_url.replace("https://", "").rstrip("/")
        try:
            resp = service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    "startDate": date_str,
                    "endDate": date_str,
                    "dimensions": ["query"],
                    "rowLimit": 500,
                }
            ).execute()

            rows = resp.get("rows", [])
            clicks = sum(r["clicks"] for r in rows)
            impressions = sum(r["impressions"] for r in rows)
            ctr = (clicks / impressions * 100) if impressions > 0 else 0

            total_clicks += clicks
            total_impressions += impressions

            keywords = []
            sorted_rows = sorted(rows, key=lambda r: r["impressions"], reverse=True)[:50]
            for row in sorted_rows:
                keywords.append({
                    "query": row["keys"][0],
                    "clicks": int(row["clicks"]),
                    "impressions": int(row["impressions"]),
                    "ctr": round(row["ctr"] * 100, 2),
                    "position": round(row["position"], 1)
                })

            snapshot["sites"][name] = {
                "clicks": clicks,
                "impressions": impressions,
                "ctr": round(ctr, 2),
                "top_keywords": keywords
            }
        except Exception as e:
            snapshot["sites"][name] = {"error": str(e)}

    snapshot["total"] = {
        "clicks": total_clicks,
        "impressions": total_impressions,
        "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2)
    }
    return snapshot, total_clicks, total_impressions


def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90

    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)

    end = datetime.now() - timedelta(days=2)
    collected = 0
    skipped = 0

    console.print(f"[bold]GSC {days}일 백필 시작[/]\n")

    for i in range(days, 0, -1):
        target = end - timedelta(days=i)
        date_str = target.strftime("%Y-%m-%d")
        filepath = os.path.join(SNAPSHOT_DIR, f"gsc_{date_str}.json")

        if os.path.exists(filepath):
            skipped += 1
            continue

        snapshot, clicks, impressions = fetch_day(service, date_str)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        collected += 1
        console.print(f"  [green]{date_str}[/] — 클릭 {clicks}, 노출 {impressions}")

    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    console.print(f"\n[bold]완료: 신규 {collected}일 저장, {skipped}일 스킵[/]")
    console.print(f"[bold]전체 스냅샷: {len(files)}개 ({files[0]} ~ {files[-1]})[/]")


if __name__ == "__main__":
    run()
