"""GSC 데이터를 일별로 로컬 JSON에 누적 저장"""
import json
import os
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


def run():
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=1)
    date_str = end.strftime("%Y-%m-%d")
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    snapshot_file = os.path.join(SNAPSHOT_DIR, f"gsc_{date_str}.json")

    if os.path.exists(snapshot_file):
        console.print(f"[yellow]{date_str} 스냅샷 이미 존재. 스킵.[/]")
        return

    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)

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
            resp_summary = service.searchanalytics().query(
                siteUrl=site_url,
                body={
                    "startDate": start_str,
                    "endDate": end_str,
                    "dimensions": ["query"],
                    "rowLimit": 500,
                }
            ).execute()

            rows = resp_summary.get("rows", [])
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

            console.print(f"  [green]{name}[/]: 클릭 {clicks}, 노출 {impressions}")

        except Exception as e:
            snapshot["sites"][name] = {"error": str(e)}
            console.print(f"  [red]{name}[/]: {e}")

    snapshot["total"] = {
        "clicks": total_clicks,
        "impressions": total_impressions,
        "ctr": round((total_clicks / total_impressions * 100) if total_impressions > 0 else 0, 2)
    }

    with open(snapshot_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    console.print(f"\n[bold green]스냅샷 저장: {snapshot_file}[/]")
    console.print(f"전체: 클릭 {total_clicks}, 노출 {total_impressions}")


if __name__ == "__main__":
    run()
