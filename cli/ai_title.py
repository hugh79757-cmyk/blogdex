"""AI 기반 타이틀 최적화 - GPT-4o-mini"""
import sys
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from googleapiclient.discovery import build
from google_auth import get_credentials
from api import get
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

# .env 로드 (프로젝트 루트)
load_dotenv("/Users/twinssn/Projects/blogdex/.env")

console = Console()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"

SITES = [
    {"url": "https://rotcha.kr/", "name": "rotcha.kr"},
    {"url": "https://techpawz.com/", "name": "techpawz.com"},
    {"url": "https://informationhot.kr/", "name": "informationhot.kr"},
    {"url": "https://ud.informationhot.kr/", "name": "ud.info"},
    {"url": "https://travel.rotcha.kr/", "name": "travel.rotcha"},
    {"url": "https://stock.informationhot.kr/", "name": "stock.info"},
]

HIGH_VALUE_PATTERNS = [
    "추천", "비교", "가격", "후기", "리뷰", "순위",
    "신청", "방법", "절차", "가입", "등록", "발급",
    "할인", "쿠폰", "무료", "혜택",
    "보험", "대출", "적금", "투자",
    "보조금", "지원금", "환급", "세금",
    "vs", "차이", "장단점", "구매",
]


def generate_titles(keyword, context):
    """GPT-4o-mini로 CTR 높은 타이틀 5개 생성"""
    prompt = f"""당신은 한국어 블로그 SEO 전문가입니다.

아래 키워드로 검색하는 사용자가 클릭하고 싶은 블로그 타이틀 5개를 만들어주세요.

키워드: {keyword}

참고 정보:
{context}

규칙:
1. 각 타이틀은 40~60자 사이
2. 숫자를 포함하면 CTR이 올라갑니다 (예: "3가지", "5분만에", "2026년")
3. 구체적인 혜택이나 결과를 제시하세요
4. 괄호를 활용하세요 (예: [총정리], (최신))
5. 검색 의도에 정확히 맞춰주세요
6. 낚시성 제목은 피하세요
7. 타이틀만 출력하세요. 번호와 타이틀만.

출력 형식:
1. 타이틀1
2. 타이틀2
3. 타이틀3
4. 타이틀4
5. 타이틀5"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=500,
        )
        text = response.choices[0].message.content.strip()
        titles = []
        for line in text.split("\n"):
            line = line.strip()
            if line and line[0].isdigit() and "." in line:
                title = line.split(".", 1)[1].strip()
                titles.append(title)
        return titles
    except Exception as e:
        console.print(f"[red]OpenAI 오류: {e}[/]")
        return []


def rewrite_title(original_title, keyword, gsc_data):
    """기존 타이틀을 CTR 높게 리라이트"""
    prompt = f"""당신은 한국어 블로그 SEO 전문가입니다.

아래 블로그 글의 타이틀을 CTR(클릭률)이 높아지도록 개선해주세요.

현재 타이틀: {original_title}
주요 키워드: {keyword}
현재 성과: {gsc_data}

규칙:
1. 키워드를 반드시 포함
2. 40~60자 사이
3. 숫자 활용
4. 검색자가 바로 클릭하고 싶은 구체적 혜택 제시
5. 개선안 3개 제시
6. 각 개선안에 대해 왜 더 나은지 한줄 설명

출력 형식:
1. 개선 타이틀 - 이유
2. 개선 타이틀 - 이유
3. 개선 타이틀 - 이유"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        console.print(f"[red]OpenAI 오류: {e}[/]")
        return ""


