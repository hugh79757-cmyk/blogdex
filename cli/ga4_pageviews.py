"""GA4 API로 URL별 페이지뷰 + 광고수익 수집"""
import json
from datetime import datetime, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
from google_auth import get_credentials
from api import post
from rich.console import Console

console = Console()

PROPERTIES = {
    # --- techpawz.com ---
    "407313218": "techpawz.com",
    "521925869": "biz.techpawz.com",
    "440341812": "funstaurant.techpawz.com",
    "502880375": "2.techpawz.com",
    "515574149": "issue.techpawz.com",
    "502581984": "info.techpawz.com",
    "518592752": "zodiac.techpawz.com",
    "531007356": "tour.techpawz.com",
    "531123457": "adventure.techpawz.com",
    "531065834": "bus.techpawz.com",
    "531006370": "cruise.techpawz.com",
    "531065835": "culture.techpawz.com",
    "531054102": "daytrips.techpawz.com",
    "531065294": "deals.techpawz.com",
    "531047182": "dining.techpawz.com",
    "531081619": "dividend.techpawz.com",
    "531050510": "etf.techpawz.com",
    "531123458": "ferry.techpawz.com",
    "531118185": "finance.techpawz.com",
    "531167909": "foodtour.techpawz.com",
    "531064331": "ipo.techpawz.com",
    "531139671": "multiday.techpawz.com",
    "531055811": "nature.techpawz.com",
    "531161435": "sector.techpawz.com",
    "531012256": "transfers.techpawz.com",
    "531135786": "visafree.techpawz.com",
    "531135787": "walking.techpawz.com",
    "531139672": "watersports.techpawz.com",
    "531035921": "airlines.techpawz.com",
    "531044776": "airports.techpawz.com",
    "531068317": "esim.techpawz.com",
    "531065272": "flights.techpawz.com",
    "531066288": "michelin.techpawz.com",
    "531081222": "tours.techpawz.com",
    "531082945": "trains.techpawz.com",
    "531039430": "visa.techpawz.com",
    "543474092": "eurail.techpawz.com",
    "543510271": "phototour.techpawz.com",

    # --- rotcha.kr ---
    "407323015": "rotcha.kr",
    "520232186": "hotissue.rotcha.kr",
    "446560416": "kay.rotcha.kr",
    "407690954": "ji.rotcha.kr",
    "422161800": "hero.rotcha.kr",
    "428914171": "ri.rotcha.kr",
    "430520851": "ro.rotcha.kr",
    "449396830": "no.rotcha.kr",
    "520459800": "travel.rotcha.kr",
    "531027450": "compare.rotcha.kr",
    "531086518": "deal.rotcha.kr",
    "531071264": "ev.rotcha.kr",
    "531022174": "guide.rotcha.kr",
    "531050852": "kbo.rotcha.kr",
    "531059838": "sports.rotcha.kr",
    "531012250": "tco.rotcha.kr",
    "531057733": "tour1.rotcha.kr",
    "531027528": "tour2.rotcha.kr",
    "531059839": "tour3.rotcha.kr",
    "531050452": "travel1.rotcha.kr",
    "531063285": "travel2.rotcha.kr",

    # --- informationhot.kr ---
    "519652505": "informationhot.kr",
    "437300791": "5.informationhot.kr",
    "502932448": "65.informationhot.kr",
    "469316517": "kuta.informationhot.kr",
    "490284742": "ud.informationhot.kr",
    "518365064": "stock.informationhot.kr",
    "518766137": "8.informationhot.kr",
    "510545640": "issuetwinkle-tv.informationhot.kr",
    "520033547": "simprotection.informationhot.kr",
    "520495436": "tv-show.informationhot.kr",
    "529715626": "apt.informationhot.kr",
    "529752187": "apply.informationhot.kr",
    "529742117": "tax.informationhot.kr",
    "529720369": "rent.informationhot.kr",
    "529762700": "brand.informationhot.kr",
    "531060035": "appliance.informationhot.kr",
    "531030542": "baby.informationhot.kr",
    "531081565": "betguide.informationhot.kr",
    "531028860": "fitness.informationhot.kr",
    "531076492": "fsched.informationhot.kr",
    "531068628": "fstats.informationhot.kr",
    "531082954": "interior.informationhot.kr",
    "531090148": "kboplayer.informationhot.kr",
    "531090946": "kboschedule.informationhot.kr",
    "531013822": "kboteam.informationhot.kr",
    "531055987": "laptop.informationhot.kr",
    "531068343": "proto.informationhot.kr",
    "531013823": "protostats.informationhot.kr",
    "531027923": "senior.informationhot.kr",
    "531145374": "6.informationhot.kr",
    "531063843": "7.informationhot.kr",
    "543441626": "rank.informationhot.kr",
    "543364949": "protoking.informationhot.kr",
    "543475157": "pick.informationhot.kr",
    "543483108": "pet.informationhot.kr",
    "543505819": "kitchen.informationhot.kr",
    "543536240": "health.informationhot.kr",
    "543471477": "camping.informationhot.kr",
    "543478347": "beauty.informationhot.kr",

    # --- aikorea24.kr ---
    "524509961": "aikorea24.kr",
    "524828505": "cert.aikorea24.kr",
    "531138757": "heritage.aikorea24.kr",
    "531129334": "keyword.aikorea24.kr",
    "538315250": "persona.aikorea24.kr",

    # --- tistory ---
    "489950024": "mimdiomcat.tistory.com",
    "407673873": "achaanstree.tistory.com",
    "407723312": "foodwater.tistory.com",

    # --- dead / deprecated (kept for reference) ---
    # "437320334": "biz1.techpawz.com",
}

