"""
layer2_ai/tools/benchmark_tool.py
===================================
Factory AI Navi — 벤치마크 조회 툴

kiat_industry_stats 테이블에서 동종업계 평균 지표를 조회하고
기업 입력값과의 갭을 계산합니다.
"""

from layer1_etl.models.base import SessionLocal
from layer1_etl.models.diagnosis_history import DiagnosisHistory
from layer1_etl.models.industry_stats import KiatIndustryStat
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_NAMES

# 순위(백분위)를 보여주기 전 최소로 쌓여야 하는 표본 수
# (n=1~2 상태에서 "상위 X%"를 보여주면 의미 없는 숫자가 되므로 방어)
MIN_SAMPLE_SIZE = 5


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

        # ── 불량률 (참고용 — 업종별 공식 통계 없음, 추정치) ──
        # peer_avg_defect_rate는 실측 공공데이터가 아닌 업계 참고 추정값이므로
        # AI 우선순위 결정에는 쓰지 않고(get_improvement_potential 참조),
        # 화면에는 "참고 추정치"로만 노출한다.
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
                "assessment": "양호" if gap_pp <= 0 else f"업계 참고치보다 {gap_pp:.2f}%p 높음",
                "is_estimate": True,
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

    def record_and_rank(
        self, industry_code: str, company_size: str, operating_rate: float | None,
    ) -> dict | None:
        """
        "동종업계 순위표" — 현재 진단의 가동률을 diagnosis_history에 익명 기록하고,
        같은 업종·규모 내에서 몇 %에 드는지 계산한다.

        조작된 통계가 아니라 사용자들이 실제로 입력한 값이 쌓이는 구조라,
        서비스가 커질수록 순위 정확도가 올라가는 성장형 지표다.
        표본이 MIN_SAMPLE_SIZE 미만이면 순위 대신 안내 메시지용 sample_size만 반환한다.

        Parameters
        ----------
        operating_rate : float | None
            사용자 입력 가동률. None이면 기록·계산 자체를 건너뛴다.

        Returns
        -------
        dict | None : {"percentile": float|None, "sample_size": int, "min_sample_size": int}
        """
        if operating_rate is None:
            return None

        session = SessionLocal()
        try:
            session.add(DiagnosisHistory(
                industry_code=industry_code,
                company_size=company_size,
                operating_rate=operating_rate,
            ))
            session.commit()

            rows = (
                session.query(DiagnosisHistory.operating_rate)
                .filter_by(industry_code=industry_code, company_size=company_size)
                .all()
            )
            values = [r[0] for r in rows]
            sample_size = len(values)

            if sample_size < MIN_SAMPLE_SIZE:
                return {
                    "percentile": None,
                    "sample_size": sample_size,
                    "min_sample_size": MIN_SAMPLE_SIZE,
                }

            # 상위 X% = (나보다 가동률이 높거나 같은 표본 수) / 전체 표본 수
            better_or_equal = sum(1 for v in values if v >= operating_rate)
            percentile_from_top = round(better_or_equal / sample_size * 100, 1)

            return {
                "percentile": percentile_from_top,
                "sample_size": sample_size,
                "min_sample_size": MIN_SAMPLE_SIZE,
            }
        except Exception as e:
            logger.error("[Benchmark] 순위 기록/계산 실패: %s", e)
            session.rollback()
            return None
        finally:
            session.close()

    def get_industry_weather(self, gap_analysis: dict) -> dict:
        """
        "업종 날씨예보" — 가동률 갭(KICOX 실측)을 직관적 날씨 아이콘으로 변환.

        불량률·인당생산액 등 추정치는 관여하지 않고, 실측 지표(가동률·에너지비용
        비율)만으로 판단한다 — 화면 표현만 바뀌는 거라 계산 로직은 그대로.

        Returns
        -------
        dict : {icon, label, message, energy_warning, basis}
        """
        operating = gap_analysis.get("operating_rate")
        if not operating:
            return {
                "icon": "🌫️", "label": "관측 불가",
                "message": "가동률 정보가 없어 날씨를 예보할 수 없습니다. 가동률을 입력해 주세요.",
                "energy_warning": None, "basis": None,
            }

        gap_pp = operating.get("gap_pp", 0)

        if gap_pp >= 0:
            icon, label = "☀️", "맑음"
            message = f"가동률이 동종평균보다 {gap_pp:.1f}%p 높습니다. 양호한 상태입니다."
        elif gap_pp >= -5:
            icon, label = "⛅", "구름 조금"
            message = f"가동률이 동종평균보다 {abs(gap_pp):.1f}%p 낮습니다. 주의 깊게 살펴보세요."
        elif gap_pp >= -10:
            icon, label = "🌧️", "비"
            message = f"가동률이 동종평균보다 {abs(gap_pp):.1f}%p 낮습니다. 개선이 필요합니다."
        else:
            icon, label = "⛈️", "폭풍주의보"
            message = f"가동률이 동종평균보다 {abs(gap_pp):.1f}%p나 낮습니다. 즉각적인 조치가 필요합니다."

        energy = gap_analysis.get("energy_cost_ratio")
        energy_warning = None
        if energy and energy.get("gap_pp", 0) > 3:
            energy_warning = f"에너지 비용 비율도 동종평균보다 {energy['gap_pp']:.1f}%p 높아 추가 주의가 필요합니다."

        return {
            "icon": icon, "label": label, "message": message,
            "energy_warning": energy_warning,
            "basis": "KICOX 실측 가동률 갭 기준",
        }

    def get_improvement_potential(self, industry_code: str, gap_analysis: dict) -> list[str]:
        """
        갭 분석 결과에서 개선 우선순위 항목을 문자열 목록으로 반환.
        DiagnosticAgent Step B 프롬프트 구성에 활용됩니다.
        """
        priorities = []

        # 불량률은 업종별 실측 통계가 없는 추정치라 우선순위 결정에서 제외.
        # 대신 diagnostic.py Step B에서 사용자가 직접 체크한 pain_points가
        # AI 우선순위를 주도한다 (실제 데이터 기반).

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
