#!/usr/bin/env python3
"""GA4 속성 감사: 중복 탐지 + 데이터 수신 여부 확인"""

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from google_auth import get_credentials
from google.analytics.admin import AnalyticsAdminServiceClient
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric

GA4_PROPERTIES = {
    "407313218": "techpawz.com",
    "521925869": "biz.techpawz.com",
    "440341812": "funstaurant.techpawz.com",
    "407323015": "rotcha.kr",
    "520232186": "hotissue.rotcha.kr",
    "446560416": "kay.rotcha.kr",
    "407690954": "ji.rotcha.kr",
    "422161800": "hero.rotcha.kr",
    "428914171": "ri.rotcha.kr",
    "430520851": "ro.rotcha.kr",
    "449396830": "no.rotcha.kr",
    "437300791": "5.informationhot.kr",
    "502932448": "65.informationhot.kr",
    "519652505": "informationhot.kr",
    "469316517": "kuta.informationhot.kr",
    "490284742": "ud.informationhot.kr",
    "518365064": "stock.informationhot.kr",
    "518766137": "8.informationhot.kr",
    "510545640": "issuetwinkle-tv.informationhot.kr",
    "520033547": "simprotection.informationhot.kr",
    "520495436": "tv-show.informationhot.kr",
    "489950024": "mimdiomcat.tistory.com",
    "502880375": "2.techpawz.com",
    "520459800": "travel.rotcha.kr",
    "518592752": "zodiac.techpawz.com",
    "515574149": "issue.techpawz.com",
    "502581984": "info.techpawz.com",
    "524828505": "cert.aikorea24.kr",
    "524509961": "aikorea24.kr",
    "407673873": "achaanstree.tistory.com",
    "407723312": "foodwater.tistory.com",
    "529365364": "tour1.rotcha.kr",
    "529354403": "travel1.rotcha.kr",
    "529351202": "travel2.rotcha.kr",
    "529355746": "tour2.rotcha.kr",
    "529368606": "tour3.rotcha.kr",
    "526695780": "sports.rotcha.kr",
    "529135373": "tco.rotcha.kr",
    "529150625": "deal.rotcha.kr",
    "529150626": "compare.rotcha.kr",
    "529158015": "guide.rotcha.kr",
    "529144463": "ev.rotcha.kr",
    "529144464": "dividend.techpawz.com",
    "529144841": "etf.techpawz.com",
    "529088575": "sector.techpawz.com",
    "529152161": "ipo.techpawz.com",
    "529142332": "finance.techpawz.com",
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
    "531077897": "achaanstree.tistory.com",
    "531027450": "compare.rotcha.kr",
    "531086518": "deal.rotcha.kr",
    "531071264": "ev.rotcha.kr",
    "531035058": "foodwater.tistory.com",
    "531022174": "guide.rotcha.kr",
    "531050852": "kbo.rotcha.kr",
    "531035059": "mimdiomcat.tistory.com",
    "531059838": "sports.rotcha.kr",
    "531012250": "tco.rotcha.kr",
    "531007356": "tour.techpawz.com",
    "531057733": "tour1.rotcha.kr",
    "531027528": "tour2.rotcha.kr",
    "531059839": "tour3.rotcha.kr",
    "531050452": "travel1.rotcha.kr",
    "531063285": "travel2.rotcha.kr",
    "531145374": "6.informationhot.kr",
    "531063843": "7.informationhot.kr",
    "531123457": "adventure.techpawz.com",
    "531065834": "bus.techpawz.com",
    "531006370": "cruise.techpawz.com",
    "531065835": "culture.techpawz.com",
    "531054102": "daytrips.techpawz.com",
    "531065294": "deals.techpawz.com",
    "531047182": "dining.techpawz.com",
    "531081619": "dividend.techpawz.com",
    "531050510": "etf.techpawz.com",
    "531024940": "eurail.techpawz.com",
    "531123458": "ferry.techpawz.com",
    "531118185": "finance.techpawz.com",
    "531167909": "foodtour.techpawz.com",
    "531138757": "heritage.aikorea24.kr",
    "531064331": "ipo.techpawz.com",
    "531129334": "keyword.aikorea24.kr",
    "531142752": "keywords.rotcha.kr",
    "531139671": "multiday.techpawz.com",
    "531055811": "nature.techpawz.com",
    "531036743": "phototour.techpawz.com",
    "531161435": "sector.techpawz.com",
    "531012256": "transfers.techpawz.com",
    "531135786": "visafree.techpawz.com",
    "531135787": "walking.techpawz.com",
    "531139672": "watersports.techpawz.com",
    "531050853": "airlines.techpawz.com",
    "531050854": "airports.techpawz.com",
    "531050855": "esim.techpawz.com",
    "531050856": "eurail.techpawz.com",
    "531050857": "ferry.techpawz.com",
    "531050858": "flights.techpawz.com",
    "531050859": "michelin.techpawz.com",
    "531050860": "phototour.techpawz.com",
    "531050861": "tours.techpawz.com",
    "531050862": "trains.techpawz.com",
    "531050863": "visa.techpawz.com",
}


