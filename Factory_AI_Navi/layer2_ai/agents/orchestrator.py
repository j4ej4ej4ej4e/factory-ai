"""
layer2_ai/agents/orchestrator.py
==================================
Factory AI Navi — AI 에이전트 오케스트레이터

전체 파이프라인 실행 순서:
  START
    → [매칭] MatchingAgent.match()           (지원사업 먼저 조회 — ROI 계산 시 자부담률 필요)
    → [Step A] DiagnosticAgent.run_step_a()  (벤치마크 갭 분석)
    → [Step B] DiagnosticAgent.run_step_b()  (RAG + Claude → AI 우선순위)
    → [Step C] DiagnosticAgent.run_step_c()  (ROI 시뮬레이션)
  END → DiagnosisReport 반환
"""

from dataclasses import dataclass, field
from datetime import datetime

from layer2_ai.agents.diagnostic import DiagnosticAgent
from layer2_ai.agents.matching import MatchingAgent
from layer2_ai.agents.roi_calculator import ROIResult
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_NAMES


@dataclass
class DiagnosisReport:
    """최종 진단 결과 리포트"""

    # 기업 정보
    industry_code: str
    industry_name: str
    company_size: str
    headcount: int
    annual_production: float

    # Step A
    peer_data: dict
    gap_analysis: dict
    improvement_priorities: list[str]

    # Step B
    ai_priorities: list[dict]
    rag_sources: list[dict]

    # Step C
    roi_results: list[ROIResult]

    # 매칭
    subsidies: list[dict]

    # 메타
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "industry_code":          self.industry_code,
            "industry_name":          self.industry_name,
            "company_size":           self.company_size,
            "headcount":              self.headcount,
            "annual_production":      self.annual_production,
            "peer_data":              self.peer_data,
            "gap_analysis":           self.gap_analysis,
            "improvement_priorities": self.improvement_priorities,
            "ai_priorities":          self.ai_priorities,
            "rag_sources":            [
                {"url": r.get("url"), "title": r.get("title"),
                 "relevance_score": r.get("relevance_score")}
                for r in self.rag_sources
            ],
            "roi_results":  [r.to_dict() for r in self.roi_results],
            "subsidies":    self.subsidies,
            "generated_at": self.generated_at,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
        }

    def print_summary(self) -> None:
        """콘솔 출력용 요약"""
        sep = "=" * 60
        print(f"\n{sep}")
        print(f"Factory AI Navi — AI 공정 진단 결과")
        print(f"[ {self.industry_name} | {self.company_size} | {self.headcount}인 ]")
        print(sep)

        print("\n▶ 동종업계 갭 분석")
        for key, gap in self.gap_analysis.items():
            print(f"  {gap.get('label', key)}: {gap.get('assessment', '')}")

        print("\n▶ AI 적용 우선순위 Top3")
        for p in self.ai_priorities:
            print(f"  {p.get('rank', '?')}위. {p.get('ai_name')} — {p.get('target_process')}")
            print(f"       효과: {p.get('expected_effect')}")
            print(f"       기간: {p.get('implementation_period')} / 비용: {p.get('estimated_cost'):,}만원")

        print("\n▶ ROI 시뮬레이션")
        for r in self.roi_results:
            print(r.to_report_text())

        print("\n▶ 추천 지원사업 Top5")
        for i, s in enumerate(self.subsidies, 1):
            urgent = s.get("urgency_label", "")
            print(f"  {i}. {s.get('program_name')} {urgent}")
            print(f"     지원금: {s.get('support_amount_label')} / 마감: {s.get('application_end')}")

        print(f"\n생성 시각: {self.generated_at} (소요: {self.elapsed_seconds:.1f}초)")
        print(sep)


class Orchestrator:
    """
    Layer 2 AI 에이전트 오케스트레이터.

    사용 예시
    ---------
    orchestrator = Orchestrator()
    report = orchestrator.run({
        "industry_code":    "C25",
        "company_size":     "small",
        "headcount":        35,
        "annual_revenue":   150_000,    # 만원
        "annual_production": 130_000,   # 만원
        "defect_rate":      5.1,        # %
        "operating_rate":   60.0,       # %
        "energy_cost_ratio": 11.0,      # %
        "equipment_age":    8,          # 년
        "pain_points":      ["defect_high", "equipment_breakdown"],
    })
    report.print_summary()
    """

    def __init__(self):
        self.diagnostic = DiagnosticAgent()
        self.matching   = MatchingAgent()

    def run(self, company_profile: dict) -> DiagnosisReport:
        """
        전체 진단 파이프라인 실행.

        Parameters
        ----------
        company_profile : dict
            필수: industry_code, company_size, headcount,
                  annual_revenue, annual_production
            선택: defect_rate, operating_rate, energy_cost_ratio,
                  equipment_age, production_per_person, pain_points

        Returns
        -------
        DiagnosisReport
        """
        start = datetime.now()
        industry_code = company_profile["industry_code"]
        industry_name = INDUSTRY_NAMES.get(industry_code, industry_code)

        logger.info("[Orchestrator] === 진단 시작: %s / %s ===",
                    industry_name, company_profile.get("company_size"))

        # ① 지원사업 매칭 (ROI 자부담률 계산에 필요해서 먼저 실행)
        logger.info("[Orchestrator] → 지원사업 매칭")
        subsidies = self.matching.match(company_profile, ai_priorities=None)

        # ② Step A: 벤치마크 갭 분석
        logger.info("[Orchestrator] → Step A: 벤치마크 분석")
        step_a = self.diagnostic.run_step_a(company_profile)

        # ③ Step B: AI 우선순위 도출 (RAG + Claude)
        logger.info("[Orchestrator] → Step B: AI 우선순위 도출")
        step_b = self.diagnostic.run_step_b(company_profile, step_a)

        # ④ 지원사업 재매칭 (AI 유형 반영)
        if step_b.get("ai_priorities"):
            logger.info("[Orchestrator] → 지원사업 재매칭 (AI 유형 반영)")
            subsidies = self.matching.match(company_profile, step_b["ai_priorities"])

        # ⑤ Step C: ROI 시뮬레이션
        logger.info("[Orchestrator] → Step C: ROI 시뮬레이션")
        step_c = self.diagnostic.run_step_c(
            company_profile,
            step_a.get("peer_data") or {},
            step_b.get("ai_priorities", []),
            subsidies,
        )

        elapsed = (datetime.now() - start).total_seconds()
        logger.info("[Orchestrator] === 진단 완료 (%.1f초) ===", elapsed)

        return DiagnosisReport(
            industry_code=industry_code,
            industry_name=industry_name,
            company_size=company_profile.get("company_size", ""),
            headcount=company_profile.get("headcount", 0),
            annual_production=company_profile.get("annual_production", 0),
            peer_data=step_a.get("peer_data") or {},
            gap_analysis=step_a.get("gap_analysis", {}),
            improvement_priorities=step_a.get("improvement_priorities", []),
            ai_priorities=step_b.get("ai_priorities", []),
            rag_sources=step_b.get("rag_sources", []),
            roi_results=step_c.get("roi_results", []),
            subsidies=subsidies,
            elapsed_seconds=elapsed,
        )
