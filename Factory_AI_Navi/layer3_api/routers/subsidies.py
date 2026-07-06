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
from layer2_ai.tools.benchmark_tool import BenchmarkTool
from layer3_api.schemas import ROISimulateRequest

router = APIRouter()
_matching = MatchingAgent()
_roi_calc = ROICalculator()
_benchmark = BenchmarkTool()


@router.get("/subsidies")
def list_subsidies(
    industry_code: str = Query(..., example="C25"),
    company_size: str = Query(..., example="small"),
    top_n: int = Query(10, ge=1, le=100),
):
    """업종·규모 기준 지원사업 목록 반환"""
    profile = {"industry_code": industry_code, "company_size": company_size}
    subsidies = _matching.match(profile, ai_priorities=None, top_n=top_n)
    return {"items": subsidies, "total": len(subsidies)}


@router.post("/roi-simulate")
def roi_simulate(req: ROISimulateRequest):
    """
    가상 시나리오 ROI 시뮬레이터 — "회수 타이머"

    사용자가 인건비/에너지 절감률·가동률 개선폭을 슬라이더로 조정하며
    실시간으로 ROI를 재계산할 때 쓰는 엔드포인트. 조정하지 않은 항목은
    업종 기본값(INDUSTRY_ROI_PARAMS)을 그대로 쓰고, 가동률 기준선은
    (요청에 없으면) KICOX 실측 동종평균을 사용한다.
    """
    profile = req.model_dump()

    # 가동률 기준선 — KICOX 실측 동종평균 (요청에 operating_rate 없을 때 사용)
    peer_data = _benchmark.get_peer_data(req.industry_code, req.company_size) or {}

    ai_priority = {
        "ai_type":       req.ai_type,
        "ai_name":       req.ai_type,
        "estimated_cost": req.estimated_cost,
    }

    # 더미 보조금 (자부담률만 필요)
    dummy_subsidy = {"co_funding_rate": req.co_funding_rate}

    param_overrides = {
        "labor_reduction_rate":   req.labor_reduction_rate,
        "energy_reduction_rate":  req.energy_reduction_rate,
        "operating_rate_gain_pp": req.operating_rate_gain_pp,
    }

    results = _roi_calc.calculate(
        company_profile=profile,
        peer_data=peer_data,
        ai_priorities=[ai_priority],
        subsidies=[dummy_subsidy],
        param_overrides=param_overrides,
    )

    base_params = INDUSTRY_ROI_PARAMS.get(req.industry_code, INDUSTRY_ROI_PARAMS["C25"])
    return {
        "results": [r.to_dict() for r in results],
        "defaults": {
            "labor_reduction_rate":   base_params["labor_reduction_rate"],
            "energy_reduction_rate":  base_params["energy_reduction_rate"],
            "operating_rate_gain_pp": base_params["operating_rate_gain_pp"],
            "operating_rate_baseline": peer_data.get("avg_operating_rate"),
        },
    }
