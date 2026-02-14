import sys
import csv
import os
from api import get, post
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()

def cmd_add():
    console.print("[bold cyan]타이틀 입력 (빈 줄 입력시 종료)[/]")
    titles = []
    while True:
        title = Prompt.ask("타이틀", default="")
        if not title:
            break
        source = Prompt.ask("출처(선택)", default="manual")
        titles.append({"title": title, "url": "", "source": source})
    if titles:
        post("/titles", {"titles": titles})
        console.print(f"[bold green]{len(titles)}개 저장 완료[/]")

def cmd_csv(filepath):
    if not os.path.exists(filepath):
        console.print(f"[red]파일 없음: {filepath}[/]")
        return
    titles = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            title = row[1].strip()
            url = row[2].strip() if len(row) >= 3 else ""
            if not title:
                continue
            skip = ["카테고리", "태그 목록", "전체보기"]
            if any(s in title for s in skip):
                continue
            source = os.path.basename(filepath).replace("_titles.csv", "").replace(".csv", "")
            titles.append({"title": title, "url": url, "source": source})
    if titles:
        for i in range(0, len(titles), 500):
            batch = titles[i:i+500]
            post("/titles", {"titles": batch})
        console.print(f"[green]{os.path.basename(filepath)}[/] -> {len(titles)}개 저장")

def cmd_csv_dir(dirpath):
    import glob
    files = glob.glob(os.path.join(dirpath, "*.csv"))
    console.print(f"[cyan]{len(files)}개 CSV 발견[/]")
    total = 0
    for f in sorted(files):
        cmd_csv(f)

def cmd_list(keyword=""):
    params = {"q": keyword} if keyword else {"q": ""}
    results = get("/titles/search", params=params)
    if not results:
        console.print("[yellow]저장된 타이틀 없음[/]")
        return
    table = Table(title=f"수집 타이틀 ({len(results)}건)", box=box.ROUNDED, expand=True)
    table.add_column("ID", style="dim", width=5)
    table.add_column("타이틀", style="white", width=45)
    table.add_column("출처", style="cyan", width=20)
    table.add_column("상태", style="yellow", width=6)
    for r in results[:50]:
        table.add_row(str(r["id"]), r["title"][:45], (r["source"] or "")[:20], r["status"])
    console.print(table)

def main():
    if len(sys.argv) < 2:
        console.print("[bold]사용법:[/]")
        console.print("  python titles.py add          수동 입력")
        console.print("  python titles.py csv <파일>    CSV 임포트")
        console.print("  python titles.py csvdir <폴더> 폴더 전체 임포트")
        console.print("  python titles.py list [키워드] 목록 보기")
        return
    cmd = sys.argv[1]
    if cmd == "add":
        cmd_add()
    elif cmd == "csv" and len(sys.argv) >= 3:
        cmd_csv(sys.argv[2])
    elif cmd == "csvdir" and len(sys.argv) >= 3:
        cmd_csv_dir(sys.argv[2])
    elif cmd == "list":
        keyword = sys.argv[2] if len(sys.argv) >= 3 else ""
        cmd_list(keyword)
    else:
        console.print("[red]알 수 없는 명령[/]")

if __name__ == "__main__":
    main()
