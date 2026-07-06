"""
layer3_api/routers/subsidies.py
=================================
GET /api/v1/subsidies — 현재 신청 가능 지원사업 목록
POST /api/v1/roi-simulate — ROI 단독 계산
POST /api/v1/subsidy-eligibility — 지원사업 자격 자동 체크리스트
"""

import json

from fastapi import APIRouter, Query
from layer2_ai.agents.matching import MatchingAgent
from layer2_ai.agents.roi_calculator import ROICalculator
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_NAMES, INDUSTRY_ROI_PARAMS
from layer2_ai.llm_client import call_llm
from layer2_ai.tools.benchmark_tool import BenchmarkTool
from layer3_api.schemas import EligibilityCheckRequest, ROISimulateRequest

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


_ELIGIBILITY_FALLBACK = {
    "items": [],
    "overall": "확인 필요",
    "overall_note": "일시적 오류로 자동 체크에 실패했습니다 — 공고 원문을 직접 확인해 주세요.",
}


@router.post("/subsidy-eligibility")
def check_eligibility(req: EligibilityCheckRequest):
    """
    지원사업 자격 자동 체크리스트.

    공고 설명(description) 원문에서 신청 자격 요건을 뽑아 사용자 회사
    프로필과 대조한다. 사용자가 지원사업 하나를 클릭했을 때만 호출되는
    온디맨드 방식 — 매칭된 모든 공고에 대해 미리 돌리지 않음(LLM 호출
    비용·할당량 절약).
    """
    if not req.description.strip():
        return {
            "items": [],
            "overall": "확인 필요",
            "overall_note": "공고 설명이 없어 자동 체크가 불가합니다 — 공고 원문을 직접 확인해 주세요.",
        }

    industry_name = INDUSTRY_NAMES.get(req.industry_code, req.industry_code)
    size_label = "소기업 (50인 미만)" if req.company_size == "small" else "중기업 (50~300인)"

    prompt = f"""다음 정부지원사업 공고문에서 신청 자격 요건을 찾아, 아래 신청 기업 정보와
대조해 체크리스트를 작성하세요.

[공고명] {req.program_name}
[공고 내용]
{req.description[:1500]}

[신청 기업 정보]
- 업종: {industry_name} ({req.industry_code})
- 기업 규모: {size_label}
- 종업원 수: {req.headcount}인

JSON으로만 출력 (설명·마크다운 없이):
{{
  "items": [
    {{"requirement": "공고문에서 추출한 자격요건 한 줄", "status": "충족|확인필요|미충족", "note": "판단 근거 한 줄"}}
  ],
  "overall": "충족 가능성 높음|보통|낮음",
  "overall_note": "종합 코멘트 한 줄"
}}

규칙:
- 공고문에 지역·업종·규모·설립연차 등 제한이 있으면 반드시 항목으로 뽑아 대조할 것
- 공고문에 없는 정보(예: 매출액, 설립일)로는 함부로 판단하지 말고 "확인필요"로 표시할 것
- 최대 5개 항목만 추출
- 공고문 자체에 자격요건이 뚜렷하지 않으면 items를 빈 배열로 두고 overall_note에 그 사실을 명시할 것"""

    try:
        raw = call_llm(user=prompt, max_tokens=700)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        result = json.loads(raw[start:end])
        result.setdefault("items", [])
        result.setdefault("overall", "확인 필요")
        result.setdefault("overall_note", "")
        return result
    except Exception as e:
        logger.error("[Eligibility] 자격 체크 실패: %s", e)
        return _ELIGIBILITY_FALLBACK
