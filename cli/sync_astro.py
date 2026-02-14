import yaml
from pathlib import Path
from api import get, post
from sync_hugo import parse_front_matter
from rich.console import Console

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"

def run():
    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    blogs_in_db = get("/blogs")
    astro_sites = config.get("sites", {}).get("astro", [])

    for a in astro_sites:
        name = a["name"]
        repo_path = a["path"]
        content_dir = a.get("content_dir", "src/content")

        db_blog_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_blog_id = b["id"]
                break

        if not db_blog_id:
            console.print(f"[red]{name} — DB에서 찾을 수 없음[/]")
            continue

        content_path = Path(repo_path) / content_dir
        if not content_path.exists():
            console.print(f"[red]{name} — 경로 없음: {content_path}[/]")
            continue

        console.print(f"\n[bold cyan]{name}[/] ({content_path}) 수집 중...")

        all_posts = []
        for md_file in content_path.rglob("*.md"):
            meta = parse_front_matter(md_file)
            title = meta.get("title", "")
            if not title:
                continue

            tags = meta.get("tags", [])
            categories = meta.get("categories", [])
            if isinstance(tags, str):
                tags = [tags]
            if isinstance(categories, str):
                categories = [categories]
            keywords = ", ".join(tags + categories)
            date = str(meta.get("date", ""))[:10]

            all_posts.append({
                "blog_id": db_blog_id,
                "title": title,
                "url": "",
                "keywords": keywords,
                "published_at": date
            })

        if all_posts:
            for i in range(0, len(all_posts), 100):
                batch = all_posts[i:i+100]
                post("/posts", {"posts": batch})
            console.print(f"  [green]완료: {len(all_posts)}개 저장[/]")
        else:
            console.print(f"  [yellow]글 없음[/]")

if __name__ == "__main__":
    run()