def find_duplicates(props):
    domain_map = defaultdict(list)
    for pid, domain in props.items():
        domain_map[domain].append(pid)
    return {d: ids for d, ids in domain_map.items() if len(ids) > 1}


def check_recent_pv(client, prop_id):
    try:
        end = datetime.now() - timedelta(days=1)
        start = end - timedelta(days=6)
        req = RunReportRequest(
            property=f"properties/{prop_id}",
            date_ranges=[DateRange(
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
            )],
            metrics=[Metric(name="screenPageViews")],
            limit=1,
        )
        resp = client.run_report(request=req)
        return sum(int(r.metric_values[0].value) for r in resp.rows)
    except Exception as e:
        err = str(e)
        if "403" in err or "PERMISSION_DENIED" in err:
            return "NO_ACCESS"
        if "404" in err or "not found" in err.lower():
            return "NOT_FOUND"
        return f"ERR:{err[:60]}"


def check_streams(admin_client, prop_id):
    try:
        streams = list(admin_client.list_data_streams(
            parent=f"properties/{prop_id}"
        ))
        return len(streams), [s.display_name for s in streams]
    except Exception as e:
        return -1, [str(e)[:60]]


def main():
    print("=" * 70)
    print("  GA4 속성 감사 리포트")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    creds = get_credentials()
    admin_client = AnalyticsAdminServiceClient(credentials=creds)
    data_client = BetaAnalyticsDataClient(credentials=creds)

    # ── 1. 중복 탐지 ────────────────────────────────────────────────
    print("\n[1] 중복 등록 속성")
    dups = find_duplicates(GA4_PROPERTIES)
    remove_ids = set()

    if not dups:
        print("    ✅ 중복 없음")
    else:
        print(f"    ⚠️  {len(dups)}개 도메인 중복\n")
        for domain, ids in sorted(dups.items()):
            ids_sorted = sorted(ids)
            keep = ids_sorted[-1]
            removes = ids_sorted[:-1]
            for r in removes:
                remove_ids.add(r)
            print(f"    {domain}")
            print(f"      ✅ 유지: {keep}")
            for r in removes:
                print(f"      🗑  삭제: {r}")

    # ── 2. 데이터 수신 현황 ──────────────────────────────────────────
    print("\n[2] 데이터 수신 현황 (최근 7일, 삭제 대상 제외)")
    print(f"    {'ID':<13} {'도메인':<38} {'7일PV':>7}  상태")
    print("    " + "-" * 68)

    ok_list, no_data_list, no_access_list, error_list = [], [], [], []

    for pid, domain in sorted(GA4_PROPERTIES.items(), key=lambda x: x[1]):
        if pid in remove_ids:
            continue
        pv = check_recent_pv(data_client, pid)

        if isinstance(pv, int):
            if pv > 0:
                status = "✅ 정상"
                ok_list.append((pid, domain, pv))
            else:
                status = "⚠️  0 PV"
                no_data_list.append((pid, domain))
            print(f"    {pid:<13} {domain:<38} {pv:>7}  {status}")
        elif pv == "NO_ACCESS":
            no_access_list.append((pid, domain))
            print(f"    {pid:<13} {domain:<38} {'—':>7}  ❌ 권한없음")
        elif pv == "NOT_FOUND":
            error_list.append((pid, domain, "NOT_FOUND"))
            print(f"    {pid:<13} {domain:<38} {'—':>7}  ❌ 속성없음")
        else:
            error_list.append((pid, domain, pv))
            print(f"    {pid:<13} {domain:<38} {'—':>7}  ❌ {pv}")

    # ── 3. 0 PV 속성 스트림 상세 진단 ───────────────────────────────
    if no_data_list:
        print("\n[3] 0 PV 속성 스트림 진단")
        print(f"    {'ID':<13} {'도메인':<38} 스트림수  스트림명")
        print("    " + "-" * 68)
        for pid, domain in no_data_list:
            cnt, names = check_streams(admin_client, pid)
            if cnt == 0:
                sinfo = "❌ 스트림 없음 ← 핵심 원인"
            elif cnt == -1:
                sinfo = f"❌ 조회실패: {names[0]}"
            else:
                sinfo = f"✅ {cnt}개: {', '.join(names)}"
            print(f"    {pid:<13} {domain:<38} {sinfo}")

    # ── 4. 최종 요약 ─────────────────────────────────────────────────
    valid_total = len(GA4_PROPERTIES) - len(remove_ids)
    print("\n[4] 최종 요약")
    print(f"    전체 속성        : {len(GA4_PROPERTIES)}개")
    print(f"    🗑  삭제 대상    : {len(remove_ids)}개 (중복)")
    print(f"    유효 속성        : {valid_total}개")
    print(f"    ✅ 정상 수신     : {len(ok_list)}개")
    print(f"    ⚠️  데이터 없음  : {len(no_data_list)}개")
    print(f"    ❌ 권한 없음     : {len(no_access_list)}개")
    print(f"    ❌ 기타 오류     : {len(error_list)}개")

    print("\n[5] GA4 콘솔에서 직접 삭제할 속성 ID 목록")
    print("    (Admin > 휴지통으로 이동)")
    for pid in sorted(remove_ids):
        domain = GA4_PROPERTIES[pid]
        print(f"    properties/{pid}  ({domain})")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
