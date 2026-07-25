"""과거 91일치 GSC 데이터를 page 포함으로 재수집"""
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
    "https://mimdiomcat.tistory.com/",
    "https://foodwater.tistory.com/",
    "https://achaanstree.tistory.com/",
    "https://zodiac.techpawz.com/",
]

def run():
    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)
    
    end_date = datetime.now() - timedelta(days=2)
    
    for day_offset in range(91):
        target = end_date - timedelta(days=day_offset)
        date_str = target.strftime("%Y-%m-%d")
        snapshot_file = os.path.join(SNAPSHOT_DIR, f"gsc_{date_str}.json")
        
        # 기존 파일이 있으면 page 필드 확인
        if os.path.exists(snapshot_file):
            with open(snapshot_file) as f:
                existing = json.load(f)
            # page 필드가 이미 있는지 확인
            has_page = False
            for site_data in existing.get("sites", {}).values():
                for kw in site_data.get("top_keywords", []):
                    if kw.get("page"):
                        has_page = True
                        break
                if has_page:
                    break
            if has_page:
                console.print(f"[dim]{date_str} - page 있음, 스킵[/]")
                continue
        
        console.print(f"[cyan]{date_str} 재수집 중...[/]", end=" ")
        
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
                        "dimensions": ["query", "page"],
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
                sorted_rows = sorted(rows, key=lambda r: r["impressions"], reverse=True)[:100]
                for row in sorted_rows:
                    keywords.append({
                        "query": row["keys"][0],
                        "page": row["keys"][1] if len(row["keys"]) > 1 else "",
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
        
        with open(snapshot_file, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
        
        console.print(f"클릭 {total_clicks}, 노출 {total_impressions}")
    
    console.print("\n[bold green]백필 완료! upload_snapshots.py를 다시 실행하세요.[/]")

if __name__ == "__main__":
    run()
