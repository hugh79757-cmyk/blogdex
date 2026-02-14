import yaml
import re
from pathlib import Path
from api import get
from sync_utils import get_existing_posts, save_new_posts, safe_title
from rich.console import Console

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"


def parse_front_matter(filepath):
    text = filepath.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        match = re.match(r"^\+\+\+\s*\n(.*?)\n\+\+\+", text, re.DOTALL)
    if not match:
        return {}

    meta = {}
    current_key = None
    list_values = []

    for line in match.group(1).split("\n"):
        line = line.strip()
        if not line:
            continue

        if ":" in line and not line.startswith("-"):
            if current_key and list_values:
                meta[current_key] = list_values
                list_values = []

            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")

            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
                meta[key] = val
            elif val:
                meta[key] = val
            else:
                current_key = key
        elif line.startswith("- "):
            list_values.append(line[2:].strip().strip('"').strip("'"))

    if current_key and list_values:
        meta[current_key] = list_values

    return meta


def run():
    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    blogs_in_db = get("/blogs")
    hugo_sites = config.get("sites", {}).get("hugo", [])

    total_new = 0
    total_skip = 0

    for h in hugo_sites:
        name = h["name"]
        repo_path = h["path"]
        content_dir = h.get("content_dir", "content/posts")

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

        existing = get_existing_posts(db_blog_id)
        console.print(f"  DB 기존 글: {len(existing)}개")

        all_posts = []
        for md_file in content_path.rglob("*.md"):
            meta = parse_front_matter(md_file)
            title = safe_title(meta.get("title", ""))
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

        new, skip = save_new_posts(all_posts, existing, name)
        total_new += new
        total_skip += skip

    console.print(f"\n[bold]Hugo 전체: 신규 {total_new}개 저장, {total_skip}개 스킵[/]")


if __name__ == "__main__":
    run()
