"""
models/diagnosis_history.py
============================
Factory AI Navi — diagnosis_history 테이블 모델

매 진단 요청마다 (업종, 규모, 가동률)을 익명으로 누적 저장한다.
"동종업계 순위표" 기능의 기반 데이터 — 사용자가 늘수록 순위 정확도가
올라가는 성장형 지표. 실측/추정 구분과 무관하게 "사용자가 실제로 입력한
본인 값"만 쌓으므로 조작된 통계가 아니다.

작성일: 2026-07-06
버전: v1.0
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.sql import func

from layer1_etl.models.base import Base


class DiagnosisHistory(Base):
    """
    진단 요청 이력 (익명 — 사업체 식별 정보 없음).

    Columns
    -------
    id             : 자동증가 PK
    industry_code  : KSIC 업종코드
    company_size   : 기업규모 (small/medium)
    operating_rate : 사용자가 입력한 본인 가동률 (%)
    created_at     : 기록 일시
    """

    __tablename__ = "diagnosis_history"
    __table_args__ = (
        Index("ix_diag_hist_industry_size", "industry_code", "company_size"),
        {"comment": "진단 요청 이력 (동종업계 순위표 기반 데이터, 익명)"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    industry_code  = Column(String(10), nullable=False, comment="KSIC 업종코드")
    company_size   = Column(String(20), nullable=False, comment="기업규모: small/medium")
    operating_rate = Column(Float,      nullable=False, comment="사용자 입력 가동률 (%)")
    created_at     = Column(DateTime,   server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DiagnosisHistory industry={self.industry_code} "
            f"size={self.company_size} rate={self.operating_rate}>"
        )
