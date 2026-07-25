# WARNING: token_*.json files contain OAuth refresh tokens.
# Never commit these to version control.
# Rotate immediately if exposed.

"""
Blogdex Google OAuth 2.0 인증 모듈

JSON 형식의 OAuth 토큰 관리 (pickle → JSON 마이그레이션 완료)

사용법:
    from google_auth import get_credentials
    creds = get_credentials()              # account=1 (기본, twinssn)
    creds = get_credentials(account=2)     # account=2 (informationhot)

    from google_auth import get_adsense_credentials
    creds = get_adsense_credentials(1)     # AdSense account 1
"""

import json
import os
import fcntl
import tempfile
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ── 프로젝트 루트 (이 파일 기준: cli/ 아래에 위치) ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CREDENTIALS_DIR = _PROJECT_ROOT / "credentials"
_CLI_DIR = _PROJECT_ROOT / "cli"

# ── 계정 메타데이터 ──
# account=1이 기본값 — get_credentials() 호출 시 twinssn 계정 사용
_ACCOUNTS = {
    1: {"name": "twinssn", "suffix": "1_twinssn"},
    2: {"name": "informationhot", "suffix": "2_informationhot"},
    3: {"name": "aikorea24", "suffix": "3_aikorea24"},
}

# ── 기본 OAuth 클라이언트 시크릿 (GA4/GSC/Blogger/Indexing/SiteVerification) ──
_PRIMARY_CLIENT_SECRET = _CLI_DIR / "client_secret_hugh7973.json"

# ── AdSense 전용 클라이언트 시크릿 (계정별) ──
_ADSENSE_CLIENT_SECRETS = {
    1: _CREDENTIALS_DIR / "ADSENSE_CREDENTIALS_1twinssn.json",
    2: _CREDENTIALS_DIR / "ADSENSE_CREDENTIALS_2informationhot.json",
    3: _CREDENTIALS_DIR / "ADSENSE_CREDENTIALS_3aikorea24.json",
}

# ── API Scope 목록 ──
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/analytics.edit",
    "https://www.googleapis.com/auth/webmasters",
    "https://www.googleapis.com/auth/blogger.readonly",
    "https://www.googleapis.com/auth/indexing",
    "https://www.googleapis.com/auth/siteverification",
    "https://www.googleapis.com/auth/adsense.readonly",
]

# ── AdSense 전용 Scope (범용 scopes와 별도로 정의) ──
_ADSENSE_SCOPES = [
    "https://www.googleapis.com/auth/adsense.readonly",
]


def _token_path(account: int) -> Path:
    """계정 번호에 대응하는 JSON 토큰 파일 경로 반환"""
    info = _ACCOUNTS.get(account)
    if not info:
        raise ValueError(f"Unknown account {account}. Valid: {list(_ACCOUNTS.keys())}")
    return _CREDENTIALS_DIR / f"token_{info['suffix']}.json"


def _acquire_lock(token_path: Path, exclusive: bool = False):
    """
    토큰 파일에 대한 파일 잠금 획득.
    exclusive=True: 쓰기 잠금 (LOCK_EX) — 토큰 갱신 시 사용
    exclusive=False: 읽기 잠금 (LOCK_SH) — 검증만 할 때 사용
    반환값: 잠금 파일 디스크립터 (호출자가 close/unlock 책임)
    """
    lock_path = token_path.with_suffix(".json.lock")
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    fcntl.flock(fd, lock_type)
    return fd


def _release_lock(fd):
    """파일 잠금 해제"""
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)


def _load_credentials(token_path: Path):
    """JSON 파일에서 Credentials 객체 로드"""
    if not token_path.exists():
        return None
    try:
        return Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"[WARNING] Corrupted token file {token_path}: {e}. Will re-authorize.")
        return None


def _save_credentials(creds, token_path: Path):
    """Credentials 객체를 JSON 파일로 저장 (원자적 쓰기 + 파일 잠금)"""
    _CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    fd = _acquire_lock(token_path, exclusive=True)
    try:
        # 임시 파일에 먼저 쓰고 rename으로 원자적 교체
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(_CREDENTIALS_DIR),
            prefix=".tmp_token_",
            suffix=".json",
            delete=False,
        )
        try:
            tmp.write(creds.to_json())
            tmp.close()
            os.replace(tmp.name, str(token_path))
        except Exception:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)
            raise

        # 권한 설정 (소유자만 읽기)
        os.chmod(str(token_path), 0o600)
    finally:
        _release_lock(fd)


def get_credentials(account: int = 1):
    """
    Google API (GA4/GSC/Blogger 등)용 OAuth Credentials 반환.

    Args:
        account: 계정 번호 (1=twinssn, 2=informationhot, 3=aikorea24)

    Returns:
        google.oauth2.credentials.Credentials

    최초 실행 시 로컬 브라우저에서 OAuth 인증을 진행합니다.
    이후 토큰은 credentials/token_{suffix}.json 에 JSON 형식으로 저장됩니다.
    """
    token_path = _token_path(account)
    creds = _load_credentials(token_path)

    if creds and creds.valid:
        return creds

    # 읽기 잠금 해제 후 쓰기 잠금으로 갱신
    if creds and creds.expired and creds.refresh_token:
        # 갱신 시도 (잠금 없이 — 토큰 자체 갱신은 Google API 호출)
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[WARNING] Token refresh failed: {e}. Re-authorizing...")
            creds = None

    if not creds or not creds.valid:
        # 새 인증 필요
        if not _PRIMARY_CLIENT_SECRET.exists():
            raise FileNotFoundError(
                f"Client secret file not found: {_PRIMARY_CLIENT_SECRET}\n"
                "Download from Google Cloud Console > APIs & Services > Credentials."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(_PRIMARY_CLIENT_SECRET), SCOPES
        )
        creds = flow.run_local_server(port=9090)

    # 쓰기 잠금 하에 저장
    _save_credentials(creds, token_path)

    return creds


def get_adsense_credentials(account: int = 1):
    """
    Google AdSense API용 OAuth Credentials 반환.
    AdSense는 계정별 별도 OAuth 클라이언트 시크릿 사용.

    Args:
        account: 계정 번호 (1=twinssn, 2=informationhot, 3=aikorea24)

    Returns:
        google.oauth2.credentials.Credentials
    """
    token_path = _token_path(account)
    client_secret = _ADSENSE_CLIENT_SECRETS.get(account)

    if not client_secret:
        raise ValueError(
            f"No AdSense client secret configured for account {account}. "
            f"Valid: {list(_ADSENSE_CLIENT_SECRETS.keys())}"
        )

    creds = _load_credentials(token_path)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[WARNING] AdSense token refresh failed: {e}. Re-authorizing...")
            creds = None

    if not creds or not creds.valid:
        if not client_secret.exists():
            raise FileNotFoundError(
                f"AdSense client secret not found: {client_secret}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret), _ADSENSE_SCOPES
        )
        creds = flow.run_local_server(port=9090)

    _save_credentials(creds, token_path)

    return creds


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--adsense":
        acct = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        creds = get_adsense_credentials(acct)
        acct_name = _ACCOUNTS[acct]["name"]
        print(f"AdSense 인증 성공! (account={acct}, {acct_name})")
        print(f"토큰 저장됨: {_token_path(acct)}")
    else:
        acct = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        creds = get_credentials(acct)
        acct_name = _ACCOUNTS.get(acct, {}).get("name", "twinssn")
        print(f"Google API 인증 성공! (account={acct}, {acct_name})")
        print(f"토큰 저장됨: {_token_path(acct)}")
