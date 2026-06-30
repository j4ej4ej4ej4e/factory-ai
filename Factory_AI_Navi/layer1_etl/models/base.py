"""
models/base.py
==============
Factory AI Navi — SQLAlchemy 선언적 Base 클래스

모든 ORM 모델이 이 Base를 상속합니다.
DB 초기화(테이블 생성)도 이 파일에서 수행합니다.

작성일: 2026-04-28
버전: v1.0
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from layer1_etl.config import DATABASE_URL, USE_MOCK_DATA, logger


class Base(DeclarativeBase):
    """SQLAlchemy 선언적 메타데이터 Base"""
    pass


def get_engine(echo: bool = False):
    """
    SQLAlchemy 엔진 생성.

    Parameters
    ----------
    echo : bool
        True 이면 실행 SQL을 콘솔에 출력 (디버깅용)

    Returns
    -------
    Engine
    """
    if USE_MOCK_DATA:
        # ── Mock 모드: 인메모리 SQLite 사용 (API 키 없어도 전체 파이프라인 테스트 가능)
        logger.info("[DB] Mock 모드 — SQLite in-memory 엔진 사용")
        return create_engine(
            "sqlite:///:memory:",
            echo=echo,
            connect_args={"check_same_thread": False},
        )

    is_sqlite = "sqlite" in DATABASE_URL
    logger.info("[DB] 실제 모드 — %s: %s",
                "SQLite" if is_sqlite else "PostgreSQL", DATABASE_URL[:50] + "...")

    if is_sqlite:
        return create_engine(
            DATABASE_URL,
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
        )
    return create_engine(
        DATABASE_URL,
        echo=echo,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


# 전역 엔진 & 세션 팩토리
engine = get_engine(echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    모든 ORM 모델 테이블을 DB에 생성합니다.
    이미 존재하는 테이블은 건너뜁니다 (checkfirst=True).

    사용:
        from layer1_etl.models.base import init_db
        init_db()
    """
    # 모든 모델을 import 해야 Base.metadata 에 등록됨
    import layer1_etl.models.industry_stats  # noqa: F401
    import layer1_etl.models.subsidies       # noqa: F401
    import layer1_etl.models.benchmark       # noqa: F401

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("[DB] 테이블 초기화 완료: %s", list(Base.metadata.tables.keys()))


def get_db_session():
    """
    FastAPI Dependency Injection 또는 일반 context manager 용 세션 생성기.

    사용:
        with get_db_session() as session:
            session.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
