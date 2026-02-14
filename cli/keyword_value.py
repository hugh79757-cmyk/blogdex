"""키워드를 수익 관점으로 분류·정렬"""
import json
import os
import sys
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"

# 상업적 의도가 높은 키워드 패턴
HIGH_VALUE_PATTERNS = [
    "추천", "비교", "가격", "후기", "리뷰", "순위", "TOP", "best",
    "신청", "방법", "절차", "가입", "등록", "발급",
    "할인", "쿠폰", "무료", "이벤트", "혜택",
    "보험", "대출", "적금", "예금", "투자", "연금",
    "보조금", "지원금", "환급", "세금", "공제",
    "vs", "차이", "장단점",
    "구매", "구입", "사는법", "파는법",
]

# 저가치 패턴
LOW_VALUE_PATTERNS = [
    "뜻", "의미", "영어로", "누구", "나이", "키", "몸무게",
    "생일", "MBTI", "학력", "고향",
]


def classify_keyword(query):
    """키워드 상업 의도 분류: high / medium / low"""
    q = query.lower()
    for pattern in HIGH_VALUE_PATTERNS:
        if pattern.lower() in q:
            return "high"
    for pattern in LOW_VALUE_PATTERNS:
        if pattern.lower() in q:
            return "low"
    return "medium"


def run():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    # 스냅샷에서 키워드 집계
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    if not files:
        console.print("[red]스냅샷 없음. python gsc_backfill.py 먼저 실행[/]")
        return

    # 최근 N일 필터
    recent_files = files[-days:]
    console.print(f"[cyan]스냅샷 {len(recent_files)}일치 분석 중...[/]\n")

    keyword_data = {}

    for fname in recent_files:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            for kw in site_data.get("top_keywords", []):
                query = kw["query"]
                if query not in keyword_data:
                    keyword_data[query] = {
                        "clicks": 0,
                        "impressions": 0,
                        "best_site": "",
                        "best_impressions": 0,
                        "positions": [],
                    }
                keyword_data[query]["clicks"] += kw["clicks"]
                keyword_data[query]["impressions"] += kw["impressions"]
                keyword_data[query]["positions"].append(kw["position"])
                if kw["impressions"] > keyword_data[query]["best_impressions"]:
                    keyword_data[query]["best_site"] = site_name
                    keyword_data[query]["best_impressions"] = kw["impressions"]

    # 분류 및 점수 계산
    scored = []
    for query, data in keyword_data.items():
        value_class = classify_keyword(query)
        avg_pos = sum(data["positions"]) / len(data["positions"]) if data["positions"] else 99
        ctr = (data["clicks"] / data["impressions"] * 100) if data["impressions"] > 0 else 0

        # 수익 점수: 노출 × 가치 가중치
        weight = {"high": 3.0, "medium": 1.0, "low": 0.3}
        score = data["impressions"] * weight[value_class]

        # 순위 보너스: 11~20위는 1페이지 진입 가능 = 높은 기회
        if 5 <= avg_pos <= 20:
            score *= 1.5

        scored.append({
            "query": query,
            "clicks": data["clicks"],
            "impressions": data["impressions"],
            "ctr": ctr,
            "avg_pos": avg_pos,
            "value": value_class,
            "score": score,
            "best_site": data["best_site"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    # 고가치 키워드 테이블
    high_value = [s for s in scored if s["value"] == "high"]
    table = Table(title=f"고가치 키워드 TOP 30 ({len(recent_files)}일 누적)", box=box.ROUNDED, expand=True)
    table.add_column("키워드", style="bold white", width=28)
    table.add_column("노출", justify="right", style="cyan", width=8)
    table.add_column("클릭", justify="right", style="green", width=6)
    table.add_column("CTR", justify="right", style="yellow", width=7)
    table.add_column("순위", justify="right", style="magenta", width=6)
    table.add_column("수익점수", justify="right", style="bold red", width=8)
    table.add_column("사이트", style="dim", width=18)

    for s in high_value[:30]:
        table.add_row(
            s["query"][:28],
            f"{s['impressions']:,}",
            str(s["clicks"]),
            f"{s['ctr']:.1f}%",
            f"{s['avg_pos']:.1f}",
            f"{s['score']:.0f}",
            s["best_site"]
        )
    console.print(table)

    # 전체 요약
    table2 = Table(title=f"전체 수익 점수 TOP 30", box=box.ROUNDED, expand=True)
    table2.add_column("키워드", style="white", width=28)
    table2.add_column("가치", style="bold", width=6)
    table2.add_column("노출", justify="right", style="cyan", width=8)
    table2.add_column("클릭", justify="right", style="green", width=6)
    table2.add_column("순위", justify="right", style="magenta", width=6)
    table2.add_column("점수", justify="right", style="bold red", width=8)
    table2.add_column("사이트", style="dim", width=18)

    for s in scored[:30]:
        vc = {"high": "[red]HIGH[/]", "medium": "[yellow]MED[/]", "low": "[dim]LOW[/]"}
        table2.add_row(
            s["query"][:28],
            vc[s["value"]],
            f"{s['impressions']:,}",
            str(s["clicks"]),
            f"{s['avg_pos']:.1f}",
            f"{s['score']:.0f}",
            s["best_site"]
        )
    console.print(table2)

    # 통계
    total_high = len([s for s in scored if s["value"] == "high"])
    total_med = len([s for s in scored if s["value"] == "medium"])
    total_low = len([s for s in scored if s["value"] == "low"])
    console.print(f"\n전체 키워드: {len(scored)}개")
    console.print(f"  [red]HIGH[/] {total_high}개 | [yellow]MED[/] {total_med}개 | [dim]LOW[/] {total_low}개")


if __name__ == "__main__":
    run()
