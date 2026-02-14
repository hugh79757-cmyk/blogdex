import yaml
import requests
from api import get, post
from rich.console import Console

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"

def run():
    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    blogs_in_db = get("/blogs")
    wp_sites = config.get("sites", {}).get("wordpress", [])

    for wp in wp_sites:
        name = wp["name"]
        url = wp["url"].rstrip("/")
        username = wp["username"]
        password = wp["app_password"]

        blog_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                blog_id = b["id"]
                break

        if not blog_id:
            console.print(f"[red]{name} — DB에서 찾을 수 없음[/]")
            continue

        console.print(f"\n[bold cyan]{name}[/] ({url}) 수집 중...")

        page = 1
        total = 0
        all_posts = []

        while True:
            try:
                r = requests.get(
                    f"{url}/wp-json/wp/v2/posts",
                    params={"page": page, "per_page": 100, "status": "publish"},
                    auth=(username, password),
                    timeout=30
                )
            except Exception as e:
                console.print(f"  [red]연결 오류: {e}[/]")
                break

            if r.status_code != 200:
                break

            posts = r.json()
            if not posts:
                break

            for p in posts:
                all_posts.append({
                    "blog_id": blog_id,
                    "title": p["title"]["rendered"],
                    "url": p["link"],
                    "keywords": "",
                    "published_at": p["date"][:10]
                })

            total += len(posts)
            console.print(f"  페이지 {page} — {len(posts)}개")
            page += 1

        if all_posts:
            for i in range(0, len(all_posts), 100):
                batch = all_posts[i:i+100]
                post("/posts", {"posts": batch})

            console.print(f"  [green]완료: {total}개 저장[/]")
        else:
            console.print(f"  [yellow]글 없음[/]")

if __name__ == "__main__":
    run()

