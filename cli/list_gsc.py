from googleapiclient.discovery import build
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    creds = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)

    site_list = service.sites().list().execute()
    sites = site_list.get("siteEntry", [])

    table = Table(title="Search Console 사이트 목록", box=box.ROUNDED)
    table.add_column("사이트 URL", style="cyan")
    table.add_column("권한", style="yellow")

    for site in sites:
        table.add_row(site["siteUrl"], site["permissionLevel"])

    console.print(table)
    console.print(f"\n총 {len(sites)}개 사이트")

if __name__ == "__main__":
    run()

