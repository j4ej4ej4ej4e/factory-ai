"""
layer2_ai/tools/benchmark_tool.py
===================================
Factory AI Navi — 벤치마크 조회 툴

kiat_industry_stats 테이블에서 동종업계 평균 지표를 조회하고
기업 입력값과의 갭을 계산합니다.
"""

from layer1_etl.models.base import SessionLocal
from layer1_etl.models.industry_stats import KiatIndustryStat
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_NAMES


class BenchmarkTool:
    """
    동종업계 벤치마크 데이터 조회 및 갭 분석.

    사용 예시
    ---------
    tool = BenchmarkTool()
    peer = tool.get_peer_data("C25", "small")
    gap  = tool.analyze_gap({"defect_rate": 5.1, "operating_rate": 60}, peer)
    """

    def get_peer_data(self, industry_code: str, company_size: str) -> dict | None:
        """
        동종업계 벤치마크 데이터 조회.

        Parameters
        ----------
        industry_code : str
            KSIC 업종코드 (예: "C25")
        company_size : str
            기업 규모 ("small" | "medium")

        Returns
        -------
        dict | None
            KiatIndustryStat.to_dict() 결과. 데이터 없으면 None.
        """
        session = SessionLocal()
        try:
            stat = (
                session.query(KiatIndustryStat)
                .filter_by(industry_code=industry_code, company_size=company_size)
                .order_by(KiatIndustryStat.reference_year.desc())
                .first()
            )
            if stat is None:
                logger.warning(
                    "[Benchmark] 데이터 없음: %s / %s — seed_db.py 실행 필요",
                    industry_code, company_size,
                )
                return None
            return stat.to_dict()
        finally:
            session.close()

    def analyze_gap(self, company_kpi: dict, peer_data: dict) -> dict:
        """
        기업 KPI vs 동종업계 평균 갭 분석.

        Parameters
        ----------
        company_kpi : dict
            기업 입력 KPI. 키: defect_rate, operating_rate,
            energy_cost_ratio, production_per_person
        peer_data : dict
            get_peer_data() 반환값

        Returns
        -------
        dict
            지표별 갭 분석 결과
        """
        gaps: dict[str, dict] = {}

        # ── 인당 생산액 ──────────────────────────────
        if peer_data.get("avg_production_per_person") and company_kpi.get("production_per_person"):
            peer_v  = peer_data["avg_production_per_person"]
            my_v    = company_kpi["production_per_person"]
            gap_pct = (my_v - peer_v) / peer_v * 100
            gaps["production_per_person"] = {
                "label":      "인당 생산액",
                "unit":       "만원/년",
                "company":    round(my_v, 0),
                "peer_avg":   round(peer_v, 0),
                "gap_pct":    round(gap_pct, 1),
                "assessment": "양호" if gap_pct >= 0 else f"동종평균 대비 {abs(gap_pct):.1f}% 낮음",
            }

        # ── 불량률 (낮을수록 좋음) ───────────────────
        if peer_data.get("avg_defect_rate") is not None and company_kpi.get("defect_rate") is not None:
            peer_v = peer_data["avg_defect_rate"]
            my_v   = company_kpi["defect_rate"]
            gap_pp = my_v - peer_v
            gaps["defect_rate"] = {
                "label":      "불량률",
                "unit":       "%",
                "company":    round(my_v, 2),
                "peer_avg":   round(peer_v, 2),
                "gap_pp":     round(gap_pp, 2),
                "assessment": "양호" if gap_pp <= 0 else f"동종평균보다 {gap_pp:.2f}%p 높음 → 개선 필요",
            }

        # ── 가동률 (높을수록 좋음) ───────────────────
        if peer_data.get("avg_operating_rate") is not None and company_kpi.get("operating_rate") is not None:
            peer_v = peer_data["avg_operating_rate"]
            my_v   = company_kpi["operating_rate"]
            gap_pp = my_v - peer_v
            gaps["operating_rate"] = {
                "label":      "설비 가동률",
                "unit":       "%",
                "company":    round(my_v, 1),
                "peer_avg":   round(peer_v, 1),
                "gap_pp":     round(gap_pp, 1),
                "assessment": "양호" if gap_pp >= 0 else f"동종평균보다 {abs(gap_pp):.1f}%p 낮음 → 개선 필요",
            }

        # ── 에너지 비용 비율 (낮을수록 좋음) ────────
        if peer_data.get("avg_energy_cost_ratio") is not None and company_kpi.get("energy_cost_ratio") is not None:
            peer_v = peer_data["avg_energy_cost_ratio"]
            my_v   = company_kpi["energy_cost_ratio"]
            gap_pp = my_v - peer_v
            gaps["energy_cost_ratio"] = {
                "label":      "에너지 비용 비율",
                "unit":       "%",
                "company":    round(my_v, 1),
                "peer_avg":   round(peer_v, 1),
                "gap_pp":     round(gap_pp, 1),
                "assessment": "양호" if gap_pp <= 0 else f"동종평균보다 {gap_pp:.1f}%p 높음 → 개선 필요",
            }

        # ── AI 도입률 (참고용) ───────────────────────
        if peer_data.get("ai_adoption_rate") is not None:
            gaps["ai_adoption_rate"] = {
                "label":    "AI 도입률",
                "unit":     "%",
                "peer_avg": round(peer_data["ai_adoption_rate"], 1),
                "note":     "동종업계 AI 도입률 참고값",
            }

        return gaps

    def get_improvement_potential(self, industry_code: str, gap_analysis: dict) -> list[str]:
        """
        갭 분석 결과에서 개선 우선순위 항목을 문자열 목록으로 반환.
        DiagnosticAgent Step B 프롬프트 구성에 활용됩니다.
        """
        priorities = []

        defect = gap_analysis.get("defect_rate", {})
        if defect.get("gap_pp", 0) > 0.5:
            priorities.append(f"불량률 {defect['company']}% (동종평균 {defect['peer_avg']}%보다 {defect['gap_pp']:.2f}%p 높음)")

        operating = gap_analysis.get("operating_rate", {})
        if operating.get("gap_pp", 0) < -5:
            priorities.append(f"가동률 {operating['company']}% (동종평균 {operating['peer_avg']}%보다 {abs(operating['gap_pp']):.1f}%p 낮음)")

        energy = gap_analysis.get("energy_cost_ratio", {})
        if energy.get("gap_pp", 0) > 2:
            priorities.append(f"에너지 비용 비율 {energy['company']}% (동종평균 {energy['peer_avg']}%보다 {energy['gap_pp']:.1f}%p 높음)")

        production = gap_analysis.get("production_per_person", {})
        if production.get("gap_pct", 0) < -10:
            priorities.append(f"인당 생산액 {production['company']:,.0f}만원 (동종평균 대비 {abs(production['gap_pct']):.1f}% 낮음)")

        return priorities
