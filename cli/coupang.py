"""쿠팡 파트너스 수익 CSV 임포트 및 분석"""
import sys
import os
import csv
import json
import glob
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()

COUPANG_DIR = "/Users/twinssn/Projects/blogdex/cli/coupang_data"
COUPANG_DB = os.path.join(COUPANG_DIR, "coupang_history.json")


def load_history():
    """누적 수익 데이터 로드"""
    if os.path.exists(COUPANG_DB):
        with open(COUPANG_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": [], "imported_files": []}


def save_history(history):
    """누적 수익 데이터 저장"""
    with open(COUPANG_DB, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def cmd_import(filepath):
    """쿠팡 파트너스 CSV 임포트
    
    쿠팡 CSV 컬럼이 다를 수 있으므로 자동 감지합니다.
    일반적인 쿠팡 파트너스 리포트 컬럼:
    - 날짜, 클릭수, 주문수, 주문금액, 커미션
    또는
    - 날짜, 서브ID, 클릭, 구매건수, 구매금액, 수익금
    """
    if not os.path.exists(filepath):
        console.print(f"[red]파일 없음: {filepath}[/]")
        return

    history = load_history()
    fname = os.path.basename(filepath)

    if fname in history["imported_files"]:
        console.print(f"[yellow]{fname} — 이미 임포트됨. 스킵.[/]")
        return

    records = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, None)

        if not header:
            console.print("[red]빈 CSV[/]")
            return

        # 헤더 정규화 (공백, BOM 제거)
        header = [h.strip().replace("\ufeff", "") for h in header]
        console.print(f"[dim]CSV 컬럼: {header}[/]")

        # 컬럼 매핑 자동 감지
        col_map = {}
        for i, h in enumerate(header):
            hl = h.lower()
            if "날짜" in hl or "date" in hl:
                col_map["date"] = i
            elif "서브" in hl or "sub" in hl:
                col_map["sub_id"] = i
            elif "클릭" in hl or "click" in hl:
                col_map["clicks"] = i
            elif "주문수" in hl or "구매건" in hl or "order" in hl:
                col_map["orders"] = i
            elif "주문금액" in hl or "구매금액" in hl or "amount" in hl:
                col_map["amount"] = i
            elif "커미션" in hl or "수익" in hl or "commission" in hl or "revenue" in hl:
                col_map["revenue"] = i
            elif "상품" in hl or "product" in hl:
                col_map["product"] = i
            elif "url" in hl or "링크" in hl or "페이지" in hl:
                col_map["url"] = i

        console.print(f"[dim]매핑: {col_map}[/]")

        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue

            record = {"source_file": fname}

            for key, idx in col_map.items():
                if idx < len(row):
                    val = row[idx].strip()
                    if key in ("clicks", "orders"):
                        try:
                            val = int(val.replace(",", ""))
                        except:
                            val = 0
                    elif key in ("amount", "revenue"):
                        try:
                            val = float(val.replace(",", "").replace("원", "").replace("₩", ""))
                        except:
                            val = 0.0
                    record[key] = val

            records.append(record)

    if records:
        history["records"].extend(records)
        history["imported_files"].append(fname)
        save_history(history)
        console.print(f"[green]{fname} — {len(records)}건 임포트 완료[/]")
    else:
        console.print(f"[yellow]{fname} — 데이터 없음[/]")


def cmd_import_dir():
    """coupang_data 폴더의 모든 CSV 임포트"""
    files = glob.glob(os.path.join(COUPANG_DIR, "*.csv"))
    if not files:
        console.print(f"[yellow]{COUPANG_DIR} 에 CSV 없음[/]")
        console.print("쿠팡 파트너스 대시보드에서 CSV 다운로드 후 이 폴더에 넣으세요.")
        return

    console.print(f"[cyan]{len(files)}개 CSV 발견[/]\n")
    for f in sorted(files):
        cmd_import(f)


def cmd_summary():
    """수익 요약 분석"""
    history = load_history()
    records = history.get("records", [])

    if not records:
        console.print("[yellow]임포트된 데이터 없음[/]")
        console.print(f"1. 쿠팡 파트너스에서 CSV 다운로드")
        console.print(f"2. {COUPANG_DIR}/ 에 파일 넣기")
        console.print(f"3. python coupang.py import")
        return

    # 전체 요약
    total_clicks = sum(r.get("clicks", 0) for r in records)
    total_orders = sum(r.get("orders", 0) for r in records)
    total_amount = sum(r.get("amount", 0) for r in records)
    total_revenue = sum(r.get("revenue", 0) for r in records)

    console.print(Panel(
        f"총 클릭: {total_clicks:,}\n"
        f"총 주문: {total_orders:,}\n"
        f"총 주문금액: {total_amount:,.0f}원\n"
        f"총 수익: {total_revenue:,.0f}원\n"
        f"전환율: {(total_orders / total_clicks * 100) if total_clicks > 0 else 0:.2f}%\n"
        f"데이터: {len(records)}건, 파일: {len(history.get('imported_files', []))}개",
        title="쿠팡 파트너스 전체 요약"
    ))

    # 날짜별 추이
    daily = {}
    for r in records:
        date = r.get("date", "unknown")
        if date not in daily:
            daily[date] = {"clicks": 0, "orders": 0, "revenue": 0.0}
        daily[date]["clicks"] += r.get("clicks", 0)
        daily[date]["orders"] += r.get("orders", 0)
        daily[date]["revenue"] += r.get("revenue", 0)

    if len(daily) > 1:
        table = Table(title="날짜별 수익 추이", box=box.ROUNDED, expand=True)
        table.add_column("날짜", style="cyan", width=12)
        table.add_column("클릭", justify="right", style="white", width=8)
        table.add_column("주문", justify="right", style="green", width=6)
        table.add_column("수익", justify="right", style="bold yellow", width=12)
        table.add_column("전환율", justify="right", style="magenta", width=8)

        for date in sorted(daily.keys())[-30:]:
            d = daily[date]
            cvr = (d["orders"] / d["clicks"] * 100) if d["clicks"] > 0 else 0
            table.add_row(
                date,
                f"{d['clicks']:,}",
                str(d["orders"]),
                f"{d['revenue']:,.0f}원",
                f"{cvr:.1f}%"
            )
        console.print(table)

    # 서브ID별 (블로그별) 분석
    by_sub = {}
    for r in records:
        sub = r.get("sub_id", "미지정")
        if not sub:
            sub = "미지정"
        if sub not in by_sub:
            by_sub[sub] = {"clicks": 0, "orders": 0, "revenue": 0.0}
        by_sub[sub]["clicks"] += r.get("clicks", 0)
        by_sub[sub]["orders"] += r.get("orders", 0)
        by_sub[sub]["revenue"] += r.get("revenue", 0)

    if by_sub and not (len(by_sub) == 1 and "미지정" in by_sub):
        table2 = Table(title="서브ID(블로그)별 수익", box=box.ROUNDED, expand=True)
        table2.add_column("서브ID", style="cyan", width=20)
        table2.add_column("클릭", justify="right", style="white", width=8)
        table2.add_column("주문", justify="right", style="green", width=6)
        table2.add_column("수익", justify="right", style="bold yellow", width=12)
        table2.add_column("전환율", justify="right", style="magenta", width=8)

        sorted_subs = sorted(by_sub.items(), key=lambda x: x[1]["revenue"], reverse=True)
        for sub, d in sorted_subs:
            cvr = (d["orders"] / d["clicks"] * 100) if d["clicks"] > 0 else 0
            table2.add_row(
                sub[:20],
                f"{d['clicks']:,}",
                str(d["orders"]),
                f"{d['revenue']:,.0f}원",
                f"{cvr:.1f}%"
            )
        console.print(table2)
        console.print("\n[dim]팁: 쿠팡 링크에 서브ID를 블로그별로 다르게 넣으면 어떤 블로그가 수익을 내는지 추적됩니다.[/]")

    # 상품별 분석
    by_product = {}
    for r in records:
        product = r.get("product", "")
        if not product:
            continue
        if product not in by_product:
            by_product[product] = {"orders": 0, "revenue": 0.0}
        by_product[product]["orders"] += r.get("orders", 0)
        by_product[product]["revenue"] += r.get("revenue", 0)

    if by_product:
        table3 = Table(title="상품별 수익 TOP 15", box=box.ROUNDED, expand=True)
        table3.add_column("상품", style="white", width=35)
        table3.add_column("주문", justify="right", style="green", width=6)
        table3.add_column("수익", justify="right", style="bold yellow", width=12)

        sorted_products = sorted(by_product.items(), key=lambda x: x[1]["revenue"], reverse=True)
        for product, d in sorted_products[:15]:
            table3.add_row(
                product[:35],
                str(d["orders"]),
                f"{d['revenue']:,.0f}원"
            )
        console.print(table3)


def cmd_gsc_match():
    """GSC 키워드와 쿠팡 수익 매칭 분석"""
    history = load_history()
    records = history.get("records", [])

    if not records:
        console.print("[yellow]쿠팡 데이터 없음. python coupang.py import 먼저[/]")
        return

    # 수익 발생한 서브ID/URL 추출
    revenue_subs = {}
    for r in records:
        sub = r.get("sub_id", "")
        url = r.get("url", "")
        rev = r.get("revenue", 0)
        if rev > 0 and (sub or url):
            key = sub or url
            if key not in revenue_subs:
                revenue_subs[key] = 0
            revenue_subs[key] += rev

    if not revenue_subs:
        console.print("[yellow]수익 발생 데이터 없음[/]")
        return

    console.print(Panel(
        f"수익 발생 채널: {len(revenue_subs)}개\n"
        f"총 수익: {sum(revenue_subs.values()):,.0f}원",
        title="쿠팡 수익 × GSC 매칭"
    ))

    # 스냅샷에서 관련 키워드 찾기
    SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"
    files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])

    if files:
        console.print("\n[cyan]수익 발생 채널의 GSC 키워드:[/]")
        for sub, rev in sorted(revenue_subs.items(), key=lambda x: x[1], reverse=True)[:10]:
            console.print(f"\n  [bold yellow]{sub}[/] — 수익 {rev:,.0f}원")
            console.print(f"  [dim]이 채널로 유입되는 GSC 키워드를 확인하려면 서브ID를 블로그 도메인으로 설정하세요.[/]")


def main():
    if len(sys.argv) < 2:
        console.print("[bold]쿠팡 파트너스 수익 분석[/]\n")
        console.print("  python coupang.py import              coupang_data/ CSV 전체 임포트")
        console.print("  python coupang.py import <파일>       특정 CSV 임포트")
        console.print("  python coupang.py summary             수익 요약")
        console.print("  python coupang.py match               GSC 키워드 매칭")
        console.print(f"\nCSV 파일 위치: {COUPANG_DIR}/")
        console.print("쿠팡 파트너스 > 리포트 > CSV 다운로드 후 위 폴더에 넣으세요.")
        return

    cmd = sys.argv[1]

    if cmd == "import":
        if len(sys.argv) >= 3:
            cmd_import(sys.argv[2])
        else:
            cmd_import_dir()
    elif cmd == "summary":
        cmd_summary()
    elif cmd == "match":
        cmd_gsc_match()
    else:
        console.print(f"[red]알 수 없는 명령: {cmd}[/]")


if __name__ == "__main__":
    main()
