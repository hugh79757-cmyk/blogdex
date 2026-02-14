"""Blogdex 데이터 정합성 검증"""
import yaml
import os
from pathlib import Path
from api import get
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"
SNAPSHOT_DIR = "/Users/twinssn/Projects/blogdex/cli/snapshots"


def count_local_md(path, content_dir):
    content_path = Path(path) / content_dir
    if not content_path.exists():
        return -1
    return len(list(content_path.rglob("*.md")))


def run():
    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    blogs_in_db = get("/blogs")
    all_posts = get("/posts/search", params={"q": ""})
    if isinstance(all_posts, dict):
        all_posts = all_posts.get("results", [])

    # 블로그별 DB 포스트 수
    db_counts = {}
    for p in all_posts:
        bid = str(p.get("blog_id"))
        db_counts[bid] = db_counts.get(bid, 0) + 1

    console.print("[bold]1. 블로그 등록 상태[/]\n")

    table = Table(box=box.ROUNDED)
    table.add_column("블로그", style="cyan", width=30)
    table.add_column("플랫폼", style="yellow", width=10)
    table.add_column("DB 글 수", justify="right", style="green", width=10)
    table.add_column("로컬 MD", justify="right", style="white", width=10)
    table.add_column("상태", width=15)

    sites = config.get("sites", {})

    for h in sites.get("hugo", []):
        name = h["name"]
        db_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_id = str(b["id"])
                break
        db_count = db_counts.get(db_id, 0) if db_id else 0
        local_count = count_local_md(h["path"], h.get("content_dir", "content/posts"))
        status = "[green]OK[/]" if db_count > 0 else "[red]비어있음[/]"
        if local_count >= 0 and db_count > 0 and abs(db_count - local_count) > 5:
            status = f"[yellow]차이 {abs(db_count - local_count)}[/]"
        table.add_row(name, "hugo", str(db_count), str(local_count) if local_count >= 0 else "-", status)

    for a in sites.get("astro", []):
        name = a["name"]
        db_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_id = str(b["id"])
                break
        db_count = db_counts.get(db_id, 0) if db_id else 0
        local_count = count_local_md(a["path"], a.get("content_dir", "src/content/blog"))
        status = "[green]OK[/]" if db_count > 0 else "[red]비어있음[/]"
        if local_count >= 0 and db_count > 0 and abs(db_count - local_count) > 5:
            status = f"[yellow]차이 {abs(db_count - local_count)}[/]"
        table.add_row(name, "astro", str(db_count), str(local_count) if local_count >= 0 else "-", status)

    for w in sites.get("wordpress", []):
        name = w["name"]
        db_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_id = str(b["id"])
                break
        db_count = db_counts.get(db_id, 0) if db_id else 0
        table.add_row(name, "wordpress", str(db_count), "API", "[green]OK[/]" if db_count > 0 else "[red]비어있음[/]")

    for bg in sites.get("blogger", []):
        name = bg["name"]
        db_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_id = str(b["id"])
                break
        db_count = db_counts.get(db_id, 0) if db_id else 0
        table.add_row(name, "blogger", str(db_count), "API", "[green]OK[/]" if db_count > 0 else "[red]비어있음[/]")

    console.print(table)
    console.print(f"\nDB 등록 블로그: {len(blogs_in_db)}개 | 총 포스트: {len(all_posts)}개")

    # 스냅샷 상태
    console.print("\n[bold]2. GSC 스냅샷 상태[/]\n")
    if os.path.exists(SNAPSHOT_DIR):
        files = sorted([f for f in os.listdir(SNAPSHOT_DIR) if f.endswith(".json")])
        if files:
            console.print(f"  저장된 스냅샷: {len(files)}개")
            console.print(f"  최초: {files[0]}")
            console.print(f"  최근: {files[-1]}")
        else:
            console.print("  [yellow]스냅샷 없음 — python gsc_snapshot.py 실행 필요[/]")
    else:
        console.print("  [red]snapshots 디렉토리 없음[/]")


if __name__ == "__main__":
    run()
