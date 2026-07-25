import os
import warnings
from pathlib import Path

API_URL = "https://blogdex-api.hugh79757.workers.dev"

_api_key = os.environ.get("BLOGDEX_API_KEY")
if not _api_key:
    raise RuntimeError(
        "BLOGDEX_API_KEY environment variable is not set. "
        "Set it in cli/.env or export it. "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
API_KEY = _api_key

# ── 프로젝트 루트 (config.py 기준: cli/config.py → project root) ──
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── 경로 설정 (환경변수로 오버라이드 가능) ──
# BLOGDEX_PUBLISH_CONFIG: Hugo/Astro/WordPress/Blogger publish 설정 파일
PUBLISH_CONFIG = os.environ.get(
    "BLOGDEX_PUBLISH_CONFIG",
    str(PROJECT_ROOT / "publish_config.yaml")
)

# BLOGDEX_CSV_DIR: 사이트맵 타이틀 CSV 디렉토리
CSV_DIR = os.environ.get(
    "BLOGDEX_CSV_DIR",
    str(PROJECT_ROOT / "sitemap-title")
)

# ── 경로 유효성 경고 (import 시점에 1회) ──
if not Path(PUBLISH_CONFIG).exists():
    warnings.warn(
        f"PUBLISH_CONFIG not found: {PUBLISH_CONFIG}. "
        f"Set BLOGDEX_PUBLISH_CONFIG env var to the correct path."
    )

if not Path(CSV_DIR).exists():
    warnings.warn(
        f"CSV_DIR not found: {CSV_DIR}. "
        f"Set BLOGDEX_CSV_DIR env var to the correct directory."
    )
