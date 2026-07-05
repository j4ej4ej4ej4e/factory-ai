"""
models/subsidies.py
===================
Factory AI Navi — keit_subsidies 테이블 모델

출처: KEIT 사업공고 + 국가R&D API + 중기부 스마트공장 지원사업
활용: 기업 프로파일 & 진단 결과와 매칭하여 적합 지원사업 Top 5 추천

작성일: 2026-04-28
버전: v1.0
"""

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    Float, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.sql import func

from layer1_etl.models.base import Base


class KeitSubsidy(Base):
    """
    정부지원사업 공고 테이블.

    KEIT 사업공고, 국가R&D API, 중기부 스마트공장 지원사업 등
    여러 기관의 지원사업을 통합 관리합니다.

    매칭 에이전트(SubsidyMatchingAgent)가 이 테이블에서
    코사인 유사도 기반으로 기업에 적합한 사업을 검색합니다.

    Columns
    -------
    id                  : 자동증가 PK
    subsidy_id          : 원본 시스템 공고 ID (출처별 고유 식별자)
    source              : 출처 기관 (KEIT / NTIS / MSS 등)
    program_name        : 사업명
    program_category    : 사업 분류 (스마트공장 / R&D / 뿌리업종 등)

    -- 지원 조건 --
    target_industry_codes : 대상 업종 코드 목록 (콤마 구분)
    target_company_sizes  : 대상 기업 규모 (콤마 구분)
    target_ai_types       : 해당 AI 유형 (콤마 구분)

    -- 지원 금액 --
    max_support_amount    : 최대 지원금액 (만원)
    min_support_amount    : 최소 지원금액 (만원)
    co_funding_rate       : 자부담 비율 (0.0 ~ 1.0)

    -- 일정 --
    application_start   : 신청 시작일
    application_end     : 신청 마감일
    announcement_date   : 공고일

    -- 링크·설명 --
    apply_url           : 신청 링크
    description         : 사업 설명 (RAG 검색용 텍스트)
    requirements        : 신청 자격 요건

    -- 벡터 (pgvector — Layer 2 대비) --
    # embedding        : Vector(1536)  ← pgvector 확장 필요 시 활성화

    -- 메타 --
    is_active           : 현재 신청 가능 여부
    collected_at        : 수집 일시
    created_at          : DB 적재 일시
    updated_at          : 최종 갱신 일시
    """

    __tablename__ = "keit_subsidies"
    __table_args__ = (
        UniqueConstraint("subsidy_id", "source", name="uq_subsidy_source"),
        Index("ix_subsidy_application_end", "application_end"),
        Index("ix_subsidy_is_active", "is_active"),
        Index("ix_subsidy_source", "source"),
        {"comment": "KEIT·국가R&D·중기부 정부지원사업 공고 통합 테이블"},
    )

    # ── 기본 키 ─────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 공고 식별 ────────────────────────────────
    subsidy_id        = Column(String(100), nullable=False, comment="원본 공고 ID")
    source            = Column(String(20),  nullable=False, comment="출처 기관 코드")
    program_name      = Column(String(255), nullable=False, comment="사업명")
    program_category  = Column(String(100), nullable=True,  comment="사업 분류")

    # ── 대상 조건 ────────────────────────────────
    target_industry_codes = Column(Text, nullable=True, comment="대상 업종 코드 (콤마 구분)")
    target_company_sizes  = Column(Text, nullable=True, comment="대상 기업 규모 (콤마 구분)")
    target_ai_types       = Column(Text, nullable=True, comment="연관 AI 유형 (콤마 구분)")

    # ── 지원 금액 ────────────────────────────────
    max_support_amount = Column(BigInteger, nullable=True, comment="최대 지원금액 (만원)")
    min_support_amount = Column(BigInteger, nullable=True, comment="최소 지원금액 (만원)")
    co_funding_rate    = Column(Float,      nullable=True, comment="자부담 비율 (0.0~1.0)")

    # ── 신청 일정 ────────────────────────────────
    application_start = Column(Date, nullable=True, comment="신청 시작일")
    application_end   = Column(Date, nullable=True, comment="신청 마감일")
    announcement_date = Column(Date, nullable=True, comment="공고일")

    # ── 링크·설명 ────────────────────────────────
    apply_url    = Column(Text, nullable=True, comment="신청 링크 URL")
    description  = Column(Text, nullable=True, comment="사업 설명 (RAG 텍스트 검색용)")
    requirements = Column(Text, nullable=True, comment="신청 자격 요건")

    # ── pgvector 임베딩 (Layer 2 RAG 대비) ───────
    # ─────────────────────────────────────────────────────────────
    # pgvector 확장 활성화 후 아래 주석 해제:
    #   from pgvector.sqlalchemy import Vector
    #   embedding = Column(Vector(1536), nullable=True,
    #                      comment="사업 설명 임베딩 벡터 (text-embedding-3-small)")
    # ─────────────────────────────────────────────────────────────

    # ── 메타 ─────────────────────────────────────
    is_active    = Column(Boolean,  default=True,      nullable=False, comment="현재 신청 가능 여부")
    collected_at = Column(DateTime, nullable=True,      comment="수집 일시")
    created_at   = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at   = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def days_until_deadline(self) -> int | None:
        """마감일까지 남은 일수 계산 (마감 지난 경우 음수)"""
        if self.application_end is None:
            return None
        from datetime import date
        return (self.application_end - date.today()).days

    @property
    def is_urgent(self) -> bool:
        """마감 D-7 이내 여부"""
        days = self.days_until_deadline
        return days is not None and 0 <= days <= 7

    def to_dict(self) -> dict:
        return {
            "subsidy_id":          self.subsidy_id,
            "source":              self.source,
            "program_name":        self.program_name,
            "program_category":    self.program_category,
            "target_industry_codes": self.target_industry_codes,
            "target_company_sizes":  self.target_company_sizes,
            "target_ai_types":       self.target_ai_types,
            "max_support_amount":  self.max_support_amount,
            "co_funding_rate":     self.co_funding_rate,
            "application_end":     str(self.application_end) if self.application_end else None,
            "days_until_deadline": self.days_until_deadline,
            "is_urgent":           self.is_urgent,
            "apply_url":           self.apply_url,
            "description":         self.description,
        }

    def __repr__(self) -> str:
        return (
            f"<KeitSubsidy "
            f"name={self.program_name[:30]} "
            f"source={self.source} "
            f"deadline={self.application_end}>"
        )
