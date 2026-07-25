#!/usr/bin/env python3
"""
Blogdex OAuth 토큰 마이그레이션 — pickle → JSON 형식 변환

Google OAuth 토큰을 안전하지 않은 Python pickle 형식에서
표준 JSON 형식(google.oauth2.credentials.Credentials.to_json())으로 변환합니다.

사용법:
    python cli/migrate_tokens.py

이 스크립트는 pickle 파일을 읽어 JSON으로 변환만 하고
pickle 파일은 삭제하지 않습니다. 완료 후 안내에 따라 직접 삭제하세요.

요구사항:
    google-auth>=2.0, google-auth-oauthlib>=1.0
"""

import json
import pickle
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
CLI_DIR = PROJECT_ROOT / "cli"

# ── 변환 대상 pickle 파일 목록 ──
# (설명, pickle 경로, 대상 json 경로)
PICKLE_FILES = [
    # GA4/GSC/공용 토큰 (google_auth.py의 get_credentials()에서 사용)
    ("GA4/GSC twinssn",        CREDENTIALS_DIR / "token_1_twinssn.pickle",
                                CREDENTIALS_DIR / "token_1_twinssn.json"),
    ("GA4/GSC informationhot", CREDENTIALS_DIR / "token_2_informationhot.pickle",
                                CREDENTIALS_DIR / "token_2_informationhot.json"),
    ("GA4/GSC aikorea24",      CREDENTIALS_DIR / "token_3_aikorea24.pickle",
                                CREDENTIALS_DIR / "token_3_aikorea24.json"),

    # AdSense 전용 토큰 (현재 미사용 — 코드에서 참조 없음)
    ("AdSense twinssn (미사용)", CREDENTIALS_DIR / "adsense_token_1_twinssn.pickle",
                                 CREDENTIALS_DIR / "adsense_token_1_twinssn.json"),
    ("AdSense informationhot (미사용)", CREDENTIALS_DIR / "adsense_token_2_informationhot.pickle",
                                         CREDENTIALS_DIR / "adsense_token_2_informationhot.json"),
    ("AdSense aikorea24 (미사용)", CREDENTIALS_DIR / "adsense_token_3_aikorea24.pickle",
                                    CREDENTIALS_DIR / "adsense_token_3_aikorea24.json"),

    # 레거시 토큰 (cli/ 디렉토리, google_auth.py 예전 위치)
    ("레거시 google_token",     CLI_DIR / "google_token.pickle",
                                CREDENTIALS_DIR / "token_1_twinssn.json"),  # 동일 계정, 중복 방출
]

# 연속된 백업 파일 (migrate 불필요, 삭제 권장 대상에만 표시)
BACKUP_PICKLE_FILES = [
    ("백업", CREDENTIALS_DIR / "token_2_informationhot.pickle.bak"),
    ("백업", CLI_DIR / "google_token.pickle.bak"),
    ("백업", CLI_DIR / "google_token.pickle.bak2"),
    ("백업", CLI_DIR / "google_token.pickle.bak.20260319"),
]


def convert_pickle_to_json(description: str, pickle_path: Path, json_path: Path) -> bool:
    """단일 pickle 파일을 JSON 형식으로 변환"""
    if not pickle_path.exists():
        print(f"  ⏭️  [{description}] 파일 없음: {pickle_path.name}")
        return False

    try:
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)
    except (pickle.UnpicklingError, EOFError, ValueError) as e:
        print(f"  ❌ [{description}] pickle 로드 실패: {e}")
        return False

    # Credentials 객체인지 검증
    if not hasattr(creds, "token") or not hasattr(creds, "refresh_token"):
        print(f"  ⚠️  [{description}] 유효한 OAuth 토큰 아님 (type: {type(creds).__name__})")
        return False

    # JSON 직렬화
    try:
        token_data = json.loads(creds.to_json())
    except Exception as e:
        print(f"  ❌ [{description}] JSON 직렬화 실패: {e}")
        return False

    # 최소 필드 검증
    required_fields = ["token", "refresh_token", "token_uri", "client_id", "client_secret"]
    missing = [f for f in required_fields if f not in token_data]
    if missing:
        print(f"  ⚠️  [{description}] 필드 누락: {missing} (그래도 저장 시도)")

    # JSON 저장
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w") as f:
            f.write(creds.to_json())
        # 권한 설정 (소유자만 읽기)
        json_path.chmod(0o600)
        print(f"  ✅ [{description}] 변환 완료: {json_path.name} "
              f"(expires={token_data.get('expiry', 'unknown')[:10]})")
        return True
    except Exception as e:
        print(f"  ❌ [{description}] JSON 저장 실패: {e}")
        return False


