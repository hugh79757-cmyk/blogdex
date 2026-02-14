"""로컬 GSC 스냅샷을 D1에 업로드"""
import os
import json
from api import get, post
from rich.console import Console

console = Console()

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"


def run():
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    console.print(f"[cyan]스냅샷 {len(files)}개 업로드 시작[/]\n")

    for fname in files:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        date = snapshot.get("date", fname.replace("gsc_", "").replace(".json", ""))

        # 사이트별 일별 요약
        daily_data = []
        keyword_data = []

        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue

            daily_data.append({
                "site": site_name,
                "date": date,
                "clicks": site_data.get("clicks", 0),
                "impressions": site_data.get("impressions", 0),
                "ctr": site_data.get("ctr", 0),
            })

            for kw in site_data.get("top_keywords", []):
                keyword_data.append({
                    "site": site_name,
                    "date": date,
                    "query": kw["query"],
                    "clicks": kw["clicks"],
                    "impressions": kw["impressions"],
                    "ctr": kw["ctr"],
                    "position": kw["position"],
                })

        # 업로드
        if daily_data:
            post("/gsc/daily", {"data": daily_data})

        if keyword_data:
            # 100개씩 청크
            for i in range(0, len(keyword_data), 100):
                chunk = keyword_data[i:i + 100]
                post("/gsc/keywords", {"data": chunk})

        kw_count = len(keyword_data)
        console.print(f"  [green]{date}[/] — 사이트 {len(daily_data)}개, 키워드 {kw_count}개")

    console.print(f"\n[bold green]업로드 완료: {len(files)}일치[/]")


if __name__ == "__main__":
    run()
