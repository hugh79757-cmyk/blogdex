from api import get
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    blogs = get("/blogs")
    posts = get("/posts/search?q=")

    blog_counts = {}
    for p in posts:
        name = p["blog_name"]
        if name not in blog_counts:
            blog_counts[name] = {"platform": p["platform"], "count": 0}
        blog_counts[name]["count"] += 1

    table = Table(title="Blogdex 전체 현황", box=box.ROUNDED)
    table.add_column("블로그", style="cyan")
    table.add_column("플랫폼", style="yellow")
    table.add_column("글 수", justify="right", style="bold green")

    total = 0
    for name, info in blog_counts.items():
        table.add_row(name, info["platform"], str(info["count"]))
        total += info["count"]

    console.print(table)
    console.print(f"\n총 [bold]{total}[/]개 글 관리 중")

if __name__ == "__main__":
    run()

