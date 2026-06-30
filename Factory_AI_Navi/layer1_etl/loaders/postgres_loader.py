"""
loaders/postgres_loader.py
==========================
Factory AI Navi — PostgreSQL (AWS RDS) 적재 모듈

수집·변환이 완료된 DataFrame을 PostgreSQL에 Upsert 방식으로 적재합니다.
중복 실행 시 기존 데이터를 최신값으로 갱신합니다.

지원 테이블
-----------
  - kiat_industry_stats  (KiatIndustryStat ORM)
  - keit_subsidies       (KeitSubsidy ORM)
  - benchmark_summary    (BenchmarkSummary ORM)

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# AWS RDS 연결 설정은 config.py 에서 관리됩니다.
# DATABASE_URL 이 PLACEHOLDER 상태인 경우 SQLite in-memory로 폴백됩니다.
# RDS 엔드포인트 수령 후 .env 에 RDS_* 변수를 설정하세요.
# ──────────────────────────────────────────────────────────────────────────────

from contextlib import contextmanager
from datetime import datetime
from typing import Type

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from layer1_etl.config import DATABASE_URL, logger
from layer1_etl.models.base import Base, SessionLocal, engine, init_db
from layer1_etl.models.industry_stats import KiatIndustryStat
from layer1_etl.models.subsidies import KeitSubsidy
from layer1_etl.models.benchmark import BenchmarkSummary


class PostgresLoader:
    """
    PostgreSQL (AWS RDS) 데이터 적재기.

    사용법
    ------
    loader = PostgresLoader()
    loader.init_tables()                        # 테이블 최초 생성
    loader.load_industry_stats(df)             # kiat_industry_stats 적재
    loader.load_subsidies(df)                  # keit_subsidies 적재
    loader.rebuild_benchmark_summary()        # 집계 요약 테이블 갱신
    """

    def __init__(self):
        self.logger = logger.getChild("PostgresLoader")
        self._is_postgres = "postgresql" in DATABASE_URL
        self._is_sqlite = "sqlite" in DATABASE_URL

    # ──────────────────────────────────────────────
    # 초기화
    # ──────────────────────────────────────────────

    def init_tables(self) -> None:
        """모든 테이블 생성 (없는 경우에만)"""
        init_db()
        self.logger.info("[Loader] DB 테이블 초기화 완료")

    @contextmanager
    def _session(self):
        """DB 세션 context manager"""
        session: Session = SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error("[Loader] DB 오류 — rollback: %s", e)
            raise
        finally:
            session.close()

    # ──────────────────────────────────────────────
    # 산업통계 적재
    # ──────────────────────────────────────────────

    def load_industry_stats(self, df: pd.DataFrame) -> int:
        """
        kiat_industry_stats 테이블에 DataFrame 적재 (upsert).

        고유 키: (industry_code, company_size, reference_year)
        충돌 시: 수치 컬럼 모두 최신값으로 갱신

        Returns
        -------
        int : 적재된 행 수
        """
        if df.empty:
            self.logger.warning("[Loader] load_industry_stats: 빈 DataFrame")
            return 0

        records = df.to_dict(orient="records")
        loaded = 0

        with self._session() as session:
            for record in records:
                record = self._clean_record(record)
                try:
                    self._upsert_industry_stat(session, record)
                    loaded += 1
                except Exception as e:
                    self.logger.error("[Loader] 업종통계 적재 실패: %s | %s", record, e)

        self.logger.info("[Loader] 업종통계 적재 완료: %d건", loaded)
        return loaded

    def _upsert_industry_stat(self, session: Session, record: dict) -> None:
        """단건 upsert — PostgreSQL ON CONFLICT 또는 SQLite merge"""
        existing = session.query(KiatIndustryStat).filter_by(
            industry_code=record.get("industry_code"),
            company_size=record.get("company_size"),
            reference_year=record.get("reference_year"),
        ).first()

        if existing:
            # UPDATE
            for col, val in record.items():
                if hasattr(existing, col) and col not in ("id", "created_at"):
                    setattr(existing, col, val)
            existing.updated_at = datetime.utcnow()
        else:
            # INSERT
            obj = KiatIndustryStat(**{
                k: v for k, v in record.items()
                if hasattr(KiatIndustryStat, k)
            })
            session.add(obj)

    # ──────────────────────────────────────────────
    # 지원사업 적재
    # ──────────────────────────────────────────────

    def load_subsidies(self, df: pd.DataFrame) -> int:
        """
        keit_subsidies 테이블에 DataFrame 적재 (upsert).

        고유 키: (subsidy_id, source)
        충돌 시: 모든 정보 최신값으로 갱신
        """
        if df.empty:
            self.logger.warning("[Loader] load_subsidies: 빈 DataFrame")
            return 0

        records = df.to_dict(orient="records")
        loaded = 0

        # 기존 공고 전체 비활성화 (신규 수집분으로 교체)
        with self._session() as session:
            session.query(KeitSubsidy).filter_by(source=records[0].get("source", "")).update(
                {"is_active": False}
            )

        with self._session() as session:
            for record in records:
                record = self._clean_record(record)
                try:
                    self._upsert_subsidy(session, record)
                    loaded += 1
                except Exception as e:
                    self.logger.error("[Loader] 공고 적재 실패: %s | %s", record, e)

        self.logger.info("[Loader] 공고 적재 완료: %d건", loaded)
        return loaded

    def _upsert_subsidy(self, session: Session, record: dict) -> None:
        """지원사업 단건 upsert"""
        existing = session.query(KeitSubsidy).filter_by(
            subsidy_id=record.get("subsidy_id"),
            source=record.get("source"),
        ).first()

        if existing:
            for col, val in record.items():
                if hasattr(existing, col) and col not in ("id", "created_at"):
                    setattr(existing, col, val)
            existing.updated_at = datetime.utcnow()
            existing.is_active = True   # 다시 활성화
        else:
            obj = KeitSubsidy(**{
                k: v for k, v in record.items()
                if hasattr(KeitSubsidy, k)
            })
            session.add(obj)

    # ──────────────────────────────────────────────
    # 벤치마크 집계
    # ──────────────────────────────────────────────

    def rebuild_benchmark_summary(self) -> int:
        """
        kiat_industry_stats 데이터를 집계하여 benchmark_summary 테이블 갱신.
        ETL 파이프라인 마지막 단계에서 호출됩니다.

        Returns
        -------
        int : 갱신된 행 수
        """
        with self._session() as session:
            stats = session.query(KiatIndustryStat).all()
            # session이 닫히기 전에 dict 변환
            stats_dicts = [s.to_dict() for s in stats]

        if not stats_dicts:
            self.logger.warning("[Loader] rebuild_benchmark: 원본 데이터 없음")
            return 0

        df = pd.DataFrame(stats_dicts)
        summary_rows = []

        for (industry_code, company_size, ref_year), group in df.groupby(
            ["industry_code", "company_size", "reference_year"]
        ):
            row = {
                "industry_code":              industry_code,
                "company_size":               company_size,
                "reference_year":             ref_year,
                "p25_production_per_person":  group["avg_production_per_person"].quantile(0.25) if "avg_production_per_person" in group else None,
                "p50_production_per_person":  group["avg_production_per_person"].quantile(0.50) if "avg_production_per_person" in group else None,
                "p75_production_per_person":  group["avg_production_per_person"].quantile(0.75) if "avg_production_per_person" in group else None,
                "p25_defect_rate":            group["avg_defect_rate"].quantile(0.25) if "avg_defect_rate" in group else None,
                "p50_defect_rate":            group["avg_defect_rate"].quantile(0.50) if "avg_defect_rate" in group else None,
                "p75_defect_rate":            group["avg_defect_rate"].quantile(0.75) if "avg_defect_rate" in group else None,
                "p50_operating_rate":         group["avg_operating_rate"].quantile(0.50) if "avg_operating_rate" in group else None,
                "avg_ai_adoption_rate":       group["ai_adoption_rate"].mean() if "ai_adoption_rate" in group else None,
                "avg_labor_cost_per_person":  group["avg_labor_cost_per_person"].mean() if "avg_labor_cost_per_person" in group else None,
                "avg_energy_cost_ratio":      group["avg_energy_cost_ratio"].mean() if "avg_energy_cost_ratio" in group else None,
                "sample_count":               len(group),
                "aggregated_at":              datetime.utcnow(),
            }
            summary_rows.append(row)

        loaded = 0
        with self._session() as session:
            for row in summary_rows:
                existing = session.query(BenchmarkSummary).filter_by(
                    industry_code=row["industry_code"],
                    company_size=row["company_size"],
                    reference_year=row["reference_year"],
                ).first()
                if existing:
                    for col, val in row.items():
                        if hasattr(existing, col) and col != "id":
                            setattr(existing, col, val)
                else:
                    session.add(BenchmarkSummary(**row))
                loaded += 1

        self.logger.info("[Loader] benchmark_summary 갱신: %d건", loaded)
        return loaded

    # ──────────────────────────────────────────────
    # 유틸리티
    # ──────────────────────────────────────────────

    @staticmethod
    def _clean_record(record: dict) -> dict:
        """NaN → None 변환 (DB null 처리)"""
        import math
        cleaned = {}
        for k, v in record.items():
            if isinstance(v, float) and math.isnan(v):
                cleaned[k] = None
            else:
                cleaned[k] = v
        return cleaned

    def health_check(self) -> bool:
        """DB 연결 상태 확인"""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.logger.info("[Loader] DB 연결 정상")
            return True
        except Exception as e:
            self.logger.error("[Loader] DB 연결 실패: %s", e)
            return False

    def get_stats(self) -> dict:
        """각 테이블 행 수 반환 (모니터링용)"""
        with self._session() as session:
            return {
                "kiat_industry_stats": session.query(KiatIndustryStat).count(),
                "keit_subsidies":      session.query(KeitSubsidy).count(),
                "benchmark_summary":   session.query(BenchmarkSummary).count(),
            }