def cmd_generate():
    """키워드 입력 → 타이틀 5개 생성 + 블로그 추천"""
    if len(sys.argv) < 3:
        console.print("[yellow]사용법: python ai_title.py gen <키워드>[/]")
        console.print('예: python ai_title.py gen "전기차 보조금 신청"')
        return

    keyword = " ".join(sys.argv[2:])
    console.print(Panel(f"[bold]{keyword}[/]", title="타이틀 생성"))

    # 중복 체크
    console.print("[cyan]1. 중복 체크...[/]")
    words = keyword.split()
    found = False
    for w in words:
        if len(w) < 2:
            continue
        results = get("/posts/search", params={"q": w})
        if isinstance(results, dict):
            results = results.get("results", [])
        relevant = [r for r in results if sum(1 for kw in words if kw.lower() in str(r.get("title", "")).lower()) >= 2]
        if relevant:
            found = True
            console.print(f"  [yellow]관련 기존 글 {len(relevant)}건 발견[/]")
            for r in relevant[:3]:
                t = r.get("title", "")
                if isinstance(t, list):
                    t = t[0] if t else ""
                console.print(f"    - {str(t)[:60]}")
            break

    if not found:
        console.print("  [green]중복 없음[/]")

    # GSC에서 관련 데이터
    console.print("[cyan]2. GSC 데이터 수집...[/]")
    context_parts = []

    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    recent = files[-30:]
    related_queries = set()

    for fname in recent:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            for kw in site_data.get("top_keywords", []):
                for w in words:
                    if len(w) >= 2 and w.lower() in kw["query"].lower():
                        related_queries.add(kw["query"])
                        break

    if related_queries:
        context_parts.append(f"관련 검색어: {', '.join(list(related_queries)[:10])}")

    # 상업 가치 확인
    is_high = any(p in keyword for p in HIGH_VALUE_PATTERNS)
    if is_high:
        context_parts.append("이 키워드는 상업적 의도가 높습니다 (구매/신청 관련)")
    else:
        context_parts.append("이 키워드는 정보성 검색입니다")

    context = "\n".join(context_parts) if context_parts else "추가 정보 없음"

    # 타이틀 생성
    console.print("[cyan]3. AI 타이틀 생성 중...[/]\n")
    titles = generate_titles(keyword, context)

    if titles:
        table = Table(title="생성된 타이틀 후보", box=box.ROUNDED, expand=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("타이틀", style="bold white")
        table.add_column("글자수", justify="right", style="cyan", width=6)

        for i, t in enumerate(titles, 1):
            table.add_row(str(i), t, str(len(t)))
        console.print(table)

    # 블로그 추천
    console.print("\n[cyan]4. 발행 블로그 추천...[/]")
    site_totals = {}
    for fname in recent:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            if site_name not in site_totals:
                site_totals[site_name] = {"impressions": 0, "related": 0}
            site_totals[site_name]["impressions"] += site_data.get("impressions", 0)
            for kw in site_data.get("top_keywords", []):
                for w in words:
                    if len(w) >= 2 and w.lower() in kw["query"].lower():
                        site_totals[site_name]["related"] += kw["impressions"]
                        break

    # 관련 노출 기준, 없으면 전체 노출 기준
    has_related = any(v["related"] > 0 for v in site_totals.values())
    sort_key = "related" if has_related else "impressions"
    sorted_sites = sorted(site_totals.items(), key=lambda x: x[1][sort_key], reverse=True)

    if sorted_sites:
        best = sorted_sites[0]
        reason = f"관련 노출 {best[1]['related']}회" if has_related else f"전체 노출 {best[1]['impressions']}회"
        console.print(f"\n[bold green]추천: {best[0]}[/]에 발행 ({reason})")


def cmd_rewrite():
    """rewrite_queue의 글들을 AI로 타이틀 개선"""
    from urllib.parse import unquote

    days = 30
    end = datetime.now() - timedelta(days=2)
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")

    creds = get_credentials()
    service = build("webmasters", "v3", credentials=creds)

    console.print("[bold]CTR 낮은 글 AI 타이틀 개선[/]\n")

    targets = []

    for site in SITES:
        try:
            # 페이지별 성과
            resp = service.searchanalytics().query(
                siteUrl=site["url"],
                body={
                    "startDate": start_str,
                    "endDate": end_str,
                    "dimensions": ["page"],
                    "rowLimit": 100,
                }
            ).execute()

            for row in resp.get("rows", []):
                page = row["keys"][0]
                impressions = int(row["impressions"])
                ctr = row["ctr"] * 100
                position = row["position"]

                if position <= 10 and ctr < 5 and impressions >= 10:
                    # 이 페이지의 키워드
                    try:
                        kw_resp = service.searchanalytics().query(
                            siteUrl=site["url"],
                            body={
                                "startDate": start_str,
                                "endDate": end_str,
                                "dimensions": ["query"],
                                "dimensionFilterGroups": [{
                                    "filters": [{
                                        "dimension": "page",
                                        "expression": page
                                    }]
                                }],
                                "rowLimit": 5,
                            }
                        ).execute()
                        kw_rows = kw_resp.get("rows", [])
                        top_kw = kw_rows[0]["keys"][0] if kw_rows else ""
                    except:
                        top_kw = ""

                    targets.append({
                        "site": site["name"],
                        "page": page,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                        "keyword": top_kw,
                    })
        except:
            pass

    targets.sort(key=lambda x: x["impressions"], reverse=True)

    if not targets:
        console.print("[yellow]개선 대상 없음[/]")
        return

    console.print(f"[green]개선 대상 {len(targets)}건 발견[/]\n")

    for idx, t in enumerate(targets[:10], 1):
        decoded = unquote(t["page"])
        short = decoded.split("/")[-1] if "/" in decoded else decoded
        # URL에서 타이틀 추정 (한글 URL slug)
        original_title = short.replace("-", " ").replace("_", " ")

        gsc_info = f"노출 {t['impressions']}, CTR {t['ctr']:.1f}%, 순위 {t['position']:.0f}"

        console.print(Panel(
            f"[cyan]{t['site']}[/] | {gsc_info}\n"
            f"URL: {decoded[:70]}\n"
            f"키워드: {t['keyword']}",
            title=f"#{idx}"
        ))

        if t["keyword"]:
            result = rewrite_title(original_title, t["keyword"], gsc_info)
            if result:
                console.print(result)
                console.print()


def cmd_bulk():
    """analyze.py의 기회 목록에 대해 일괄 타이틀 생성"""
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
    recent = files[-30:]

    all_keywords = {}
    for fname in recent:
        filepath = os.path.join(SNAPSHOT_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        for site_name, site_data in snapshot.get("sites", {}).items():
            if "error" in site_data:
                continue
            for kw in site_data.get("top_keywords", []):
                query = kw["query"]
                if query not in all_keywords:
                    all_keywords[query] = {"impressions": 0, "best_site": "", "best_imp": 0}
                all_keywords[query]["impressions"] += kw["impressions"]
                if kw["impressions"] > all_keywords[query]["best_imp"]:
                    all_keywords[query]["best_site"] = site_name
                    all_keywords[query]["best_imp"] = kw["impressions"]

    # 상위 키워드에 대해 타이틀 생성
    sorted_kw = sorted(all_keywords.items(), key=lambda x: x[1]["impressions"], reverse=True)

    # 이미 쓴 글 필터
    my_posts = get("/posts/search", params={"q": ""})
    if isinstance(my_posts, dict):
        my_posts = my_posts.get("results", [])
    my_titles = [str(p.get("title", "")).lower() for p in my_posts]

    console.print("[bold]고노출 키워드 일괄 타이틀 생성[/]\n")

    count = 0
    for kw, data in sorted_kw:
        if count >= 5:
            break

        already = any(kw.lower() in t for t in my_titles)
        if already:
            continue

        console.print(f"\n[bold cyan]키워드: {kw}[/] (노출 {data['impressions']}, 추천: {data['best_site']})")

        titles = generate_titles(kw, f"추천 블로그: {data['best_site']}, 월간 노출: {data['impressions']}회")
        if titles:
            for i, t in enumerate(titles, 1):
                console.print(f"  {i}. {t}")
        count += 1


def main():
    if len(sys.argv) < 2:
        console.print("[bold]AI 타이틀 최적화[/]\n")
        console.print("  python ai_title.py gen <키워드>    키워드로 타이틀 5개 생성")
        console.print("  python ai_title.py rewrite         CTR 낮은 글 타이틀 개선")
        console.print("  python ai_title.py bulk            고노출 키워드 일괄 생성")
        console.print()
        console.print('예: python ai_title.py gen "전기차 보조금 신청방법"')
        return

    cmd = sys.argv[1]
    if cmd == "gen":
        cmd_generate()
    elif cmd == "rewrite":
        cmd_rewrite()
    elif cmd == "bulk":
        cmd_bulk()
    else:
        console.print(f"[red]알 수 없는 명령: {cmd}[/]")


if __name__ == "__main__":
    main()
