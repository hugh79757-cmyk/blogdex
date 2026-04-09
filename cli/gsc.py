# gsc.py의 URL 속성 조회 부분에서 sc-domain과 겹치는 것 제외
# sc-domain:rotcha.kr 가 있으면 rotcha.kr, *.rotcha.kr URL 속성은 스킵

import sys
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")

    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    all_sites    = service.sites().list().execute().get("siteEntry", [])
    owner_sites  = [s["siteUrl"] for s in all_sites if s["permissionLevel"] in ("siteOwner", "siteFullUser")]
    sc_domains   = [s for s in owner_sites if s.startswith("sc-domain:")]
    url_sites    = [s for s in owner_sites if not s.startswith("sc-domain:")]

    # sc-domain에 포함되는 URL 속성은 제외 (중복 방지)
    sc_base_domains = [s.replace("sc-domain:", "") for s in sc_domains]
    def is_covered(url):
        host = url.replace("https://", "").rstrip("/")
        for base in sc_base_domains:
            if host == base or host.endswith("." + base):
                return True
        return False

    url_sites_filtered = [s for s in url_sites if not is_covered(s)]

    summary = Table(title=f"Search Console 전체 요약 ({days}일)", box=box.ROUNDED, expand=True)
    summary.add_column("사이트", style="cyan",       width=35)
    summary.add_column("클릭",   justify="right", style="bold green", width=8)
    summary.add_column("노출",   justify="right", style="white",      width=10)
    summary.add_column("CTR",    justify="right", style="yellow",     width=8)
    summary.add_column("순위",   justify="right", style="magenta",    width=8)
    summary.add_column("타입",   style="dim",                         width=6)

    total_clicks = 0
    total_impressions = 0
    results = []

    def query(site_url):
        resp = service.searchanalytics().query(
            siteUrl=site_url,
            body={"startDate": start_str, "endDate": end_str, "rowLimit": 1}
        ).execute()
        rows = resp.get("rows", [])
        clicks      = sum(r["clicks"] for r in rows)
        impressions = sum(r["impressions"] for r in rows)
        ctr         = (clicks / impressions * 100) if impressions > 0 else 0
        avg_pos     = sum(r["position"] for r in rows) / len(rows) if rows else 0
        return clicks, impressions, ctr, avg_pos

    for sc in sc_domains:
        try:
            clicks, impressions, ctr, avg_pos = query(sc)
            total_clicks += clicks
            total_impressions += impressions
            name = sc.replace("sc-domain:", "") + " (*)"
            results.append((impressions, name, clicks, impressions, ctr, avg_pos, "domain"))
        except Exception as e:
            results.append((-1, sc, 0, 0, 0, 0, str(e)[:15]))

    for site_url in url_sites_filtered:
        try:
            clicks, impressions, ctr, avg_pos = query(site_url)
            total_clicks += clicks
            total_impressions += impressions
            name = site_url.replace("https://", "").rstrip("/")
            results.append((impressions, name, clicks, impressions, ctr, avg_pos, "url"))
        except Exception as e:
            name = site_url.replace("https://", "").rstrip("/")
            results.append((-1, name, 0, 0, 0, 0, str(e)[:15]))

    results.sort(key=lambda x: x[0], reverse=True)

    for _, name, clicks, impressions, ctr, avg_pos, typ in results:
        if impressions > 0:
            summary.add_row(name, f"{clicks:,}", f"{impressions:,}", f"{ctr:.1f}%", f"{avg_pos:.1f}", typ)
        else:
            summary.add_row(name, "0", "0", "0.0%", "0.0", typ)

    console.print(summary)
    total_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    console.print(f"\n전체: 클릭 {total_clicks:,} | 노출 {total_impressions:,} | CTR {total_ctr:.1f}%")

if __name__ == "__main__":
    run()
