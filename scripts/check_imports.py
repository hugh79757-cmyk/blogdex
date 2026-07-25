#!/usr/bin/env python3
"""
Blogdex Import Checker — 검토 대상 파일들의 import 관계를 분석합니다.

각 파일에 대해 다른 Python 파일들이 import 하고 있는지 검사하여
안전하게 삭제할 수 있는지 판단합니다.

Usage:
    python scripts/check_imports.py                     # 전체 검사
    python scripts/check_imports.py --verbose           # 상세 출력
    python scripts/check_imports.py --json              # JSON 출력 (파이프용)
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CLI_DIR = PROJECT_DIR / "cli"

# ── 검사 대상 파일 (cli/ 기준) ──
CANDIDATES = [
    "gsc_snapshot.py",
    "revenue.py",
    "title.py",
    "keyword_value.py",
    "list_gsc.py",
    "list_ga4.py",
    "verify.py",
    "crawl_naver.py",
    "summary.py",
    "upload_snapshots.py",
]


def find_imports_in_file(filepath: Path) -> list[str]:
    """파일의 모든 import/from ... import 문을 추출하여 모듈명 리스트 반환."""
    imports = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except (FileNotFoundError, IOError):
        return imports

    # import foo, import foo.bar
    for m in re.finditer(r'^\s*import\s+(\S+)', text, re.MULTILINE):
        mod = m.group(1).split(".")[0]  # foo.bar → foo
        imports.append(mod)

    # from foo import bar, from foo.bar import baz
    for m in re.finditer(r'^\s*from\s+(\S+)\s+import', text, re.MULTILINE):
        mod = m.group(1).split(".")[0]
        imports.append(mod)

    return imports


def find_files_importing(module_name: str, exclude_paths: set[Path]) -> list[Path]:
    """특정 모듈(파일)을 import 하는 모든 .py 파일 검색 (venv 제외)."""
    # module_name.py 가 import 되는 패턴:
    # import module_name
    # from module_name import ...
    # from cli import module_name  (module_name이 cli/의 하위)
    results = []

    pattern1 = re.compile(rf'^\s*import\s+{re.escape(module_name)}\b', re.MULTILINE)
    pattern2 = re.compile(rf'^\s*from\s+{re.escape(module_name)}\s+import', re.MULTILINE)
    pattern3 = re.compile(rf'^\s*from\s+cli\.{re.escape(module_name)}\s+import', re.MULTILINE)

    for py_file in sorted(CLI_DIR.rglob("*.py")):
        if py_file in exclude_paths:
            continue
        if py_file.name == module_name + ".py":
            continue  # 자기 자신 제외
        if "venv" in py_file.parts or ".venv" in py_file.parts:
            continue  # 가상환경 라이브러리 제외
        try:
            text = py_file.read_text(encoding="utf-8")
        except (FileNotFoundError, IOError):
            continue

        if pattern1.search(text) or pattern2.search(text) or pattern3.search(text):
            results.append(py_file)

    return results


def check_sys_path_imports(module_name: str) -> list[Path]:
    """sys.path.insert나 os.system 등 간접 참조 검색 (간단히 cli/ 내에서 grep)"""
    results = []
    for py_file in sorted(CLI_DIR.rglob("*.py")):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (FileNotFoundError, IOError):
            continue
        # exec(), subprocess.run([...module_name...]), os.system(...module_name...)
        if module_name in text:
            results.append(py_file)
    return results


def main():
    parser = argparse.ArgumentParser(description="Blogdex import checker")
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    results = {}

    print(f"Blogdex Import Checker")
    print(f"CLI 디렉토리: {CLI_DIR}")
    print(f"검사 대상: {len(CANDIDATES)}개 파일")
    print()

    for filename in CANDIDATES:
        filepath = CLI_DIR / filename
        if not filepath.exists():
            if args.json:
                results[filename] = {"status": "not_found"}
            else:
                print(f"  ⏭️  {filename} (파일 없음)")
            continue

        module_name = filename.replace(".py", "")
        exclude = {filepath}

        # 직접 import 검색
        importers = find_files_importing(module_name, exclude)

        # 간접 참조 검색 (subprocess, exec 등)
        indirect = check_sys_path_imports(module_name)

        all_refs = importers + indirect

        # ── 결과 판정 ──
        if not all_refs:
            status = "SAFE_TO_DELETE"
            detail = "import 하는 곳 없음"
        else:
            status = "IN_USE"
            # 중복 제거
            seen = set()
            unique_refs = []
            for p in all_refs:
                if p not in seen:
                    seen.add(p)
                    unique_refs.append(p)
            detail = [str(p.relative_to(PROJECT_DIR)) for p in unique_refs]

        if args.json:
            results[filename] = {
                "status": status,
                "detail": detail,
                "importers": [str(p.relative_to(PROJECT_DIR)) for p in importers],
                "indirect_refs": [str(p.relative_to(PROJECT_DIR)) for p in indirect],
            }
        else:
            icon = "🟢" if status == "SAFE_TO_DELETE" else "🟡"
            print(f"  {icon} {filename}")
            results[filename] = {"status": status, "detail": detail}
            if args.verbose:
                if isinstance(detail, str):
                    print(f"       {detail}")
                else:
                    for ref in detail:
                        print(f"       └─ 참조: {ref}")

    # ── 요약 ──
    if not args.json:
        print()
        print("=" * 50)
        for filename in CANDIDATES:
            r = results.get(filename, {})
            s = r.get("status", "not_found")
            if s == "SAFE_TO_DELETE":
                print(f"  🟢 rm cli/{filename}")
            elif s == "IN_USE":
                refs = r.get("detail", [])
                print(f"  🟡 보류: cli/{filename} ({len(refs)}개 파일에서 import)")
            elif s == "not_found":
                print(f"  ⏭️  cli/{filename} (파일 없음)")
        print("=" * 50)
        print()
        print("🟢 = 삭제 안전 | 🟡 = 사용 중이므로 보류 후 수동 확인")

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
