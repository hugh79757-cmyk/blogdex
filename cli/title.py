"""타이틀 입력 → 중복체크 + 블로그별 수익 비교 추천"""
import sys
import json
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth import get_credentials
from api import get
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"

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

HIGH_VALUE_PATTERNS = [
    "추천", "비교", "가격", "후기", "리뷰", "순위", "best",
    "신청", "방법", "절차", "가입", "등록", "발급",
    "할인", "쿠폰", "무료", "이벤트", "혜택",
    "보험", "대출", "적금", "예금", "투자", "연금",
    "보조금", "지원금", "환급", "세금", "공제",
    "vs", "차이", "장단점", "구매", "구입",
]

# 너무 일반적이라 매칭에서 제외할 단어
STOP_WORDS = {
    "총정리", "정리", "방법", "신청방법", "알아보기", "확인",
    "2024", "2025", "2026", "2024년", "2025년", "2026년",
    "최신", "완벽", "가이드", "정보", "안내", "소개",
}


def extract_keywords(title):
    """타이틀에서 의미있는 키워드만 추출 (불용어 제거)"""
    words = title.replace(",", " ").replace(".", " ").replace("!", " ").split()
    keywords = [w for w in words if len(w) >= 2 and w not in STOP_WORDS]
    return keywords


def is_relevant_match(query, keywords):
    """핵심 키워드가 2개 이상 매칭되는지 확인 (느슨한 매칭 방지)"""
    q = query.lower()
    matched = 0
    for kw in keywords:
        if kw.lower() in q:
            matched += 1
    return matched >= 2


