import json
import glob
import sys
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def load_snapshot(date_str):
    path = f"snapshots/gsc_{date_str}.json"
    try:
        data = json.load(open(path))
        return data.get("sites", {})
    except:
        return {}

def run():
    filter_kw = sys.argv[1] if len(sys.argv) > 1 else "-hugo"

    today = datetime.now().date()
    yesterday   = today - timedelta(days=1)
    week1_ago   = today - timedelta(days=7)
    week2_ago   = today - timedelta(days=14)

    d_yesterday = yesterday.strftime("%Y-%m-%d")
    d_week1     = week1_ago.strftime("%Y-%m-%d")
    d_week2     = week2_ago.strftime("%Y-%m-%d")

    snap_yday  = load_snapshot(d_yesterday)
    snap_week1 = load_snapshot(d_week1)
    snap_week2 = load_snapshot(d_week2)

    # 필터 적용 (기본: -hugo)
    all_sites = set(snap_yday) | set(snap_week1) | set(snap_week2)
    if filter_kw:
        all_sites = {s for s in all_sites if filter_kw in s}

    if not all_sites:
        console.print(f"[red]'{filter_kw}' 포함 사이트 없음. 스냅샷 날짜: {d_yesterday}, {d_week1}, {d_week2}[/red]")
        return

    # 1주전 노출 기준 정렬
    def impressions(snap, site):
        return snap.get(site, {}).get("impressions", 0)

    sites_sorted = sorted(all_sites, key=lambda s: impressions(snap_week1, s), reverse=True)

    table = Table(
        title=f"신생 블로그 노출 추이 (필터: '{filter_kw}')",
        box=box.ROUNDED, expand=True
    )
    table.add_column("블로그",         style="cyan",       width=25)
    table.add_column(f"노출 {d_week2[:10]}", justify="right", style="white",      width=14)
    table.add_column(f"노출 {d_week1[:10]}", justify="right", style="bold yellow", width=14)
    table.add_column(f"노출 {d_yesterday}",  justify="right", style="bold green",  width=14)
    table.add_column("클릭 2주전",     justify="right", style="white",  width=10)
    table.add_column("클릭 1주전",     justify="right", style="yellow", width=10)
    table.add_column("클릭 어제",      justify="right", style="green",  width=10)
    table.add_column("추이",           justify="center",               width=6)

    for site in sites_sorted:
        imp_w2   = impressions(snap_week2, site)
        imp_w1   = impressions(snap_week1, site)
        imp_yday = impressions(snap_yday, site)
        clk_w2   = snap_week2.get(site, {}).get("clicks", 0)
        clk_w1   = snap_week1.get(site, {}).get("clicks", 0)
        clk_yday = snap_yday.get(site, {}).get("clicks", 0)

        if imp_w1 > imp_w2:
            trend = "▲"
        elif imp_w1 < imp_w2:
            trend = "▼"
        else:
            trend = "─"

        table.add_row(
            site,
            str(imp_w2), str(imp_w1), str(imp_yday),
            str(clk_w2), str(clk_w1), str(clk_yday),
            trend
        )

    console.print(table)
    console.print(f"\n스냅샷 날짜: 2주전={d_week2} | 1주전={d_week1} | 어제={d_yesterday}")
    console.print(f"[dim]사용법: python gsc_trend.py          # -hugo 필터[/dim]")
    console.print(f"[dim]        python gsc_trend.py ''       # 전체 사이트[/dim]")
    console.print(f"[dim]        python gsc_trend.py rotcha   # rotcha만[/dim]")

if __name__ == "__main__":
    run()
