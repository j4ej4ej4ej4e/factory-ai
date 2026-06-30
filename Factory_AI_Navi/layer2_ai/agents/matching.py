"""
layer2_ai/agents/matching.py
==============================
Factory AI Navi — 지원사업 매칭 에이전트

SubsidyTool을 호출하고 진단 결과를 반영하여
기업에 최적화된 지원사업 Top5를 선별합니다.
"""

from layer2_ai.config import logger
from layer2_ai.constants import ROOTS_INDUSTRY_CODES
from layer2_ai.tools.subsidy_tool import SubsidyTool


class MatchingAgent:
    """
    지원사업 매칭 에이전트.

    사용 예시
    ---------
    agent = MatchingAgent()
    results = agent.match(company_profile, ai_priorities)
    """

    def __init__(self):
        self.subsidy_tool = SubsidyTool()

    def match(
        self,
        company_profile: dict,
        ai_priorities: list[dict] | None = None,
        top_n: int = 5,
    ) -> list[dict]:
        """
        기업 프로파일 + 진단 결과를 결합하여 지원사업 매칭.

        Parameters
        ----------
        company_profile : dict
            industry_code, company_size 필수
        ai_priorities : list[dict] | None
            DiagnosticAgent Step B 결과 (ai_type 목록 추출에 활용)
        top_n : int
            반환 건수

        Returns
        -------
        list[dict]
            SubsidyTool.search() 결과 + urgency_label 추가
        """
        industry_code = company_profile["industry_code"]
        company_size  = company_profile["company_size"]

        # 진단된 AI 유형 목록 추출
        ai_types: list[str] = []
        if ai_priorities:
            ai_types = [p["ai_type"] for p in ai_priorities if p.get("ai_type")]

        logger.info(
            "[Matching] 검색: %s / %s / ai_types=%s",
            industry_code, company_size, ai_types,
        )

        results = self.subsidy_tool.search(
            industry_code=industry_code,
            company_size=company_size,
            ai_types=ai_types or None,
            top_n=top_n,
        )

        # 긴급 레이블 및 표시용 필드 보강
        for r in results:
            days = r.get("days_until_deadline")
            if days is not None and 0 <= days <= 7:
                r["urgency_label"] = f"⚠️ 마감 D-{days}"
            elif days is not None and days < 0:
                r["urgency_label"] = "마감 종료"
            else:
                r["urgency_label"] = ""

            # 뿌리업종 전용 여부
            r["is_roots_priority"] = (
                industry_code in ROOTS_INDUSTRY_CODES
                and r.get("program_category") in ("뿌리업종", "뿌리산업")
            )

            # 지원금 표시
            if r.get("max_support_amount"):
                r["support_amount_label"] = f"최대 {r['max_support_amount']:,}만원"
            else:
                r["support_amount_label"] = "금액 미정"

        logger.info("[Matching] 완료: %d건 매칭", len(results))
        return results