def run():
    if len(sys.argv) < 2:
        console.print("[yellow]사용법: python title.py <타이틀>[/]")
        console.print('예: python title.py "전기차 보조금 2026년 신청방법 총정리"')
        return

    title = " ".join(sys.argv[1:])
    keywords = extract_keywords(title)

    console.print(Panel(f"[bold]{title}[/]", title="입력 타이틀"))

    is_high = any(p in title for p in HIGH_VALUE_PATTERNS)
    value_label = "[red]HIGH VALUE[/]" if is_high else "[yellow]MEDIUM VALUE[/]"
    console.print(f"상업 가치: {value_label}")
    console.print(f"핵심 키워드: {', '.join(keywords)}")
    console.print(f"제외된 불용어: {', '.join(w for w in title.split() if w in STOP_WORDS)}\n")

    # 1. 중복 체크 (핵심 키워드만)
    console.print("[bold cyan]1. 기존 글 중복 체크[/]")
    found_any = False
    for kw in keywords[:5]:
        results = get("/posts/search", params={"q": kw})
        if isinstance(results, dict):
            results = results.get("results", [])
        if results:
            # 2개 이상 키워드 매칭되는 것만 표시
            relevant = []
            for r in results:
                t = r.get("title", "")
                if isinstance(t, list):
                    t = t[0] if t else ""
                t = str(t)
                matched_count = sum(1 for k in keywords if k.lower() in t.lower())
                if matched_count >= 2:
                    relevant.append((r, matched_count))

            if relevant:
                found_any = True
                relevant.sort(key=lambda x: x[1], reverse=True)
                console.print(f"  [yellow]'{kw}'[/] — 관련 글 {len(relevant)}건:")
                for r, mc in relevant[:3]:
                    t = r.get("title", "")
                    if isinstance(t, list):
                        t = t[0] if t else ""
                    console.print(f"    - [{r.get('platform','')}] {str(t)[:60]} (매칭 {mc}개)")

    if not found_any:
        console.print("  [green]중복 없음! 새로운 주제입니다.[/]")

    # 2. 스냅샷 기반 블로그별 성과
    console.print(f"\n[bold cyan]2. 블로그별 관련 키워드 성과[/]")

    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    recent_files = files[-30:]

    site_scores = {}

    for fname in recent_files:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            for kw_data in site_data.get("top_keywords", []):
                query = kw_data["query"]
                if is_relevant_match(query, keywords):
                    if site_name not in site_scores:
                        site_scores[site_name] = {
                            "clicks": 0, "impressions": 0,
                            "matched_queries": set()
                        }
                    site_scores[site_name]["clicks"] += kw_data["clicks"]
                    site_scores[site_name]["impressions"] += kw_data["impressions"]
                    site_scores[site_name]["matched_queries"].add(query)

    if site_scores:
        sorted_sites = sorted(site_scores.items(), key=lambda x: x[1]["impressions"], reverse=True)

        # 최소 노출 10 이상만 의미있는 추천
        meaningful = [(n, d) for n, d in sorted_sites if d["impressions"] >= 10]

        if meaningful:
            table = Table(title="블로그별 관련 성과 비교", box=box.ROUNDED, expand=True)
            table.add_column("블로그", style="cyan", width=20)
            table.add_column("관련 노출", justify="right", style="green", width=8)
            table.add_column("관련 클릭", justify="right", style="bold green", width=8)
            table.add_column("관련 키워드", style="yellow", width=35)

            for name, data in meaningful:
                kw_examples = ", ".join(list(data["matched_queries"])[:3])
                table.add_row(
                    name,
                    f"{data['impressions']:,}",
                    str(data["clicks"]),
                    kw_examples[:35]
                )
            console.print(table)

            best_name = meaningful[0][0]
            best_data = meaningful[0][1]
            console.print(f"\n[bold green]추천: {best_name}[/]에 발행하세요!")
            console.print(f"  이유: 관련 키워드 노출 {best_data['impressions']}회로 이 주제에 가장 강합니다.")
        else:
            console.print("  [yellow]관련 데이터가 충분하지 않습니다 (노출 10회 미만).[/]")
            _recommend_by_total(recent_files)
    else:
        console.print("  [yellow]관련 키워드 성과 없음 — 완전히 새로운 분야입니다.[/]")
        _recommend_by_total(recent_files)

    # 3. GSC 실시간 (핵심 키워드 2개 이상 매칭만)
    console.print(f"\n[bold cyan]3. GSC 실시간 키워드 확인[/]")

    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=90)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    found_gsc = False
    try:
        creds = get_credentials()
        service = build("webmasters", "v3", credentials=creds)

        for site in SITES[:6]:
            try:
                response = service.searchanalytics().query(
                    siteUrl=site["url"],
                    body={
                        "startDate": start_str,
                        "endDate": end_str,
                        "dimensions": ["query"],
                        "rowLimit": 5000,
                    }
                ).execute()

                matched = []
                for row in response.get("rows", []):
                    query = row["keys"][0]
                    if is_relevant_match(query, keywords):
                        matched.append({
                            "query": query,
                            "clicks": int(row["clicks"]),
                            "impressions": int(row["impressions"]),
                            "position": row["position"]
                        })

                if matched:
                    found_gsc = True
                    console.print(f"\n  [cyan]{site['name']}[/]:")
                    for m in sorted(matched, key=lambda x: x["impressions"], reverse=True)[:5]:
                        console.print(f"    {m['query']} — 노출 {m['impressions']}, 클릭 {m['clicks']}, 순위 {m['position']:.0f}")
            except:
                pass

        if not found_gsc:
            console.print("  [dim]관련 키워드 GSC 데이터 없음[/]")
    except:
        console.print("  [dim]GSC 인증 필요[/]")


def _recommend_by_total(recent_files):
    """전체 트래픽 기준 추천"""
    console.print("\n[cyan]전체 트래픽 기준으로 추천합니다:[/]")
    site_totals = {}
    for fname in recent_files:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            if site_name not in site_totals:
                site_totals[site_name] = 0
            site_totals[site_name] += site_data.get("impressions", 0)

    sorted_totals = sorted(site_totals.items(), key=lambda x: x[1], reverse=True)
    for name, imp in sorted_totals[:5]:
        if imp > 0:
            console.print(f"  {name}: 총 노출 {imp:,}")

    active = [(n, i) for n, i in sorted_totals if i > 0]
    if active:
        console.print(f"\n[bold green]추천: {active[0][0]}[/] — 전체 노출이 가장 높아 새 주제도 잘 받을 가능성이 높습니다.")


if __name__ == "__main__":
    run()
