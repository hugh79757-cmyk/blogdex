#!/usr/bin/env python3
"""
GA4 inject 2차 - config/_default/ 구조 Hugo 사이트 처리
"""
import re
import shutil
from pathlib import Path
from datetime import datetime

# 도메인 → (측정ID, 프로젝트경로)
SITES = {
    # CUAP - config/_default/params.toml
    "appliance.informationhot.kr": ("G-995DNX1KV8", "/Users/twinssn/Projects/CUAP/appliance-hugo"),
    "baby.informationhot.kr":      ("G-CWNZR6DPP5", "/Users/twinssn/Projects/CUAP/baby-hugo"),
    "fitness.informationhot.kr":   ("G-H4CX8V0B44", "/Users/twinssn/Projects/CUAP/fitness-hugo"),
    "laptop.informationhot.kr":    ("G-CF7VEGRSDS", "/Users/twinssn/Projects/CUAP/laptop-hugo"),

    # ETAP - config/_default/params.toml
    "cruise.techpawz.com":         ("G-65W5YFCGYF", "/Users/twinssn/Projects/ETAP/cruise-hugo"),
    "culture.techpawz.com":        ("G-3TQR78109F", "/Users/twinssn/Projects/ETAP/culture-hugo"),
    "daytrips.techpawz.com":       ("G-YHYXXLJ6KX", "/Users/twinssn/Projects/ETAP/daytrips-hugo"),
    "deals.techpawz.com":          ("G-4BRKY9KE2Z", "/Users/twinssn/Projects/ETAP/deals-hugo"),
    "dining.techpawz.com":         ("G-LGDLCT7EF6", "/Users/twinssn/Projects/ETAP/dining-hugo"),
    "ferry.techpawz.com":          ("G-MKJ5PYNCT5", "/Users/twinssn/Projects/ETAP/ferry-hugo"),
    "foodtour.techpawz.com":       ("G-XY1EPFZ32T", "/Users/twinssn/Projects/ETAP/foodtour-hugo"),
    "multiday.techpawz.com":       ("G-BKLYM5WN6R", "/Users/twinssn/Projects/ETAP/multiday-hugo"),
    "tour.techpawz.com":           ("G-N4Q99745QT", "/Users/twinssn/Projects/ETAP/tour-hugo"),
    "transfers.techpawz.com":      ("G-1BT8DWNXVR", "/Users/twinssn/Projects/ETAP/transfers-hugo"),
    "walking.techpawz.com":        ("G-ZKDVHDKPWL", "/Users/twinssn/Projects/ETAP/walking-hugo"),
    "watersports.techpawz.com":    ("G-PK52YHF7Q6", "/Users/twinssn/Projects/ETAP/watersports-hugo"),

    # STAP - config/_default/
    "stock.informationhot.kr":     ("G-79ZXPZZ262", "/Users/twinssn/Projects/STAP/stock-hugo"),

    # TAP - config/_default/
    "tour1.rotcha.kr":             ("G-5HTKESXB4S", "/Users/twinssn/Projects/TAP/travel1-hugo"),
    "tour2.rotcha.kr":             ("G-RVX44514LP", "/Users/twinssn/Projects/TAP/travel2-hugo"),
    "tour3.rotcha.kr":             ("G-N2KJVYNH0P", "/Users/twinssn/Projects/TAP/travel3-hugo"),
    "travel1.rotcha.kr":           ("G-PY2ZLQSDKK", "/Users/twinssn/Projects/TAP/travel1-hugo"),
    "travel2.rotcha.kr":           ("G-0RB1EX70H8", "/Users/twinssn/Projects/TAP/travel2-hugo"),
}

# LAP, TAP(6,7.informationhot), keyword-scout 는 Hugo가 아님 → 별도 안내
SKIP_SITES = {
    "6.informationhot.kr":   ("G-1LMJJZMWHY", "LAP - Python 앱, Hugo 아님"),
    "7.informationhot.kr":   ("G-EGEJ6RFHMD", "TAP - Python 앱, Hugo 아님"),
    "keywords.rotcha.kr":    ("G-8CP7RXLDDN", "keyword-scout - Python 앱, Hugo 아님"),
}


