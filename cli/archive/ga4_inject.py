#!/usr/bin/env python3
"""
0 PV Hugo 사이트들에 GA4 측정ID를 hugo.toml/config.toml에 자동 삽입
"""
import re
import shutil
from pathlib import Path
from datetime import datetime

# 도메인 → (측정ID, Hugo 프로젝트 경로)
HUGO_SITES = {
    "6.informationhot.kr":      ("G-1LMJJZMWHY", "/Users/twinssn/Projects/LAP"),
    "7.informationhot.kr":      ("G-EGEJ6RFHMD", "/Users/twinssn/Projects/TAP"),
    "appliance.informationhot.kr": ("G-995DNX1KV8", "/Users/twinssn/Projects/CUAP/appliance-hugo"),
    "baby.informationhot.kr":   ("G-CWNZR6DPP5", "/Users/twinssn/Projects/CUAP/baby-hugo"),
    "compare.rotcha.kr":        ("G-JZT8RM1VK9", "/Users/twinssn/Projects/CAP/compare-hugo"),
    "cruise.techpawz.com":      ("G-65W5YFCGYF", "/Users/twinssn/Projects/ETAP/cruise-hugo"),
    "culture.techpawz.com":     ("G-3TQR78109F", "/Users/twinssn/Projects/ETAP/culture-hugo"),
    "daytrips.techpawz.com":    ("G-YHYXXLJ6KX", "/Users/twinssn/Projects/ETAP/daytrips-hugo"),
    "deal.rotcha.kr":           ("G-T98CY06DDF", "/Users/twinssn/Projects/CAP/deal-hugo"),
    "deals.techpawz.com":       ("G-4BRKY9KE2Z", "/Users/twinssn/Projects/ETAP/deals-hugo"),
    "dining.techpawz.com":      ("G-LGDLCT7EF6", "/Users/twinssn/Projects/ETAP/dining-hugo"),
    "dividend.techpawz.com":    ("G-LCZKTDERF7", "/Users/twinssn/Projects/STAP/dividend-hugo"),
    "etf.techpawz.com":         ("G-VY6QY49KTZ", "/Users/twinssn/Projects/STAP/etf-hugo"),
    "ev.rotcha.kr":             ("G-C1GFXL0PHD", "/Users/twinssn/Projects/CAP/ev-hugo"),
    "ferry.techpawz.com":       ("G-MKJ5PYNCT5", "/Users/twinssn/Projects/ETAP/ferry-hugo"),
    "finance.techpawz.com":     ("G-VJVSEKLVXT", "/Users/twinssn/Projects/STAP/finance-hugo"),
    "fitness.informationhot.kr":("G-H4CX8V0B44", "/Users/twinssn/Projects/CUAP/fitness-hugo"),
    "foodtour.techpawz.com":    ("G-XY1EPFZ32T", "/Users/twinssn/Projects/ETAP/foodtour-hugo"),
    "guide.rotcha.kr":          ("G-LCPV1CWT9M", "/Users/twinssn/Projects/CAP/guide-hugo"),
    "hero.rotcha.kr":           ("G-QXSTFH5LXS", None),  # 경로 불명
    "info.techpawz.com":        ("G-LZZQ4B2RN9", "/Users/twinssn/Projects/info.techpawz-hugo"),
    "ipo.techpawz.com":         ("G-SWJF30GPJ8", "/Users/twinssn/Projects/STAP/ipo-hugo"),
    "keywords.rotcha.kr":       ("G-8CP7RXLDDN", "/Users/twinssn/Projects/keyword-scout"),
    "laptop.informationhot.kr": ("G-CF7VEGRSDS", "/Users/twinssn/Projects/CUAP/laptop-hugo"),
    "multiday.techpawz.com":    ("G-BKLYM5WN6R", "/Users/twinssn/Projects/ETAP/multiday-hugo"),
    "sector.techpawz.com":      ("G-56MZB43JP7", "/Users/twinssn/Projects/STAP/sector-hugo"),
    "senior.informationhot.kr": ("G-SPW68ZGGLW", "/Users/twinssn/Projects/SEAP/senior-hugo"),
    "sports.rotcha.kr":         ("G-SHPBQQW07Q", None),  # Blogger
    "stock.informationhot.kr":  ("G-79ZXPZZ262", "/Users/twinssn/Projects/STAP/stock-hugo"),
    "tco.rotcha.kr":            ("G-0DCV505VPR", "/Users/twinssn/Projects/CAP/tco-hugo"),
    "tour.techpawz.com":        ("G-N4Q99745QT", "/Users/twinssn/Projects/ETAP/tour-hugo"),
    "tour1.rotcha.kr":          ("G-5HTKESXB4S", "/Users/twinssn/Projects/travel1-hugo"),
    "tour2.rotcha.kr":          ("G-RVX44514LP", "/Users/twinssn/Projects/travel2-hugo"),
    "tour3.rotcha.kr":          ("G-N2KJVYNH0P", "/Users/twinssn/Projects/travel3-hugo"),
    "transfers.techpawz.com":   ("G-1BT8DWNXVR", "/Users/twinssn/Projects/ETAP/transfers-hugo"),
    "travel1.rotcha.kr":        ("G-PY2ZLQSDKK", "/Users/twinssn/Projects/travel1-hugo"),
    "travel2.rotcha.kr":        ("G-0RB1EX70H8", "/Users/twinssn/Projects/travel2-hugo"),
    "walking.techpawz.com":     ("G-ZKDVHDKPWL", "/Users/twinssn/Projects/ETAP/walking-hugo"),
    "watersports.techpawz.com": ("G-PK52YHF7Q6", "/Users/twinssn/Projects/ETAP/watersports-hugo"),
}

