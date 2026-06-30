"""
layer2_ai/agents/roi_calculator.py
=====================================
Factory AI Navi — ROI 시뮬레이션 계산기

업종별 ROI 파라미터 + 기업 프로파일 + 정부지원금을 조합해
AI 도입 투자 수익률을 계산합니다.

계산식
------
  연간 절감액 = 인건비 절감 + 에너지 절감 + 불량 절감
  투자 회수   = 자부담 / 연간 절감액 × 12 (개월)
  3년 순이익  = 연간 절감액 × 3 - 자부담
  ROI (3년)  = 3년 순이익 / 자부담 × 100 (%)
"""

from dataclasses import dataclass, field

from layer1_etl.constants import AI_APPLICATION_TYPES
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_ROI_PARAMS


@dataclass
class ROIResult:
    """AI 도입 항목 하나에 대한 ROI 계산 결과"""
    ai_type: str
    ai_name: str

    # 비용
    implementation_cost: float   # 총 구축비용 (만원)
    gov_subsidy: float           # 정부지원금 (만원)
    co_funding_rate: float       # 자부담 비율
    net_investment: float        # 실 자부담 (만원)

    # 절감액
    labor_savings: float         # 인건비 절감 (만원/년)
    energy_savings: float        # 에너지 절감 (만원/년)
    defect_savings: float        # 불량 절감 (만원/년)
    total_annual_savings: float  # 총 연간 절감액 (만원/년)

    # 수익성
    payback_months: float        # 투자 회수 기간 (개월)
    three_year_profit: float     # 3년 순이익 (만원)
    roi_pct: float               # ROI % (3년)

    # 메타
    gov_subsidy_name: str = ""
    calculation_basis: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ai_type":             self.ai_type,
            "ai_name":             self.ai_name,
            "implementation_cost": f"{self.implementation_cost:,.0f}만원",
            "gov_subsidy":         f"{self.gov_subsidy:,.0f}만원",
            "co_funding_rate":     f"{self.co_funding_rate * 100:.0f}%",
            "net_investment":      f"{self.net_investment:,.0f}만원",
            "labor_savings":       f"{self.labor_savings:,.0f}만원/년",
            "energy_savings":      f"{self.energy_savings:,.0f}만원/년",
            "defect_savings":      f"{self.defect_savings:,.0f}만원/년",
            "total_annual_savings":f"{self.total_annual_savings:,.0f}만원/년",
            "payback_months":      f"{self.payback_months:.1f}개월",
            "three_year_profit":   f"{self.three_year_profit:,.0f}만원",
            "roi_pct":             f"{self.roi_pct:.0f}%",
            "gov_subsidy_name":    self.gov_subsidy_name,
            "calculation_basis":   self.calculation_basis,
        }

    def to_report_text(self) -> str:
        """레포트용 텍스트 포맷"""
        return (
            f"[{self.ai_name}]\n"
            f"  구축비용: {self.implementation_cost:,.0f}만원 "
            f"(정부지원 {self.gov_subsidy:,.0f}만원 / 자부담 {self.net_investment:,.0f}만원)\n"
            f"  연간 절감: {self.total_annual_savings:,.0f}만원"
            f" (인건비 {self.labor_savings:,.0f} + 에너지 {self.energy_savings:,.0f} + 불량 {self.defect_savings:,.0f})\n"
            f"  투자 회수: {self.payback_months:.1f}개월 | 3년 순이익: {self.three_year_profit:,.0f}만원 | ROI: {self.roi_pct:.0f}%\n"
        )


