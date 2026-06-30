"""
models/benchmark.py
===================
Factory AI Navi — benchmark_summary 테이블 모델

ETL 파이프라인 실행 후, 업종별 동종업계 비교 기준값을 집계한 요약 테이블.
Layer 2 AI 에이전트가 벤치마크 분석 시 직접 조회합니다.

raw 데이터(kiat_industry_stats) 기반 집계 결과이므로
ETL 완료 후 자동 갱신되며, 캐시 역할을 합니다.

작성일: 2026-04-28
버전: v1.0
"""

from sqlalchemy import (
    Column, DateTime, Float, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.sql import func

from layer1_etl.models.base import Base


class BenchmarkSummary(Base):
    """
    업종별 벤치마크 요약 테이블.

    kiat_industry_stats 에서 집계된 업종별 평균/중앙값/백분위 기준값을 저장합니다.
    Layer 2에서 기업 입력값과 비교하는 '빠른 조회용' 캐시 테이블입니다.

    Columns
    -------
    id                  : 자동증가 PK
    industry_code       : KSIC 10차 업종코드
    company_size        : 기업 규모 (small / medium / mid_large)
    reference_year      : 집계 기준연도

    -- 생산성 벤치마크 (업종 평균) --
    p25_production_per_person  : 하위 25% 기준 인당 생산액 (만원)
    p50_production_per_person  : 중앙값 인당 생산액 (만원)
    p75_production_per_person  : 상위 25% 기준 인당 생산액 (만원)

    -- 불량률 벤치마크 --
    p25_defect_rate : 하위 25% 불량률 (%)
    p50_defect_rate : 중앙값 불량률 (%)
    p75_defect_rate : 상위 25% 불량률 (%)

    -- 가동률 벤치마크 --
    p50_operating_rate  : 중앙값 가동률 (%)

    -- AI 도입률 --
    avg_ai_adoption_rate : 업종 평균 AI 도입률 (%)

    -- 인건비 --
    avg_labor_cost_per_person : 인당 연평균 인건비 (만원)

    -- 에너지 --
    avg_energy_cost_ratio : 에너지 비용/매출 비율 (%)

    -- 집계 정보 --
    sample_count    : 집계 기업 수
    aggregated_at   : 집계 실행 일시
    notes           : 특이사항 메모
    created_at / updated_at
    """

    __tablename__ = "benchmark_summary"
    __table_args__ = (
        UniqueConstraint(
            "industry_code", "company_size", "reference_year",
            name="uq_benchmark_industry_size_year"
        ),
        Index("ix_benchmark_industry", "industry_code"),
        {"comment": "업종별 동종업계 벤치마크 집계 요약 (Layer 2 빠른 조회용)"},
    )

    # ── 기본 키 ─────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 분류 키 ──────────────────────────────────
    industry_code  = Column(String(10), nullable=False, comment="KSIC 업종코드")
    company_size   = Column(String(20), nullable=False, comment="기업 규모")
    reference_year = Column(Integer,    nullable=False, comment="집계 기준연도")

    # ── 생산성 백분위 ────────────────────────────
    p25_production_per_person = Column(Float, nullable=True, comment="인당 생산액 하위25% (만원)")
    p50_production_per_person = Column(Float, nullable=True, comment="인당 생산액 중앙값 (만원)")
    p75_production_per_person = Column(Float, nullable=True, comment="인당 생산액 상위25% (만원)")

    # ── 불량률 백분위 ────────────────────────────
    p25_defect_rate = Column(Float, nullable=True, comment="불량률 하위25% (%)")
    p50_defect_rate = Column(Float, nullable=True, comment="불량률 중앙값 (%)")
    p75_defect_rate = Column(Float, nullable=True, comment="불량률 상위25% (%)")

    # ── 가동률 ───────────────────────────────────
    p50_operating_rate = Column(Float, nullable=True, comment="가동률 중앙값 (%)")

    # ── AI·인건비·에너지 ─────────────────────────
    avg_ai_adoption_rate      = Column(Float, nullable=True, comment="평균 AI 도입률 (%)")
    avg_labor_cost_per_person = Column(Float, nullable=True, comment="인당 연평균 인건비 (만원)")
    avg_energy_cost_ratio     = Column(Float, nullable=True, comment="에너지 비용/매출 비율 (%)")

    # ── 집계 정보 ────────────────────────────────
    sample_count  = Column(Integer,  nullable=True, comment="집계 기업 수")
    aggregated_at = Column(DateTime, nullable=True, comment="집계 실행 일시")
    notes         = Column(Text,     nullable=True, comment="특이사항 메모")

    # ── 메타 ─────────────────────────────────────
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def get_percentile(self, metric: str, value: float) -> str:
        """
        입력값이 동종업계 몇 번째 백분위에 해당하는지 간단 판별.

        Parameters
        ----------
        metric : str
            'production' | 'defect_rate' | 'operating_rate'
        value : float
            기업 측정값

        Returns
        -------
        str
            '상위 25%' | '중위 25~75%' | '하위 25%'
        """
        if metric == "production":
            if value >= (self.p75_production_per_person or 0):
                return "상위 25%"
            elif value >= (self.p25_production_per_person or 0):
                return "중위 25~75%"
            else:
                return "하위 25%"
        elif metric == "defect_rate":
            # 불량률은 낮을수록 좋음 (역순)
            if value <= (self.p25_defect_rate or float("inf")):
                return "상위 25% (낮은 불량률)"
            elif value <= (self.p75_defect_rate or float("inf")):
                return "중위 25~75%"
            else:
                return "하위 25% (높은 불량률)"
        return "측정 불가"

    def to_dict(self) -> dict:
        return {
            "industry_code":              self.industry_code,
            "company_size":               self.company_size,
            "reference_year":             self.reference_year,
            "p50_production_per_person":  self.p50_production_per_person,
            "p50_defect_rate":            self.p50_defect_rate,
            "p50_operating_rate":         self.p50_operating_rate,
            "avg_ai_adoption_rate":       self.avg_ai_adoption_rate,
            "avg_labor_cost_per_person":  self.avg_labor_cost_per_person,
            "avg_energy_cost_ratio":      self.avg_energy_cost_ratio,
            "sample_count":               self.sample_count,
            "aggregated_at":              str(self.aggregated_at) if self.aggregated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<BenchmarkSummary "
            f"industry={self.industry_code} "
            f"size={self.company_size} "
            f"year={self.reference_year}>"
        )
