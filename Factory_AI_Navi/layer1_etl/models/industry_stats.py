"""
models/industry_stats.py
========================
Factory AI Navi — kiat_industry_stats 테이블 모델

출처: KIAT 산업기술통계 + 산단공 업종별 생산·수출·가동률
활용: 동종업계 벤치마크 분석 (인당 생산액, 불량률, 가동률, AI 도입률, 에너지 비용)

작성일: 2026-04-28
버전: v1.0
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Column, DateTime, Float, Index,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.sql import func

from layer1_etl.models.base import Base


class KiatIndustryStat(Base):
    """
    업종별 산업기술통계 테이블.

    KIAT 산업기술통계 + 산단공 업종별 데이터를 통합 적재합니다.
    동종업계 벤치마크 분석의 핵심 기준값으로 활용됩니다.

    Columns
    -------
    id                  : 자동증가 PK
    industry_code       : KSIC 10차 업종코드 (예: C25)
    industry_name       : 업종 한글명 (예: 금속가공)
    company_size        : 기업규모 (small / medium / mid_large)
    reference_year      : 통계 기준연도 (예: 2024)

    -- 생산성 지표 --
    avg_production_per_person  : 인당 생산액 (만원/년)
    avg_defect_rate            : 평균 불량률 (%)
    avg_operating_rate         : 평균 설비 가동률 (%)
    avg_energy_cost_per_unit   : 단위당 에너지 비용 (%)
    ai_adoption_rate           : AI 도입률 (%)

    -- 인건비·원가 지표 --
    avg_labor_cost_per_person  : 인당 연평균 인건비 (만원)
    avg_material_cost_ratio    : 재료비 비율 (%)
    avg_operating_cost_ratio   : 운영비 비율 (%)

    -- 에너지 지표 --
    avg_energy_consumption_toe : 연간 에너지 소비량 (TOE)
    avg_energy_cost_ratio      : 에너지 비용 / 매출 비율 (%)

    -- 로봇·자동화 지표 (로봇진흥원) --
    robot_adoption_rate        : 산업용 로봇 도입률 (%)
    avg_robot_roi_months       : 로봇 도입 평균 회수 기간 (개월)

    -- 메타 --
    data_source     : 데이터 출처 (KIAT / KSNPC / KOITA 등)
    raw_file_path   : 원본 파일 경로 (감사 추적용)
    created_at      : 적재 일시
    updated_at      : 최종 갱신 일시
    """

    __tablename__ = "kiat_industry_stats"
    __table_args__ = (
        UniqueConstraint(
            "industry_code", "company_size", "reference_year",
            name="uq_industry_size_year"
        ),
        Index("ix_industry_code", "industry_code"),
        Index("ix_reference_year", "reference_year"),
        {"comment": "KIAT·산단공 업종별 산업기술통계 (동종업계 벤치마크 기준)"},
    )

    # ── 기본 키 ─────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 업종 식별 ────────────────────────────────
    industry_code = Column(String(10),  nullable=False, comment="KSIC 10차 업종코드")
    industry_name = Column(String(50),  nullable=False, comment="업종 한글명")
    company_size  = Column(String(20),  nullable=False, comment="기업규모: small/medium/mid_large")
    reference_year = Column(Integer,    nullable=False, comment="통계 기준연도")

    # ── 생산성 지표 ──────────────────────────────
    avg_production_per_person = Column(Float, nullable=True, comment="인당 생산액 (만원/년)")
    avg_defect_rate           = Column(Float, nullable=True, comment="평균 불량률 (%)")
    avg_operating_rate        = Column(Float, nullable=True, comment="평균 설비 가동률 (%)")
    avg_energy_cost_per_unit  = Column(Float, nullable=True, comment="단위당 에너지 비용 (%)")
    ai_adoption_rate          = Column(Float, nullable=True, comment="AI 도입률 (%)")

    # ── 인건비·원가 지표 ─────────────────────────
    avg_labor_cost_per_person  = Column(Float, nullable=True, comment="인당 연평균 인건비 (만원)")
    avg_material_cost_ratio    = Column(Float, nullable=True, comment="재료비 비율 (%)")
    avg_operating_cost_ratio   = Column(Float, nullable=True, comment="운영비 비율 (%)")

    # ── 에너지 지표 ──────────────────────────────
    avg_energy_consumption_toe = Column(Float, nullable=True, comment="연간 에너지 소비량 (TOE)")
    avg_energy_cost_ratio      = Column(Float, nullable=True, comment="에너지 비용/매출 비율 (%)")

    # ── 로봇·자동화 지표 ─────────────────────────
    robot_adoption_rate    = Column(Float, nullable=True, comment="산업용 로봇 도입률 (%)")
    avg_robot_roi_months   = Column(Float, nullable=True, comment="로봇 도입 평균 회수 기간 (개월)")

    # ── 산단공(KSNPC) 국가산업단지 업종동향 ───────
    ksnpc_production_billion_krw = Column(Float, nullable=True, comment="국가산단 업종별 생산실적 (억원, 월)")
    ksnpc_export_million_usd     = Column(Float, nullable=True, comment="국가산단 업종별 수출실적 (백만달러, 월)")
    ksnpc_reference_month        = Column(String(10), nullable=True, comment="산단공 데이터 기준월 (YYYY-MM)")

    # ── 메타 ─────────────────────────────────────
    data_source   = Column(String(50), nullable=True, comment="데이터 출처")
    raw_file_path = Column(Text,       nullable=True, comment="원본 파일 경로 (감사용)")
    created_at    = Column(DateTime,   server_default=func.now(), nullable=False)
    updated_at    = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def to_dict(self) -> dict:
        """ORM 인스턴스 → dict 변환 (JSON 직렬화용)"""
        return {
            "industry_code":              self.industry_code,
            "industry_name":              self.industry_name,
            "company_size":               self.company_size,
            "reference_year":             self.reference_year,
            "avg_production_per_person":  self.avg_production_per_person,
            "avg_defect_rate":            self.avg_defect_rate,
            "avg_operating_rate":         self.avg_operating_rate,
            "ai_adoption_rate":           self.ai_adoption_rate,
            "avg_labor_cost_per_person":  self.avg_labor_cost_per_person,
            "avg_energy_cost_ratio":      self.avg_energy_cost_ratio,
            "robot_adoption_rate":        self.robot_adoption_rate,
            "avg_robot_roi_months":       self.avg_robot_roi_months,
            "ksnpc_production_billion_krw": self.ksnpc_production_billion_krw,
            "ksnpc_export_million_usd":     self.ksnpc_export_million_usd,
            "ksnpc_reference_month":        self.ksnpc_reference_month,
            "data_source":                self.data_source,
        }

    def __repr__(self) -> str:
        return (
            f"<KiatIndustryStat "
            f"industry={self.industry_code} "
            f"size={self.company_size} "
            f"year={self.reference_year}>"
        )