def main():
    print("=" * 60)
    print("  Blogdex OAuth 토큰 마이그레이션")
    print("  pickle → JSON 형식 변환")
    print("=" * 60)
    print()

    # ── 1. 변환 실행 ──
    print("[1/3] pickle 토큰 → JSON 변환")
    print("-" * 40)

    converted = []
    skipped = []
    failed = []

    # 중복 대상 처리 (google_token.pickle → token_1_twinssn.json)
    seen_json_targets = set()

    for desc, pickle_path, json_path in PICKLE_FILES:
        target_key = str(json_path)
        if target_key in seen_json_targets:
            # 중복 대상 (google_token.pickle과 token_1_twinssn.pickle이 같은 JSON으로)
            if pickle_path.exists():
                print(f"  ↪️  [{desc}] {pickle_path.name} → (이미 위에서 처리, 스킵)")
                skipped.append(pickle_path)
                continue
            else:
                continue  # 파일 없으면 그냥 스킵
        seen_json_targets.add(target_key)

        if convert_pickle_to_json(desc, pickle_path, json_path):
            converted.append(pickle_path)
        elif pickle_path.exists():
            failed.append(pickle_path)
        else:
            skipped.append(pickle_path)

    # ── 2. 백업 pickle 파일 확인 ──
    print()
    print("[2/3] 백업/잔여 pickle 파일 확인")
    print("-" * 40)

    orphan_backups = []
    for desc, path in BACKUP_PICKLE_FILES:
        if path.exists():
            orphan_backups.append(path)
            print(f"  📦 [{desc}] {path}")

    if not orphan_backups:
        print("  (백업 파일 없음)")

    # ── 3. 결과 요약 ──
    print()
    print("[3/3] 결과 요약")
    print("=" * 40)
    print(f"  ✅ 변환 성공: {len(converted)}개")
    print(f"  ⏭️  스킵 (파일 없음): {len(skipped)}개")
    print(f"  ❌ 변환 실패: {len(failed)}개")

    # ── 안전하게 삭제 가능한 파일 목록 ──
    safe_to_delete = []
    for p in converted:
        safe_to_delete.append(p)
    for p in orphan_backups:
        safe_to_delete.append(p)

    if safe_to_delete:
        print()
        print("=" * 60)
        print("  🗑️  삭제해도 안전한 .pickle 파일")
        print("=" * 60)
        print()
        print("  JSON 변환이 완료되었습니다. pickle 파일은 더 이상 사용되지 않습니다.")
        print("  아래 파일들을 안전하게 삭제할 수 있습니다:")
        print()
        for p in sorted(set(safe_to_delete)):
            print(f"    rm {p}")
        print()
        print("  또는 일괄 삭제:")
        print(f"    rm -f " + " ".join(str(p) for p in sorted(set(safe_to_delete))))
        print()
        print("  ⚠️  삭제 전에 JSON 파일이 정상 작동하는지 확인하세요:")
        print("       python -c \"from google_auth import get_credentials; c = get_credentials(); print('OK:', c.valid)\"")
        print()

    # ── 미사용 adense_token 파일 안내 ──
    unused_adsense = [
        CREDENTIALS_DIR / "adsense_token_1_twinssn.pickle",
        CREDENTIALS_DIR / "adsense_token_2_informationhot.pickle",
        CREDENTIALS_DIR / "adsense_token_3_aikorea24.pickle",
    ]
    any_unused = any(p.exists() for p in unused_adsense)
    if any_unused:
        print()
        print("=" * 60)
        print("  ℹ️  사용되지 않는 adense_token_*.pickle 파일")
        print("=" * 60)
        print()
        print("  다음 파일들은 현재 코드에서 참조되지 않습니다")
        print("  (adsense.py와 adsense_trend.py는 token_*.pickle을 사용):")
        print()
        for p in unused_adsense:
            if p.exists():
                print(f"    rm {p}")

    # ── 최종 메세지 ──
    print()
    print("=" * 60)
    print("  마이그레이션 완료!")
    print()
    print("  다음 단계:")
    print("  1. 새 JSON 토큰 테스트:")
    print("     python -c \"from google_auth import get_credentials; get_credentials()\"")
    print("  2. pickle 파일 삭제 (위 목록 참조)")
    print("  3. 기술 문서 업데이트: TECHNICAL_DOCUMENTATION.md")
    print("=" * 60)


if __name__ == "__main__":
    main()