TISTORY_SITES = {
    "achaanstree.tistory.com": "G-XEM5HQ7BPG",
    "foodwater.tistory.com":   "G-Z8N2Y558MD",
    "mimdiomcat.tistory.com":  "G-4XJ98F8KVV",
}

def find_config(project_path):
    """hugo.toml / config.toml / hugo.yaml 찾기"""
    p = Path(project_path)
    for name in ["hugo.toml", "config.toml", "hugo.yaml", "config.yaml"]:
        f = p / name
        if f.exists():
            return f
    return None

def has_ga_setting(content):
    """이미 googleAnalytics 설정이 있는지 확인"""
    return bool(re.search(r'googleAnalytics\s*=', content, re.IGNORECASE))

def inject_toml(config_file, mid, domain):
    """hugo.toml에 googleAnalytics 삽입"""
    content = config_file.read_text(encoding="utf-8")

    if has_ga_setting(content):
        # 이미 있으면 값만 교체
        new_content = re.sub(
            r'googleAnalytics\s*=\s*"[^"]*"',
            f'googleAnalytics = "{mid}"',
            content
        )
        if new_content == content:
            return "ALREADY_SET"
        config_file.write_text(new_content, encoding="utf-8")
        return "UPDATED"

    # [params] 섹션 안에 삽입
    if "[params]" in content:
        new_content = content.replace(
            "[params]",
            f'[params]\n  googleAnalytics = "{mid}"'
        )
    else:
        # [params] 섹션 자체가 없으면 맨 끝에 추가
        new_content = content.rstrip() + f'\n\n[params]\n  googleAnalytics = "{mid}"\n'

    config_file.write_text(new_content, encoding="utf-8")
    return "INJECTED"

def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 65)
    print(f"  GA4 측정ID 자동 삽입  |  {ts}")
    print("=" * 65)

    results = {"injected": [], "updated": [], "already": [],
               "no_path": [], "no_config": [], "skipped": []}

    print("\n【 Hugo 사이트 처리 】")
    for domain, (mid, proj_path) in sorted(HUGO_SITES.items()):
        if proj_path is None:
            print(f"  ⚠️  {domain:<40} 경로 미설정 → 스킵")
            results["no_path"].append(domain)
            continue

        proj = Path(proj_path)
        if not proj.exists():
            print(f"  ❌  {domain:<40} 폴더 없음: {proj_path}")
            results["no_path"].append(domain)
            continue

        config = find_config(proj_path)
        if not config:
            print(f"  ❌  {domain:<40} config 파일 없음")
            results["no_config"].append(domain)
            continue

        # 백업
        bak = config.parent / f"{config.name}.bak.{datetime.now().strftime('%Y%m%d')}"
        if not bak.exists():
            shutil.copy2(config, bak)

        result = inject_toml(config, mid, domain)

        if result == "INJECTED":
            print(f"  ✅  {domain:<40} {mid}  → 삽입완료 ({config.name})")
            results["injected"].append(domain)
        elif result == "UPDATED":
            print(f"  🔄  {domain:<40} {mid}  → 값 갱신 ({config.name})")
            results["updated"].append(domain)
        elif result == "ALREADY_SET":
            print(f"  ✓   {domain:<40} 이미 설정됨 ({config.name})")
            results["already"].append(domain)

    # Tistory 안내
    print("\n【 Tistory - 수동 삽입 필요 】")
    print("  Tistory 관리 → 꾸미기 → 스킨편집 → HTML → <head> 안에 삽입\n")
    for domain, mid in TISTORY_SITES.items():
        print(f"  ▶ {domain}  ({mid})")
        print(f"    <script async src=\"https://www.googletagmanager.com/gtag/js?id={mid}\"></script>")
        print(f"    <script>")
        print(f"      window.dataLayer = window.dataLayer || [];")
        print(f"      function gtag(){{dataLayer.push(arguments);}}")
        print(f"      gtag('js', new Date());")
        print(f"      gtag('config', '{mid}');")
        print(f"    </script>\n")

    # Blogger 안내
    print("【 Blogger - GA4 공식 연동 방법 】")
    print("  Blogger 대시보드 → 설정 → Google 애널리틱스 → 측정ID 입력\n")
    print(f"  ▶ sports.rotcha.kr  →  G-SHPBQQW07Q")

    # 요약
    print("\n" + "=" * 65)
    print("【 처리 결과 요약 】")
    print(f"  ✅ 새로 삽입   : {len(results['injected'])}개")
    print(f"  🔄 값 갱신     : {len(results['updated'])}개")
    print(f"  ✓  이미 설정  : {len(results['already'])}개")
    print(f"  ❌ 경로 없음   : {len(results['no_path'])}개  {results['no_path']}")
    print(f"  ❌ config 없음 : {len(results['no_config'])}개  {results['no_config']}")
    print("=" * 65)

    if results["no_path"] or results["no_config"]:
        print("\n⚠️  위 사이트들은 경로를 직접 확인 후 수동 삽입 필요")
        print("   hugo.toml [params] 섹션에 아래 추가:")
        for domain in results["no_path"] + results["no_config"]:
            mid = HUGO_SITES.get(domain, (None,))[0] or TISTORY_SITES.get(domain)
            if mid:
                print(f"   # {domain}")
                print(f"   googleAnalytics = \"{mid}\"")

if __name__ == "__main__":
    main()
