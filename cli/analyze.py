"""Blogdex 글쓰기 기회 분석 - 수익 점수 기반"""
import sys
import json
import os
from api import get
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"

HIGH_VALUE_PATTERNS = [
    "추천", "비교", "가격", "후기", "리뷰", "순위", "best",
    "신청", "방법", "절차", "가입", "등록", "발급",
    "할인", "쿠폰", "무료", "이벤트", "혜택",
    "보험", "대출", "적금", "예금", "투자", "연금",
    "보조금", "지원금", "환급", "세금", "공제",
    "vs", "차이", "장단점", "구매", "구입", "사는법",
]

LOW_VALUE_PATTERNS = [
    "뜻", "의미", "영어로", "누구", "나이", "키", "몸무게",
    "생일", "mbti", "학력", "고향",
]

# 수익 가능성이 없는 키워드 패턴 (필터링)
JUNK_PATTERNS = [
    "야스", "섹스", "업소", "19금", "성인",
    "eorneo", "ㅡㄴ", "ㅣㅡ",  # 오타/의미없는 검색
]

EXPECTED_CTR = {
    1: 0.30, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05,
    6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018,
    15: 0.01, 20: 0.005, 30: 0.002,
}


def get_expected_ctr(position):
    if position <= 1:
        return 0.30
    for pos in sorted(EXPECTED_CTR.keys()):
        if position <= pos:
            return EXPECTED_CTR[pos]
    return 0.001


def classify_keyword(query):
    q = query.lower()
    for p in HIGH_VALUE_PATTERNS:
        if p.lower() in q:
            return "high"
    for p in LOW_VALUE_PATTERNS:
        if p.lower() in q:
            return "low"
    return "medium"


def is_junk(query):
    q = query.lower()
    for p in JUNK_PATTERNS:
        if p in q:
            return True
    # 한글이 거의 없는 의미없는 검색
    korean_chars = sum(1 for c in q if '\uac00' <= c <= '\ud7a3')
    if len(q) > 3 and korean_chars == 0 and not any(c.isalpha() for c in q):
        return True
    return False


