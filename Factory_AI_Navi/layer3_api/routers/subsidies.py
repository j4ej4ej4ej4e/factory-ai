"""
layer3_api/routers/subsidies.py
=================================
GET /api/v1/subsidies — 현재 신청 가능 지원사업 목록
POST /api/v1/roi-simulate — ROI 단독 계산
"""

from fastapi import APIRouter, Query
from layer2_ai.agents.matching import MatchingAgent
from layer2_ai.agents.roi_calculator import ROICalculator
from layer2_ai.constants import INDUSTRY_ROI_PARAMS
from layer3_api.schemas import ROISimulateRequest

router = APIRouter()
_matching = MatchingAgent()
_roi_calc = ROICalculator()


@router.get("/subsidies")
def list_subsidies(
    industry_code: str = Query(..., example="C25"),
    company_size: str = Query(..., example="small"),
    top_n: int = Query(10, ge=1, le=20),
):
    """업종·규모 기준 지원사업 목록 반환"""
    profile = {"industry_code": industry_code, "company_size": company_size}
    subsidies = _matching.match(profile, ai_priorities=None, top_n=top_n)
    return {"items": subsidies, "total": len(subsidies)}


@router.post("/roi-simulate")
def roi_simulate(req: ROISimulateRequest):
    """
    단일 AI 유형 ROI 빠른 계산 (진단 없이 직접 호출용)
    """
    profile = req.model_dump()
    ai_priority = {
        "ai_type":       req.ai_type,
        "ai_name":       req.ai_type,
        "estimated_cost": req.estimated_cost,
    }

    # 더미 보조금 (자부담률만 필요)
    dummy_subsidy = {"co_funding_rate": req.co_funding_rate}

    results = _roi_calc.calculate(
        company_profile=profile,
        peer_data={},
        ai_priorities=[ai_priority],
        subsidies=[dummy_subsidy],
    )
    return {"results": [r.to_dict() for r in results]}
