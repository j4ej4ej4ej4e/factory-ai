"""
layer3_api/schemas.py
======================
FastAPI Pydantic 요청/응답 스키마
"""

from pydantic import BaseModel, Field
from typing import Optional


class CompanyProfileRequest(BaseModel):
    industry_code: str = Field(..., example="C25")
    company_size: str = Field(..., example="small")
    headcount: int = Field(..., ge=1, example=35)
    annual_revenue: float = Field(..., gt=0, description="연간 매출액 (만원)", example=150000)
    annual_production: float = Field(..., gt=0, description="연간 생산액 (만원)", example=130000)
    defect_rate: Optional[float] = Field(None, ge=0, le=100, description="불량률 (%)", example=5.1)
    operating_rate: Optional[float] = Field(None, ge=0, le=100, description="설비 가동률 (%)", example=60.0)
    energy_cost_ratio: Optional[float] = Field(None, ge=0, le=100, description="에너지 비용 비율 (%)", example=11.0)
    equipment_age: Optional[int] = Field(None, ge=0, description="설비 평균 노후도 (년)", example=8)
    production_per_person: Optional[float] = Field(None, description="인당 생산액 (만원/년)", example=2800)
    pain_points: list[str] = Field(default=[], example=["defect_high", "equipment_breakdown"])


class ROISimulateRequest(BaseModel):
    industry_code: str
    company_size: str
    headcount: int
    annual_revenue: float
    annual_production: float
    operating_rate: Optional[float] = Field(None, ge=0, le=100, description="현재 설비 가동률 (%) — 없으면 KICOX 실측 동종평균 사용")
    ai_type: str = Field(..., example="predictive_maintenance")
    estimated_cost: Optional[float] = Field(None, description="구축비용 (만원)")
    co_funding_rate: Optional[float] = Field(0.5, description="자부담 비율")

    # ── 가상 시나리오 슬라이더 — 없으면 업종 기본값(INDUSTRY_ROI_PARAMS) 사용 ──
    labor_reduction_rate: Optional[float] = Field(None, ge=0, le=1, description="인건비 절감률 (0.0~1.0)")
    energy_reduction_rate: Optional[float] = Field(None, ge=0, le=1, description="에너지 절감률 (0.0~1.0)")
    operating_rate_gain_pp: Optional[float] = Field(None, ge=0, le=50, description="가동률 개선폭 (%p)")


class EligibilityCheckRequest(BaseModel):
    """지원사업 자격 자동 체크리스트 요청 — 공고 원문을 사용자 프로필과 대조"""
    program_name: str = Field(..., description="지원사업명")
    description: str = Field("", description="공고 상세 설명 (신청자격 텍스트 추출 대상)")
    industry_code: str
    company_size: str
    headcount: int = Field(..., ge=1)