def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    # 1. 스냅샷에서 키워드 집계
    console.print("[cyan]1. GSC 스냅샷에서 키워드 수집...[/]")
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    if not files:
        console.print("[red]스냅샷 없음. python gsc_backfill.py 먼저 실행[/]")
        return

    recent_files = files[-days:]

    all_keywords = {}
    for fname in recent_files:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            for kw in site_data.get("top_keywords", []):
                query = kw["query"]
                if is_junk(query):
                    continue
                if query not in all_keywords:
                    all_keywords[query] = {
                        "clicks": 0, "impressions": 0,
                        "best_site": "", "best_impressions": 0,
                        "positions": [], "sites": set()
                    }
                all_keywords[query]["clicks"] += kw["clicks"]
                all_keywords[query]["impressions"] += kw["impressions"]
                all_keywords[query]["positions"].append(kw["position"])
                all_keywords[query]["sites"].add(site_name)
                if kw["impressions"] > all_keywords[query]["best_impressions"]:
                    all_keywords[query]["best_site"] = site_name
                    all_keywords[query]["best_impressions"] = kw["impressions"]

    console.print(f"  유효 키워드: {len(all_keywords)}개")

    # 2. 내 포스트 로딩
    console.print("[cyan]2. 내 포스트 로딩...[/]")
    my_posts = get("/posts/search", params={"q": ""})
    if isinstance(my_posts, dict):
        my_posts = my_posts.get("results", [])
    my_titles_lower = []
    for p in my_posts:
        t = p.get("title", "")
        if isinstance(t, list):
            t = t[0] if t else ""
        my_titles_lower.append(str(t).lower())
    console.print(f"  내 포스트: {len(my_posts)}개")

    # 3. 수집 타이틀 로딩
    console.print("[cyan]3. 수집 타이틀 로딩...[/]")
    titles = get("/titles/search", params={"q": ""})
    if isinstance(titles, dict):
        titles = titles.get("results", [])
    console.print(f"  수집 타이틀: {len(titles)}개")

    # 4. 수익 점수 기반 분석
    console.print("[cyan]4. 수익 점수 분석 중...[/]\n")

    opportunities = []

    for kw, data in all_keywords.items():
        if data["impressions"] < 3:
            continue

        already_written = any(kw.lower() in t for t in my_titles_lower)

        matched_titles = []
        for t in titles:
            title_text = t.get("title", "")
            if isinstance(title_text, list):
                title_text = title_text[0] if title_text else ""
            if kw.lower() in str(title_text).lower():
                matched_titles.append(str(title_text))

        avg_pos = sum(data["positions"]) / len(data["positions"]) if data["positions"] else 99
        value_class = classify_keyword(kw)

        value_weight = {"high": 3.0, "medium": 1.0, "low": 0.3}
        expected_ctr = get_expected_ctr(avg_pos)
        expected_monthly_clicks = data["impressions"] * expected_ctr
        revenue_score = expected_monthly_clicks * value_weight[value_class]

        if already_written:
            revenue_score *= 0.1

        if matched_titles:
            revenue_score *= 1.3

        if 5 <= avg_pos <= 20:
            revenue_score *= 1.5

        opportunities.append({
            "keyword": kw,
            "impressions": data["impressions"],
            "clicks": data["clicks"],
            "avg_pos": avg_pos,
            "value": value_class,
            "score": revenue_score,
            "best_site": data["best_site"],
            "sites": list(data["sites"]),
            "already_written": already_written,
            "matched_titles": matched_titles[:3],
            "expected_clicks": expected_monthly_clicks,
        })

    opportunities.sort(key=lambda x: x["score"], reverse=True)

    new_opps = [o for o in opportunities if not o["already_written"]]
    rewrite_opps = [o for o in opportunities if o["already_written"] and o["score"] > 0]

    console.print(Panel(
        f"유효 키워드: {len(all_keywords)}개\n"
        f"새로 쓸 기회: {len(new_opps)}개\n"
        f"기존 글 개선: {len(rewrite_opps)}개",
        title="분석 결과 요약"
    ))

    if new_opps:
        table = Table(title=f"새 글 기회 TOP 30 (수익 점수순)", box=box.ROUNDED, expand=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("키워드", style="bold white", width=25)
        table.add_column("가치", width=5)
        table.add_column("노출", justify="right", style="cyan", width=6)
        table.add_column("예상클릭", justify="right", style="green", width=7)
        table.add_column("순위", justify="right", style="magenta", width=5)
        table.add_column("점수", justify="right", style="bold red", width=6)
        table.add_column("추천블로그", style="yellow", width=15)
        table.add_column("참고타이틀", style="dim", width=25)

        for idx, o in enumerate(new_opps[:30], 1):
            vc = {"high": "[red]H[/]", "medium": "[yellow]M[/]", "low": "[dim]L[/]"}
            ref = o["matched_titles"][0][:25] if o["matched_titles"] else "-"
            table.add_row(
                str(idx),
                o["keyword"][:25],
                vc[o["value"]],
                f"{o['impressions']:,}",
                f"{o['expected_clicks']:.1f}",
                f"{o['avg_pos']:.0f}",
                f"{o['score']:.0f}",
                o["best_site"],
                ref
            )
        console.print(table)

    if rewrite_opps:
        table2 = Table(title=f"기존 글 개선 TOP 15", box=box.ROUNDED, expand=True)
        table2.add_column("#", style="dim", width=3)
        table2.add_column("키워드", style="white", width=25)
        table2.add_column("가치", width=5)
        table2.add_column("노출", justify="right", style="cyan", width=6)
        table2.add_column("클릭", justify="right", style="green", width=5)
        table2.add_column("순위", justify="right", style="magenta", width=5)
        table2.add_column("사이트", style="yellow", width=15)

        for idx, o in enumerate(rewrite_opps[:15], 1):
            vc = {"high": "[red]H[/]", "medium": "[yellow]M[/]", "low": "[dim]L[/]"}
            table2.add_row(
                str(idx),
                o["keyword"][:25],
                vc[o["value"]],
                f"{o['impressions']:,}",
                str(o["clicks"]),
                f"{o['avg_pos']:.0f}",
                o["best_site"]
            )
        console.print(table2)

    if new_opps:
        best = new_opps[0]
        console.print(f"\n[bold green]1순위 추천:[/] '{best['keyword']}' → [cyan]{best['best_site']}[/]에 발행")
        console.print(f"  노출 {best['impressions']}회, 예상 클릭 {best['expected_clicks']:.1f}회/월, 수익점수 {best['score']:.0f}")
        if best["matched_titles"]:
            console.print(f"  참고: {best['matched_titles'][0]}")


if __name__ == "__main__":
    console.print("[bold]Blogdex 수익 기반 글쓰기 기회 분석[/]")
    console.print("  python analyze.py        최근 30일")
    console.print("  python analyze.py 90     최근 90일")
    console.print()
    run()
