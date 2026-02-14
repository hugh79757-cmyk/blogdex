import yaml
from api import get, post
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()
PUBLISH_CONFIG = "/Users/twinssn/Projects/blogdex/cli/publish_config.yaml"


def run():
    with open(PUBLISH_CONFIG, "r") as f:
        config = yaml.safe_load(f)

    sites = config.get("sites", {})

    for b in sites.get("blogger", []):
        post("/blogs", {
            "name": b["name"],
            "platform": "blogger",
            "url": "https://www.blogger.com/blog/posts/" + str(b["blog_id"])
        })

    for h in sites.get("hugo", []):
        post("/blogs", {
            "name": h["name"],
            "platform": "hugo",
            "url": h.get("path", "")
        })

    for w in sites.get("wordpress", []):
        post("/blogs", {
            "name": w["name"],
            "platform": "wordpress",
            "url": w["url"]
        })

    for a in sites.get("astro", []):
        post("/blogs", {
            "name": a["name"],
            "platform": "astro",
            "url": a.get("path", "")
        })

    blogs = get("/blogs")
    table = Table(title="등록된 블로그", box=box.ROUNDED)
    table.add_column("ID", style="dim")
    table.add_column("이름", style="cyan")
    table.add_column("플랫폼", style="yellow")
    table.add_column("URL", style="dim")

    for b in blogs:
        table.add_row(str(b["id"]), b["name"], b["platform"], b["url"][:50])

    console.print(table)
    console.print(f"\n총 {len(blogs)}개 블로그 등록 완료")

if __name__ == "__main__":
    run()