class ROICalculator:
    """
    업종별 ROI 파라미터 기반 AI 도입 수익률 계산기.

    사용 예시
    ---------
    calc = ROICalculator()
    results = calc.calculate(company_profile, peer_data, ai_priorities, subsidies)
    """

    def calculate(
        self,
        company_profile: dict,
        peer_data: dict,
        ai_priorities: list[dict],
        subsidies: list[dict],
    ) -> list[ROIResult]:
        """
        AI 우선순위 Top3 각각에 대해 ROI 계산.

        Parameters
        ----------
        company_profile : dict
            headcount, annual_revenue, annual_production, industry_code
        peer_data : dict
            BenchmarkTool.get_peer_data() 결과
        ai_priorities : list[dict]
            DiagnosticAgent Step B 결과 (ai_type, estimated_cost 포함)
        subsidies : list[dict]
            SubsidyTool.search() 결과

        Returns
        -------
        list[ROIResult]
        """
        industry_code = company_profile.get("industry_code", "C25")
        params = INDUSTRY_ROI_PARAMS.get(industry_code, INDUSTRY_ROI_PARAMS["C25"])

        headcount         = float(company_profile.get("headcount", 30))
        annual_production = float(company_profile.get("annual_production", 0))
        annual_revenue    = float(company_profile.get("annual_revenue", annual_production))

        # 동종업계 기준값 (없으면 파라미터 기본값)
        labor_cost_pp    = float(peer_data.get("avg_labor_cost_per_person") or 4000)
        energy_ratio     = float(peer_data.get("avg_energy_cost_ratio") or 10) / 100

        total_labor  = labor_cost_pp * headcount
        total_energy = annual_revenue * energy_ratio

        # 매칭된 지원사업 중 첫 번째 기준
        best_subsidy    = subsidies[0] if subsidies else {}
        co_funding_rate = float(best_subsidy.get("co_funding_rate") or 0.5)
        subsidy_name    = best_subsidy.get("program_name", "스마트공장 지원사업")

        results: list[ROIResult] = []
        for ai_rec in ai_priorities[:3]:
            result = self._calc_one(
                ai_rec, params, total_labor, total_energy,
                annual_production, co_funding_rate, subsidy_name,
            )
            results.append(result)
            logger.debug("[ROI] %s → 회수 %.1f개월 / ROI %.0f%%",
                         result.ai_name, result.payback_months, result.roi_pct)

        return results

    def _calc_one(
        self,
        ai_rec: dict,
        params: dict,
        total_labor: float,
        total_energy: float,
        annual_production: float,
        co_funding_rate: float,
        subsidy_name: str,
    ) -> ROIResult:
        ai_type = ai_rec.get("ai_type", "")
        ai_name = ai_rec.get("ai_name", AI_APPLICATION_TYPES.get(ai_type, ai_type))

        # 구축 비용
        cost_min, cost_max = params.get("implementation_cost_range", (4000, 8000))
        impl_cost = float(ai_rec.get("estimated_cost") or (cost_min + cost_max) / 2)

        gov_subsidy   = impl_cost * (1 - co_funding_rate)
        net_invest    = impl_cost * co_funding_rate

        # 절감액
        labor_savings  = total_labor   * params.get("labor_reduction_rate",  0.08)
        energy_savings = total_energy  * params.get("energy_reduction_rate", 0.10)
        defect_pp      = params.get("defect_improvement_pp", 1.0) / 100
        defect_savings = defect_pp * annual_production

        total_savings = labor_savings + energy_savings + defect_savings

        payback     = (net_invest / total_savings * 12) if total_savings > 0 else 9999
        profit_3yr  = total_savings * 3 - net_invest
        roi_pct     = (profit_3yr / net_invest * 100) if net_invest > 0 else 0

        basis = [
            f"인건비 절감률 {params['labor_reduction_rate']*100:.0f}% 적용",
            f"에너지 절감률 {params['energy_reduction_rate']*100:.0f}% 적용",
            f"불량률 {params['defect_improvement_pp']:.1f}%p 개선 가정",
            "KIAT 산업기술통계 / 고용노동부 인건비 통계 기반",
        ]

        return ROIResult(
            ai_type=ai_type,
            ai_name=ai_name,
            implementation_cost=impl_cost,
            gov_subsidy=gov_subsidy,
            co_funding_rate=co_funding_rate,
            net_investment=net_invest,
            labor_savings=labor_savings,
            energy_savings=energy_savings,
            defect_savings=defect_savings,
            total_annual_savings=total_savings,
            payback_months=payback,
            three_year_profit=profit_3yr,
            roi_pct=roi_pct,
            gov_subsidy_name=subsidy_name,
            calculation_basis=basis,
        )
