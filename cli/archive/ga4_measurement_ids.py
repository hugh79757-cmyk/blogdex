#!/usr/bin/env python3
"""
0 PV 속성들의 실제 GA4 측정ID(G-XXXXXXXX) 조회
→ 블로그에 삽입해야 할 태그 목록 출력
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from google_auth import get_credentials
from google.analytics.admin import AnalyticsAdminServiceClient

# 0 PV 속성 (스트림은 있으나 데이터 없음)
ZERO_PV_PROPS = {
    "531145374": "6.informationhot.kr",
    "531063843": "7.informationhot.kr",
    "531077897": "achaanstree.tistory.com",
    "531060035": "appliance.informationhot.kr",
    "531030542": "baby.informationhot.kr",
    "531027450": "compare.rotcha.kr",
    "531006370": "cruise.techpawz.com",
    "531065835": "culture.techpawz.com",
    "531054102": "daytrips.techpawz.com",
    "531086518": "deal.rotcha.kr",
    "531065294": "deals.techpawz.com",
    "531047182": "dining.techpawz.com",
    "531081619": "dividend.techpawz.com",
    "531050510": "etf.techpawz.com",
    "531071264": "ev.rotcha.kr",
    "531123458": "ferry.techpawz.com",
    "531118185": "finance.techpawz.com",
    "531028860": "fitness.informationhot.kr",
    "531167909": "foodtour.techpawz.com",
    "531035058": "foodwater.tistory.com",
    "531022174": "guide.rotcha.kr",
    "422161800": "hero.rotcha.kr",
    "502581984": "info.techpawz.com",
    "531064331": "ipo.techpawz.com",
    "531142752": "keywords.rotcha.kr",
    "531055987": "laptop.informationhot.kr",
    "531035059": "mimdiomcat.tistory.com",
    "531139671": "multiday.techpawz.com",
    "531161435": "sector.techpawz.com",
    "531027923": "senior.informationhot.kr",
    "531059838": "sports.rotcha.kr",
    "518365064": "stock.informationhot.kr",
    "531012250": "tco.rotcha.kr",
    "531007356": "tour.techpawz.com",
    "531057733": "tour1.rotcha.kr",
    "531027528": "tour2.rotcha.kr",
    "531059839": "tour3.rotcha.kr",
    "531012256": "transfers.techpawz.com",
    "531050452": "travel1.rotcha.kr",
    "531063285": "travel2.rotcha.kr",
    "531135787": "walking.techpawz.com",
    "531139672": "watersports.techpawz.com",
}

def main():
    print("=" * 65)
    print("  GA4 측정ID 조회 리포트")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    creds = get_credentials()
    admin = AnalyticsAdminServiceClient(credentials=creds)

    # 플랫폼별 분류
    tistory   = {}
    hugo_astro = {}
    no_access = {}

    print(f"\n{'도메인':<40} {'Property ID':<13} {'측정ID':<15} 상태")
    print("-" * 80)

    results = {}
    for pid, domain in sorted(ZERO_PV_PROPS.items(), key=lambda x: x[1]):
        try:
            streams = list(admin.list_data_streams(parent=f"properties/{pid}"))
            if streams:
                mid = streams[0].web_stream_data.measurement_id or "—"
                results[domain] = {"pid": pid, "mid": mid, "stream": streams[0].display_name}
                status = "✅ 측정ID 확인"
                print(f"{domain:<40} {pid:<13} {mid:<15} {status}")

                # 플랫폼 분류
                if "tistory.com" in domain:
                    tistory[domain] = mid
                else:
                    hugo_astro[domain] = {"mid": mid, "pid": pid}
            else:
                results[domain] = {"pid": pid, "mid": None}
                print(f"{domain:<40} {pid:<13} {'❌ 스트림없음':<15}")
        except Exception as e:
            err = str(e)
            if "403" in err or "PERMISSION" in err:
                no_access[domain] = pid
                print(f"{domain:<40} {pid:<13} {'—':<15} ❌ 권한없음")
            else:
                print(f"{domain:<40} {pid:<13} {'—':<15} ❌ {err[:30]}")

    # ── Tistory 삽입 가이드 ────────────────────────────────────────
    if tistory:
        print("\n" + "=" * 65)
        print("【 Tistory 블로그 GA 태그 삽입 방법 】")
        print("  관리 → 꾸미기 → 스킨편집 → HTML 편집 → <head> 안에 삽입")
        print("=" * 65)
        for domain, mid in sorted(tistory.items()):
            print(f"\n  ▶ {domain}  (측정ID: {mid})")
            print(f"""  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{mid}');
  </script>""")

    # ── Hugo/Astro 삽입 가이드 ────────────────────────────────────
    if hugo_astro:
        print("\n" + "=" * 65)
        print("【 Hugo/Astro 사이트 config 설정 방법 】")
        print("=" * 65)
        print("\n  hugo.toml / config.toml 에 추가:")
        print("  [params]")
        for domain, info in sorted(hugo_astro.items()):
            mid = info['mid']
            pid = info['pid']
            print(f"    # {domain}")
            print(f"    googleAnalytics = \"{mid}\"")
        print()
        print("  또는 layouts/partials/head.html 에 직접 삽입:")
        for domain, info in sorted(hugo_astro.items()):
            mid = info['mid']
            if mid and mid != "—":
                print(f"\n  ▶ {domain}  →  {mid}")

    # ── 전체 측정ID 요약표 (복사용) ──────────────────────────────
    print("\n" + "=" * 65)
    print("【 전체 측정ID 요약 (daily_sync 확인용) 】")
    print("=" * 65)
    print(f"  {'도메인':<40} {'측정ID'}")
    print("  " + "-" * 55)
    for domain, info in sorted(results.items()):
        mid = info.get('mid', '—') or '—'
        print(f"  {domain:<40} {mid}")

    print("\n" + "=" * 65)
    print(f"  조회 완료: {len(results)}개 / 접근불가: {len(no_access)}개")
    print("=" * 65)

if __name__ == "__main__":
    main()
