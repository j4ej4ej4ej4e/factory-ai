"""
config.py
=========
Factory AI Navi — Layer 1 환경 설정 모듈

실제 API 키 / AWS RDS 정보는 .env 파일에 기입 후 사용.
현재는 주석 처리된 자리표시자(placeholder) 상태로 유지.
→ 문서화된 정보 수령 후 .env 파일에 값 채워 넣으면 즉시 동작.

작성일: 2026-04-28
버전: v1.0
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ──────────────────────────────────────────────
# .env 파일 로드 (프로젝트 루트 기준)
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


# ══════════════════════════════════════════════
# [1] GCP Cloud SQL — PostgreSQL 연결 설정
# ══════════════════════════════════════════════
# .env 파일에 아래 형식으로 기입:
#
#   RDS_HOST=your-cloudsql-public-ip   ← GCP Cloud SQL 퍼블릭 IP
#   RDS_PORT=5432
#   RDS_DB=factory_ai_navi
#   RDS_USER=your_db_user
#   RDS_PASSWORD=your_db_password
#
# GCP Console → SQL → 인스턴스 만들기 → PostgreSQL 15
# 연결 → 네트워킹 → 승인된 네트워크에 개발 PC IP 추가
# ──────────────────────────────────────────────
RDS_HOST:     str = os.getenv("RDS_HOST",     "PLACEHOLDER_RDS_HOST")
RDS_PORT:     int = int(os.getenv("RDS_PORT", "5432"))
RDS_DB:       str = os.getenv("RDS_DB",       "factory_ai_navi")
RDS_USER:     str = os.getenv("RDS_USER",     "PLACEHOLDER_RDS_USER")
RDS_PASSWORD: str = os.getenv("RDS_PASSWORD", "PLACEHOLDER_RDS_PASSWORD")
RDS_SSL_MODE: str = os.getenv("RDS_SSL_MODE", "require")

# DATABASE_URL: .env에 직접 지정한 값 우선, 없으면 RDS 조합으로 생성
_db_url_env: str = os.getenv("DATABASE_URL", "")
DATABASE_URL: str = _db_url_env if _db_url_env else (
    f"postgresql+psycopg2://{RDS_USER}:{RDS_PASSWORD}"
    f"@{RDS_HOST}:{RDS_PORT}/{RDS_DB}"
    f"?sslmode={RDS_SSL_MODE}"
)


# ══════════════════════════════════════════════
# [2] 공공데이터 API 키 설정
# ══════════════════════════════════════════════

# ── 2-1. 공공데이터포털 공통 서비스 키 ──────────
# 발급: https://www.data.go.kr → 마이페이지 → 인증키 발급
# .env: PUBLIC_DATA_SERVICE_KEY=your_service_key
PUBLIC_DATA_SERVICE_KEY: str = os.getenv(
    "PUBLIC_DATA_SERVICE_KEY", "PLACEHOLDER_PUBLIC_DATA_SERVICE_KEY"
)

# ── 2-2. 국가R&D 과제검색 API (NTIS) ────────────
# 발급: https://www.ntis.go.kr → API 신청
# .env: NTIS_API_KEY=your_ntis_key
NTIS_API_KEY: str = os.getenv("NTIS_API_KEY", "PLACEHOLDER_NTIS_API_KEY")
NTIS_BASE_URL: str = "https://apis.data.go.kr/B552735/rdTrnsInfo/getRdTrnsInfo"

# ── 2-3. 한국산업단지공단 (KSNPC) Open API ───────
# 발급: https://www.kicox.or.kr → 데이터 서비스
# .env: KSNPC_API_KEY=your_ksnpc_key
KSNPC_API_KEY: str = os.getenv("KSNPC_API_KEY", "PLACEHOLDER_KSNPC_API_KEY")
KSNPC_BASE_URL: str = "https://www.kicox.or.kr/openApi"   # 확인 후 수정

# ── 2-4. 특허청 Open API ─────────────────────────
# 발급: https://openapi.kipris.or.kr → 회원가입 후 발급
# .env: KIPO_API_KEY=your_kipo_key
KIPO_API_KEY: str = os.getenv("KIPO_API_KEY", "PLACEHOLDER_KIPO_API_KEY")
KIPO_BASE_URL: str = "http://plus.kipris.or.kr/openapi/rest"

# ── 2-5. OpenAI (임베딩 생성 — Layer 2 대비) ─────
# .env: OPENAI_API_KEY=your_openai_key
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "PLACEHOLDER_OPENAI_API_KEY")
EMBEDDING_MODEL: str = "text-embedding-3-small"

# ── 2-6. Anthropic Claude API (Layer 2 핵심) ─────
# .env: ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_API_KEY: str = os.getenv(
    "ANTHROPIC_API_KEY", "PLACEHOLDER_ANTHROPIC_API_KEY"
)
CLAUDE_MODEL: str = "claude-sonnet-4-6"

# ── 2-7. 카카오 비즈니스 메시지 API (Layer 3) ────
# .env: KAKAO_API_KEY=your_kakao_key
KAKAO_API_KEY: str = os.getenv("KAKAO_API_KEY", "PLACEHOLDER_KAKAO_API_KEY")
KAKAO_SENDER_KEY: str = os.getenv(
    "KAKAO_SENDER_KEY", "PLACEHOLDER_KAKAO_SENDER_KEY"
)


# ══════════════════════════════════════════════
# [3] 파일 다운로드 경로 설정 (KIAT·KEIT 등 정적 파일)
# ══════════════════════════════════════════════
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR:  Path = DATA_DIR / "raw"       # 원본 수집 파일 저장
PROC_DIR: Path = DATA_DIR / "processed" # 전처리 완료 파일 저장
LOG_DIR:  Path = BASE_DIR / "logs"

# 디렉토리 자동 생성
for _dir in [RAW_DIR, PROC_DIR, LOG_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════
# [4] HTTP 요청 공통 설정
# ══════════════════════════════════════════════
HTTP_TIMEOUT:     int = 30     # 초
HTTP_RETRY_COUNT: int = 3
HTTP_RETRY_DELAY: int = 5      # 초 (재시도 간격)
HTTP_HEADERS: dict = {
    "User-Agent": "FactoryAINavi/1.0 (datacontest@example.com)",
    "Accept": "application/json, application/xml, */*",
}


# ══════════════════════════════════════════════
# [5] 로깅 설정
# ══════════════════════════════════════════════
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_FILE:   Path = LOG_DIR / "layer1_etl.log"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("factory_ai_navi")


# ══════════════════════════════════════════════
# [6] Airflow 연결 ID (Airflow UI에서 등록)
# ══════════════════════════════════════════════
AIRFLOW_CONN_POSTGRES_ID: str = "factory_ai_navi_postgres"
AIRFLOW_CONN_HTTP_PUBLIC: str = "factory_ai_navi_public_api"


# ══════════════════════════════════════════════
# [7] ETL 동작 모드 플래그
# ══════════════════════════════════════════════
USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
# True  → 실제 API/파일 없이 mock 데이터로 파이프라인 전체 테스트
# False → 실제 API 호출 및 파일 다운로드 수행

# 결측값 처리 전략 (missing_handler.py 에서 사용)
# 'industry_mean' : 동일 업종 평균으로 대체 (기본)
# 'global_mean'   : 전체 평균으로 대체
# 'drop'          : 결측 행 제거
IMPUTATION_STRATEGY: str = os.getenv("IMPUTATION_STRATEGY", "industry_mean")


# ══════════════════════════════════════════════
# [8] pgvector 컬렉션 이름 (Layer 2 대비 사전 정의)
# ══════════════════════════════════════════════
VECTOR_COLLECTION_NAME: str = "manufacturing_cases"
VECTOR_DIMENSION:       int  = 1536   # text-embedding-3-small 출력 차원


def validate_config() -> bool:
    """
    필수 설정값이 placeholder 상태인지 검사하고 경고를 출력합니다.
    USE_MOCK_DATA=True 이면 경고만 출력하고 계속 진행합니다.
    """
    placeholders = [
        ("RDS_HOST",     RDS_HOST),
        ("RDS_USER",     RDS_USER),
        ("RDS_PASSWORD", RDS_PASSWORD),
        ("PUBLIC_DATA_SERVICE_KEY", PUBLIC_DATA_SERVICE_KEY),
        ("NTIS_API_KEY", NTIS_API_KEY),
    ]
    missing = [name for name, val in placeholders if "PLACEHOLDER" in str(val)]

    if missing:
        msg = f"미설정 항목 ({len(missing)}개): {', '.join(missing)}"
        if USE_MOCK_DATA:
            logger.warning("[Config] %s → mock 모드로 대체 실행합니다.", msg)
        else:
            logger.error("[Config] %s → .env 파일을 확인하세요.", msg)
            return False
    else:
        logger.info("[Config] 모든 설정값이 정상 로드되었습니다.")

    return True


if __name__ == "__main__":
    validate_config()
    print(f"DATABASE_URL  : {DATABASE_URL}")
    print(f"USE_MOCK_DATA : {USE_MOCK_DATA}")
    print(f"DATA_DIR      : {DATA_DIR}")
