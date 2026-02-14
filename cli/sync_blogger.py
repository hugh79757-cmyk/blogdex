import yaml
from googleapiclient.discovery import build
from google_auth import get_credentials
from api import get
from sync_utils import get_existing_posts, save_new_posts
from rich.console import Console

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"


def run():
    creds = get_credentials()
    service = build("blogger", "v3", credentials=creds)

    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    blogs_in_db = get("/blogs")
    blogger_sites = config.get("sites", {}).get("blogger", [])

    for bg in blogger_sites:
        name = bg["name"]
        blog_id = str(bg["blog_id"])

        db_blog_id = None
        for b in blogs_in_db:
            if b["name"] == name:
                db_blog_id = b["id"]
                break

        if not db_blog_id:
            console.print(f"[red]{name} — DB에서 찾을 수 없음[/]")
            continue

        console.print(f"\n[bold cyan]{name}[/] (blog_id: {blog_id}) 수집 중...")

        existing = get_existing_posts(db_blog_id)
        console.print(f"  DB 기존 글: {len(existing)}개")

        page_token = None
        all_posts = []

        while True:
            try:
                req = service.posts().list(
                    blogId=blog_id,
                    maxResults=50,
                    pageToken=page_token,
                    status="LIVE"
                )
                resp = req.execute()
            except Exception as e:
                console.print(f"  [red]오류: {e}[/]")
                break

            items = resp.get("items", [])
            if not items:
                break

            for p in items:
                labels = p.get("labels", [])
                all_posts.append({
                    "blog_id": db_blog_id,
                    "title": p["title"],
                    "url": p["url"],
                    "keywords": ", ".join(labels),
                    "published_at": p["published"][:10]
                })

            console.print(f"  {len(all_posts)}개 수집...")

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        save_new_posts(all_posts, existing, name)


if __name__ == "__main__":
    run()
