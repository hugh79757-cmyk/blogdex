"""CTR 개선으로 바로 수익 올릴 수 있는 글 찾기"""
import sys
from urllib.parse import unquote
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

# 실제 트래픽이 있는 사이트에 집중
SITES = [
    {"url": "https://rotcha.kr/", "name": "rotcha.kr"},
    {"url": "https://techpawz.com/", "name": "techpawz.com"},
    {"url": "https://informationhot.kr/", "name": "informationhot.kr"},
    {"url": "https://ud.informationhot.kr/", "name": "ud.info"},
    {"url": "https://travel.rotcha.kr/", "name": "travel.rotcha"},
    {"url": "https://stock.informationhot.kr/", "name": "stock.info"},
    {"url": "https://5.informationhot.kr/", "name": "5.info"},
    {"url": "https://65.informationhot.kr/", "name": "65.info"},
    {"url": "https://kuta.informationhot.kr/", "name": "kuta.info"},
    {"url": "https://issue.techpawz.com/", "name": "issue.tech"},
    {"url": "https://2.techpawz.com/", "name": "2.techpawz"},
    {"url": "https://hotissue.rotcha.kr/", "name": "hotissue"},
    {"url": "https://info.techpawz.com/", "name": "info.tech"},
]


def get_page_keywords(service, site_url, page_url, start_str, end_str):
    """특정 페이지에 유입되는 키워드 목록"""
    try:
        resp = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start_str,
                "endDate": end_str,
                "dimensions": ["query"],
                "dimensionFilterGroups": [{
                    "filters": [{
                        "dimension": "page",
                        "expression": page_url
                    }]
                }],
                "rowLimit": 5,
            }
        ).execute()
        return resp.get("rows", [])
    except:
        return []


def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)

    console.print(f"[bold]리라이트 큐 — 수익 개선 대상 ({days}일)[/]\n")

    all_opportunities = []

    for site in SITES:
        try:
            resp = service.searchanalytics().query(
                siteUrl=site["url"],
                body={
                    "startDate": start_str,
                    "endDate": end_str,
                    "dimensions": ["page"],
                    "rowLimit": 200,
                }
            ).execute()

            for row in resp.get("rows", []):
                page = row["keys"][0]
                clicks = int(row["clicks"])
                impressions = int(row["impressions"])
                ctr = row["ctr"] * 100
                position = row["position"]

                action = None
                priority = 0

                # 현재 트래픽 규모에 맞춘 임계값
                if position <= 10 and ctr < 5 and impressions >= 10:
                    action = "타이틀/메타 개선"
                    priority = impressions * (10 - ctr)
                elif 10 < position <= 20 and impressions >= 10:
                    action = "콘텐츠 보강 → 1페이지"
                    priority = impressions * 2
                elif impressions >= 20 and clicks == 0:
                    action = "타이틀 전면 교체"
                    priority = impressions * 5

                if action:
                    all_opportunities.append({
                        "site": site["name"],
                        "site_url": site["url"],
                        "page": page,
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                        "action": action,
                        "priority": priority,
                    })

        except Exception as e:
            console.print(f"  [red]{site['name']}[/]: {e}")

    all_opportunities.sort(key=lambda x: x["priority"], reverse=True)

    if not all_opportunities:
        console.print("[yellow]개선 대상이 없습니다.[/]")
        return

    # 상세 출력 (키워드 포함)
    console.print(f"[bold green]개선 대상 {len(all_opportunities)}건 발견[/]\n")

    for idx, o in enumerate(all_opportunities[:20], 1):
        decoded = unquote(o["page"])
        short = decoded.replace(o["site_url"], "/")

        # 이 페이지의 유입 키워드
        kw_rows = get_page_keywords(service, o["site_url"], o["page"], start_str, end_str)
        kw_list = []
        for kr in kw_rows:
            kw_list.append(f"{kr['keys'][0]} (노출{int(kr['impressions'])}, 순위{kr['position']:.0f})")

        action_color = {
            "타이틀/메타 개선": "bold red",
            "콘텐츠 보강 → 1페이지": "bold yellow",
            "타이틀 전면 교체": "bold magenta",
        }

        console.print(Panel(
            f"[cyan]{o['site']}[/] | 노출 [green]{o['impressions']}[/] | "
            f"클릭 {o['clicks']} | CTR {o['ctr']:.1f}% | 순위 {o['position']:.1f}\n"
            f"URL: {short}\n"
            f"키워드: {', '.join(kw_list) if kw_list else '(데이터 부족)'}\n"
            f"[{action_color.get(o['action'], 'white')}]액션: {o['action']}[/]",
            title=f"#{idx}",
            width=80
        ))

    # 요약
    title_fixes = len([o for o in all_opportunities if o["action"] == "타이틀/메타 개선"])
    content_fixes = len([o for o in all_opportunities if o["action"] == "콘텐츠 보강 → 1페이지"])
    zero_fixes = len([o for o in all_opportunities if o["action"] == "타이틀 전면 교체"])

    console.print(f"\n[bold]전체 {len(all_opportunities)}건[/]")
    console.print(f"  [red]타이틀/메타 개선[/]: {title_fixes}건 — 가장 빠른 효과")
    console.print(f"  [yellow]콘텐츠 보강[/]: {content_fixes}건 — 1~2주 소요")
    console.print(f"  [magenta]타이틀 전면 교체[/]: {zero_fixes}건 — 노출만 되고 클릭 0")


if __name__ == "__main__":
    run()
