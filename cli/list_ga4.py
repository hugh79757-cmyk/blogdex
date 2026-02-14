from google.analytics.admin import AnalyticsAdminServiceClient
from google_auth import get_credentials
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

def run():
    creds = get_credentials()
    client = AnalyticsAdminServiceClient(credentials=creds)

    accounts = client.list_account_summaries()

    table = Table(title="GA4 속성 목록", box=box.ROUNDED)
    table.add_column("속성 ID", style="cyan")
    table.add_column("속성 이름", style="white")

    for account in accounts:
        for prop in account.property_summaries:
            table.add_row(prop.property, prop.display_name)

    console.print(table)

if __name__ == "__main__":
    run()