def find_params(proj_path):
    """config/_default/params.toml 또는 params.yaml 찾기"""
    p = Path(proj_path)
    candidates = [
        p / "config" / "_default" / "params.toml",
        p / "config" / "_default" / "params.yaml",
        p / "config" / "_default" / "hugo.toml",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def has_ga(content):
    return bool(re.search(r'googleAnalytics\s*=', content, re.IGNORECASE))


def inject_params_toml(params_file, mid):
    content = params_file.read_text(encoding="utf-8")

    if has_ga(content):
        new = re.sub(
            r'googleAnalytics\s*=\s*"[^"]*"',
            f'googleAnalytics = "{mid}"',
            content
        )
        if new == content:
            return "ALREADY_SET"
        params_file.write_text(new, encoding="utf-8")
        return "UPDATED"

    # params.toml 맨 위에 추가 (또는 맨 끝)
    new = f'googleAnalytics = "{mid}"\n' + content
    params_file.write_text(new, encoding="utf-8")
    return "INJECTED"


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 65)
    print(f"  GA4 inject 2차  |  {ts}")
    print("=" * 65)

    results = {"injected": [], "updated": [], "already": [],
               "no_path": [], "no_config": []}

    print("\n【 Hugo (config/_default/) 사이트 처리 】")
    for domain, (mid, proj_path) in sorted(SITES.items()):
        proj = Path(proj_path)
        if not proj.exists():
            print(f"  ❌  {domain:<40} 폴더 없음: {proj_path}")
            results["no_path"].append((domain, mid, proj_path))
            continue

        params = find_params(proj_path)
        if not params:
            print(f"  ❌  {domain:<40} params.toml 없음")
            results["no_config"].append((domain, mid, proj_path))
            continue

        # 백업
        bak = params.parent / f"{params.name}.bak_ga4_{datetime.now().strftime('%Y%m%d')}"
        if not bak.exists():
            shutil.copy2(params, bak)

        result = inject_params_toml(params, mid)

        if result == "INJECTED":
            print(f"  ✅  {domain:<40} {mid}  ({params.name})")
            results["injected"].append(domain)
        elif result == "UPDATED":
            print(f"  🔄  {domain:<40} {mid}  갱신")
            results["updated"].append(domain)
        elif result == "ALREADY_SET":
            print(f"  ✓   {domain:<40} 이미 설정됨")
            results["already"].append(domain)

    # Hugo 아닌 사이트 안내
    print("\n【 Hugo 아님 - 수동 처리 필요 】")
    print("  아래 사이트는 Python 앱이므로 HTML 템플릿에 직접 삽입 필요\n")
    for domain, (mid, reason) in SKIP_SITES.items():
        print(f"  ▶ {domain}  →  {mid}")
        print(f"    ({reason})")
        print(f"    → templates/index.html 또는 base.html <head>에 삽입:\n")
        print(f"    <script async src=\"https://www.googletagmanager.com/gtag/js?id={mid}\"></script>")
        print(f"    <script>")
        print(f"      window.dataLayer = window.dataLayer || [];")
        print(f"      function gtag(){{dataLayer.push(arguments);}}")
        print(f"      gtag('js', new Date());")
        print(f"      gtag('config', '{mid}');")
        print(f"    </script>\n")

    # 요약
    print("=" * 65)
    print("【 처리 결과 요약 】")
    print(f"  ✅ 새로 삽입   : {len(results['injected'])}개  {results['injected']}")
    print(f"  🔄 값 갱신     : {len(results['updated'])}개")
    print(f"  ✓  이미 설정  : {len(results['already'])}개")
    print(f"  ❌ 경로 없음   : {len(results['no_path'])}개")
    print(f"  ❌ config 없음 : {len(results['no_config'])}개")

    if results["no_path"] or results["no_config"]:
        print("\n⚠️  미처리 항목:")
        for domain, mid, path in results["no_path"] + results["no_config"]:
            print(f"    {domain}  {mid}  →  {path}")

    print("=" * 65)
    print("\n✅ 완료! Hugo 빌드 후 배포하면 GA4 데이터 수집 시작됩니다.")
    print("   hugo --minify && 배포 명령어 실행 필요")


if __name__ == "__main__":
    main()
