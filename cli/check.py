import sys
from api import get
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    if len(sys.argv) < 2:
        console.print("[yellow]사용법: python check.py <키워드>[/]")
        return

    keyword = sys.argv[1]
    results = get("/posts/search", params={"q": keyword})

    if not results:
        console.print(f"\n[bold green]'{keyword}' — 쓴 적 없음! 새로운 주제입니다.[/]")
        return

    table = Table(title=f"'{keyword}' 검색 결과 ({len(results)}건)", box=box.ROUNDED, show_lines=True)
    table.add_column("블로그", style="cyan", width=15)
    table.add_column("제목", style="white", width=45)
    table.add_column("키워드", style="green", width=20)
    table.add_column("발행일", style="dim", width=12)

    for r in results:
        table.add_row(
            r["blog_name"][:15],
            r["title"][:45],
            (r["keywords"] or "")[:20],
            r["published_at"] or ""
        )

    console.print(table)
    console.print(f"\n[bold yellow]⚠ '{keyword}' 관련 글이 {len(results)}건 있습니다[/]")

if __name__ == "__main__":
    run()