def run(days=30):
    creds = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days-1)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    all_data = []
    total_pv = 0
    total_rev = 0.0

    for prop_id, domain in PROPERTIES.items():
        console.print(f"  [cyan]{domain}[/] ...", end=" ")
        try:
            request = RunReportRequest(
                property=f"properties/{prop_id}",
                date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
                dimensions=[
                    Dimension(name="pagePath"),
                    Dimension(name="date"),
                ],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions"),
                    Metric(name="totalAdRevenue"),
                ],
                limit=10000,
            )
            response = client.run_report(request=request)
            count = 0
            site_pv = 0
            site_rev = 0.0
            for row in response.rows:
                path = row.dimension_values[0].value
                date = row.dimension_values[1].value
                date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
                pageviews = int(row.metric_values[0].value)
                sessions = int(row.metric_values[1].value)
                revenue = float(row.metric_values[2].value)
                full_url = f"https://{domain}{path}"
                all_data.append({
                    "site": domain,
                    "date": date_fmt,
                    "page": full_url,
                    "pageviews": pageviews,
                    "sessions": sessions,
                    "revenue": round(revenue, 6),
                })
                site_pv += pageviews
                site_rev += revenue
                count += 1
            total_pv += site_pv
            total_rev += site_rev
            console.print(f"{count}건, {site_pv:,} PV, ${site_rev:.2f}")
        except Exception as e:
            console.print(f"[red]에러: {e}[/]")

    console.print(f"\n[bold]전체: {len(all_data)}건, {total_pv:,} PV, ${total_rev:.2f}[/]")

    backup = f"/Users/twinssn/Projects/blogdex/cli/snapshots/ga4_pageviews_{end_str}.json"
    with open(backup, "w") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    console.print(f"저장: {backup}")

    if all_data:
        try:
            batch_size = 500
            for i in range(0, len(all_data), batch_size):
                batch = all_data[i:i+batch_size]
                resp = post("/ga4/pageviews", {"data": batch})
            console.print(f"[bold green]D1 업로드 완료[/]")
        except Exception as e:
            console.print(f"[yellow]D1 업로드 실패: {e}[/]")

    return all_data

if __name__ == "__main__":
    run(days=30)
