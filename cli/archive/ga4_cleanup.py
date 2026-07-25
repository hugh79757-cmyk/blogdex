#!/usr/bin/env python3
"""
GA4 중복 속성을 daily_sync.py 에서 제거하고 백업 생성
"""
import re
import shutil
from pathlib import Path
from datetime import datetime

DAILY_SYNC = Path(__file__).parent / "daily_sync.py"
BACKUP = Path(__file__).parent / f"daily_sync.py.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 삭제할 구버전 Property ID (중복 중 낮은 번호)
REMOVE_IDS = {
    "407673873",  # achaanstree.tistory.com  → 유지: 531077897
    "407723312",  # foodwater.tistory.com    → 유지: 531035058
    "489950024",  # mimdiomcat.tistory.com   → 유지: 531035059
    "526695780",  # sports.rotcha.kr         → 유지: 531059838
    "529088575",  # sector.techpawz.com      → 유지: 531161435
    "529135373",  # tco.rotcha.kr            → 유지: 531012250
    "529142332",  # finance.techpawz.com     → 유지: 531118185
    "529144463",  # ev.rotcha.kr             → 유지: 531071264
    "529144464",  # dividend.techpawz.com    → 유지: 531081619
    "529144841",  # etf.techpawz.com         → 유지: 531050510
    "529150625",  # deal.rotcha.kr           → 유지: 531086518
    "529150626",  # compare.rotcha.kr        → 유지: 531027450
    "529152161",  # ipo.techpawz.com         → 유지: 531064331
    "529158015",  # guide.rotcha.kr          → 유지: 531022174
    "529351202",  # travel2.rotcha.kr        → 유지: 531063285
    "529354403",  # travel1.rotcha.kr        → 유지: 531050452
    "529355746",  # tour2.rotcha.kr          → 유지: 531027528
    "529365364",  # tour1.rotcha.kr          → 유지: 531057733
    "529368606",  # tour3.rotcha.kr          → 유지: 531059839
    "531024940",  # eurail.techpawz.com      → 유지: 531050856
    "531036743",  # phototour.techpawz.com   → 유지: 531050860
    "531050857",  # ferry.techpawz.com       → 유지: 531123458
}

def main():
    print(f"📂 대상 파일: {DAILY_SYNC}")

    # 백업
    shutil.copy2(DAILY_SYNC, BACKUP)
    print(f"💾 백업 완료: {BACKUP.name}")

    content = DAILY_SYNC.read_text(encoding="utf-8")

    removed = []
    kept = []

    # GA4_PROPERTIES 블록 내 각 줄 처리
    lines = content.splitlines(keepends=True)
    new_lines = []
    for line in lines:
        # "숫자": "도메인", 패턴 매칭
        m = re.match(r'\s+"(\d+)":\s+"([^"]+)",?\s*\n?', line)
        if m and m.group(1) in REMOVE_IDS:
            removed.append((m.group(1), m.group(2)))
            print(f"  🗑  제거: {m.group(1)}  {m.group(2)}")
        else:
            new_lines.append(line)

    DAILY_SYNC.write_text("".join(new_lines), encoding="utf-8")

    print(f"\n✅ 완료: {len(removed)}개 제거, {len(REMOVE_IDS) - len(removed)}개 미발견")
    print(f"📝 {DAILY_SYNC.name} 업데이트 완료")

    print("\n" + "=" * 55)
    print("🌐 GA4 콘솔에서 직접 삭제할 속성 (휴지통으로 이동)")
    print("   analytics.google.com → 관리 → 속성 → 휴지통")
    print("=" * 55)
    for pid, domain in sorted(removed, key=lambda x: x[0]):
        print(f"   properties/{pid}  ({domain})")

    print("\n⚠️  0 PV 속성들 원인: 스트림은 있으나 블로그에 GA 태그 미삽입")
    print("   Hugo/Astro config에 측정ID 추가 필요한 사이트들:")
    zero_pv_sites = [
        ("531145374", "6.informationhot.kr"),
        ("531063843", "7.informationhot.kr"),
        ("531077897", "achaanstree.tistory.com"),
        ("531060035", "appliance.informationhot.kr"),
        ("531030542", "baby.informationhot.kr"),
        ("531027450", "compare.rotcha.kr"),
        ("531006370", "cruise.techpawz.com"),
        ("531065835", "culture.techpawz.com"),
        ("531054102", "daytrips.techpawz.com"),
        ("531086518", "deal.rotcha.kr"),
        ("531065294", "deals.techpawz.com"),
        ("531047182", "dining.techpawz.com"),
        ("531081619", "dividend.techpawz.com"),
        ("531050510", "etf.techpawz.com"),
        ("531071264", "ev.rotcha.kr"),
        ("531123458", "ferry.techpawz.com"),
        ("531118185", "finance.techpawz.com"),
        ("531028860", "fitness.informationhot.kr"),
        ("531167909", "foodtour.techpawz.com"),
        ("531035058", "foodwater.tistory.com"),
        ("531022174", "guide.rotcha.kr"),
        ("422161800", "hero.rotcha.kr"),
        ("502581984", "info.techpawz.com"),
        ("531064331", "ipo.techpawz.com"),
        ("531142752", "keywords.rotcha.kr"),
        ("531055987", "laptop.informationhot.kr"),
        ("531035059", "mimdiomcat.tistory.com"),
        ("531139671", "multiday.techpawz.com"),
        ("531161435", "sector.techpawz.com"),
        ("531027923", "senior.informationhot.kr"),
        ("531059838", "sports.rotcha.kr"),
        ("518365064", "stock.informationhot.kr"),
        ("531012250", "tco.rotcha.kr"),
        ("531007356", "tour.techpawz.com"),
        ("531057733", "tour1.rotcha.kr"),
        ("531027528", "tour2.rotcha.kr"),
        ("531059839", "tour3.rotcha.kr"),
        ("531012256", "transfers.techpawz.com"),
        ("531050452", "travel1.rotcha.kr"),
        ("531063285", "travel2.rotcha.kr"),
        ("531135787", "walking.techpawz.com"),
        ("531139672", "watersports.techpawz.com"),
    ]
    for pid, domain in zero_pv_sites:
        print(f"   G-???????  {domain}  (측정ID 확인 필요)")

if __name__ == "__main__":
    main()
