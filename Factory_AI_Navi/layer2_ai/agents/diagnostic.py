"""
layer2_ai/agents/diagnostic.py
================================
Factory AI Navi — 공정 진단 AI 에이전트

Step A: 동종업계 벤치마크 분석 (DB 조회 + 갭 계산)
Step B: AI 적용 우선순위 Top3 도출 (온라인 RAG + Claude)
Step C: ROI 시뮬레이션 (ROICalculator 위임)
"""

import json

from layer1_etl.constants import AI_APPLICATION_TYPES
from layer2_ai.agents.roi_calculator import ROICalculator, ROIResult
from layer2_ai.config import logger
from layer2_ai.constants import INDUSTRY_NAMES, INDUSTRY_ROI_PARAMS, PAIN_POINT_TO_AI
from layer2_ai.llm_client import call_llm
from layer2_ai.rag.retriever import OnlineRAGRetriever
from layer2_ai.tools.benchmark_tool import BenchmarkTool

# ──────────────────────────────────────────────
# LLM 장애 시 규칙 기반 대체 문구 (ai_type별)
# ──────────────────────────────────────────────
_FALLBACK_TEMPLATES: dict[str, dict[str, str]] = {
    "predictive_maintenance": {
        "target_process": "주요 생산 설비",
        "expected_effect": "설비 고장 사전 감지로 다운타임 감소 (유사사례 기준 30~40%)",
    },
    "vision_inspection": {
        "target_process": "출하 전 품질검사 공정",
        "expected_effect": "AI 비전검사로 육안검사 대비 불량 검출률 향상",
    },
    "energy_optimization": {
        "target_process": "전체 생산 공정",
        "expected_effect": "설비별 에너지 사용패턴 분석으로 비용 절감",
    },
    "process_control": {
        "target_process": "핵심 가공 공정",
        "expected_effect": "공정 변수 실시간 모니터링으로 품질 안정화",
    },
    "demand_forecasting": {
        "target_process": "생산계획·재고관리",
        "expected_effect": "수요예측 기반 생산계획 최적화로 납기 안정화",
    },
    "quality_control": {
        "target_process": "품질관리 전 공정",
        "expected_effect": "품질 데이터 자동 분석으로 불량 조기 발견",
    },
    "supply_chain": {
        "target_process": "자재·공급망 관리",
        "expected_effect": "공급망 가시성 확보로 납기 지연 리스크 완화",
    },
    "robot_automation": {
        "target_process": "반복 조립·이송 공정",
        "expected_effect": "반복작업 자동화로 인력난 완화 및 생산성 향상",
    },
}

# 화면/프롬프트 공용 pain_point 한글 라벨 (반드시 constants.py의
# PAIN_POINT_TO_AI 키와 정확히 일치해야 함)
_PAIN_POINT_LABELS: dict[str, str] = {
    "defect_high":           "불량률 높음",
    "equipment_breakdown":   "설비 자주 고장",
    "energy_cost":           "에너지 비용 과다",
    "quality_inconsistency": "품질 균일성 불량",
    "delivery_delay":        "납기 지연",
    "labor_shortage":        "인력 부족",
    "material_waste":        "재료비 과다",
}

# ──────────────────────────────────────────────
# Claude 시스템 프롬프트
# ──────────────────────────────────────────────
_SYSTEM_PROMPT = """당신은 중소 제조기업 AI 도입 전문 컨설턴트입니다.
사장님이 이미 알고 있는 현장 문제(주요 문제점)를 출발점으로 삼아,
실측 공공데이터(가동률)와 실제 도입 사례(RAG 검색 결과)를 근거로
"무엇을, 왜, 얼마나 효과가 있을지"를 뒷받침하는 AI 적용 우선순위를 제시합니다.

원칙:
- 사장님이 이미 아는 문제를 되풀이하지 말고, 그 문제에 대한 근거(실제 사례·정량 효과)를 제시할 것
- 가동률은 실측 공공데이터이므로 인용 가능하나, 불량률 동종평균은 추정치이므로 "참고치"로만 언급하고 확정적 비교 근거로 쓰지 말 것
- 모호한 표현보다 RAG 검색 결과에 있는 구체적 수치·사례를 우선 인용할 것
- 정부지원사업 연계 가능성을 항상 언급할 것
- 뿌리업종(주조/금형/소성가공/용접/표면처리/열처리)은 소진공 뿌리업종 지원사업 우선 언급
- 검색 결과 중 "실패사례·주의점"으로 표시된 자료가 있으면, 좋은 얘기만 전달하지 말고
  해당 리스크·주의사항을 rationale에 한 문장이라도 반영해 균형 잡힌 근거를 제시할 것"""

_USER_PROMPT_TEMPLATE = """## 진단 요청 정보

**기업 프로파일**
- 업종: {industry_name} (KSIC {industry_code})
- 기업 규모: {company_size_label} ({headcount}인)
- 연간 생산액: {annual_production:,.0f}만원
- 연간 매출: {annual_revenue:,.0f}만원

**현재 KPI (기업 입력값)**
{kpi_text}

**주요 문제점**
{pain_points_text}

**동종업계 벤치마크 (KIAT 산업기술통계)**
{benchmark_text}

**갭 분석 결과 (개선 필요 항목)**
{gap_text}

**업종 최우선 AI 유형**
{best_ai_text}

**참고: 실제 도입 사례 (웹 검색 결과)**
{rag_text}

---

위 정보를 바탕으로 AI 적용 우선순위 Top3를 다음 JSON 형식으로만 출력하세요.
설명 텍스트 없이 JSON만 출력합니다.

```json
[
  {{
    "rank": 1,
    "ai_type": "predictive_maintenance",
    "ai_name": "예측유지보수",
    "target_process": "CNC 가공 공정",
    "expected_effect": "설비 다운타임 40% 감소 (유사 사례 기준)",
    "implementation_period": "3~6개월",
    "estimated_cost": 6000,
    "rationale": "설비 잦은 고장(체크된 문제)과 가동률이 동종평균보다 낮은 점을 실제 도입 사례로 뒷받침"
  }},
  {{...}},
  {{...}}
]
```

ai_type은 반드시 다음 중 하나여야 합니다:
predictive_maintenance, vision_inspection, energy_optimization,
process_control, demand_forecasting, quality_control, supply_chain, robot_automation

estimated_cost는 만원 단위 숫자(int)로만 출력합니다."""


class DiagnosticAgent:
    """
    3단계 공정 진단 AI 에이전트.

    사용 예시
    ---------
    agent = DiagnosticAgent()
    result = agent.run(company_profile)
    # result: {
    #   "step_a": {"peer_data": ..., "gap_analysis": ...},
    #   "step_b": {"ai_priorities": [...], "rag_sources": [...]},
    #   "step_c": {"roi_results": [...]},
    # }
    """

    def __init__(self):
        self.benchmark_tool = BenchmarkTool()
        self.rag_retriever  = OnlineRAGRetriever()
        self.roi_calculator = ROICalculator()

    # ──────────────────────────────────────────────
    # 메인 실행
    # ──────────────────────────────────────────────

    def run(self, company_profile: dict, subsidies: list[dict]) -> dict:
        """
        Step A → B → C 순차 실행.

        Parameters
        ----------
        company_profile : dict
            industry_code, company_size, headcount,
            annual_revenue, annual_production,
            defect_rate, operating_rate, energy_cost_ratio,
            production_per_person (선택), pain_points (list)
        subsidies : list[dict]
            MatchingAgent 또는 SubsidyTool 결과 (ROI 계산 시 자부담률 참조)

        Returns
        -------
        dict
            step_a, step_b, step_c 결과 포함
        """
        logger.info("[Diagnostic] 진단 시작: %s / %s",
                    company_profile.get("industry_code"),
                    company_profile.get("company_size"))

        step_a = self.run_step_a(company_profile)
        step_b = self.run_step_b(company_profile, step_a)
        step_c = self.run_step_c(company_profile, step_a["peer_data"] or {}, step_b["ai_priorities"], subsidies)

        return {"step_a": step_a, "step_b": step_b, "step_c": step_c}

    # ──────────────────────────────────────────────
    # Step A: 벤치마크 분석
    # ──────────────────────────────────────────────

    def run_step_a(self, company_profile: dict) -> dict:
        """
        동종업계 벤치마크 조회 및 갭 분석.

        Returns
        -------
        dict
            peer_data: 동종업계 평균 (None if 데이터 없음)
            gap_analysis: 지표별 갭 딕셔너리
            improvement_priorities: 개선 우선순위 텍스트 목록
        """
        industry_code = company_profile["industry_code"]
        company_size  = company_profile["company_size"]

        peer_data = self.benchmark_tool.get_peer_data(industry_code, company_size)

        company_kpi = {
            "defect_rate":          company_profile.get("defect_rate"),
            "operating_rate":       company_profile.get("operating_rate"),
            "energy_cost_ratio":    company_profile.get("energy_cost_ratio"),
            "production_per_person": company_profile.get("production_per_person"),
        }

        gap_analysis = {}
        improvement_priorities = []
        industry_weather = None

        if peer_data:
            gap_analysis = self.benchmark_tool.analyze_gap(company_kpi, peer_data)
            improvement_priorities = self.benchmark_tool.get_improvement_potential(
                industry_code, gap_analysis
            )
            industry_weather = self.benchmark_tool.get_industry_weather(gap_analysis)

        peer_ranking = self.benchmark_tool.record_and_rank(
            industry_code, company_size, company_profile.get("operating_rate")
        )

        logger.info("[Step A] 완료: 갭 분석 %d개 항목", len(gap_analysis))
        return {
            "peer_data":             peer_data,
            "gap_analysis":          gap_analysis,
            "improvement_priorities": improvement_priorities,
            "industry_weather":      industry_weather,
            "peer_ranking":          peer_ranking,
        }

    # ──────────────────────────────────────────────
    # Step B: AI 우선순위 도출
    # ──────────────────────────────────────────────

    def run_step_b(self, company_profile: dict, step_a_result: dict) -> dict:
        """
        온라인 RAG 검색 + Claude로 AI 적용 우선순위 Top3 도출.

        Returns
        -------
        dict
            ai_priorities: list[dict] (rank, ai_type, ai_name, ...)
            rag_sources:   list[dict] (검색에 활용된 참고 자료)
        """
        industry_code = company_profile["industry_code"]
        company_size  = company_profile["company_size"]
        pain_points   = company_profile.get("pain_points", [])

        # 업종별 최우선 AI 유형 결정
        params  = INDUSTRY_ROI_PARAMS.get(industry_code, {})
        best_ai = params.get("best_ai", [])

        # Pain point에서 추가 AI 유형 도출 (판단 근거 트레이스용으로 매핑 과정 기록)
        pain_ai = []
        pain_point_mappings = []
        for pp in pain_points:
            mapped = PAIN_POINT_TO_AI.get(pp, [])
            pain_ai.extend(mapped)
            pain_point_mappings.append({
                "pain_point": pp,
                "pain_point_label": _PAIN_POINT_LABELS.get(pp, pp),
                "mapped_ai_types": mapped,
                "mapped_ai_names": [AI_APPLICATION_TYPES.get(t, t) for t in mapped],
            })
        # 중복 제거, 사장님이 직접 체크한 pain point 기반 AI 우선
        # (업종 평균 best_ai는 pain_point 미입력 시 보조 후보로 사용)
        priority_ai = list(dict.fromkeys(pain_ai + best_ai))

        # RAG: 첫 번째 우선 AI 유형으로 검색
        primary_ai = priority_ai[0] if priority_ai else "predictive_maintenance"
        rag_sources = self.rag_retriever.retrieve(industry_code, primary_ai, company_profile)

        # Claude 프롬프트 구성
        prompt = self._build_step_b_prompt(company_profile, step_a_result, rag_sources, priority_ai)

        # Claude 호출
        ai_priorities = self._call_claude_for_priorities(prompt, priority_ai, industry_code)

        # "판단 근거 트레이스" — 블랙박스 추천이 아니라, 어떤 규칙과 근거를
        # 거쳐 이 추천에 도달했는지 그대로 노출한다 (설명 가능한 AI)
        decision_trace = {
            "pain_point_mappings":  pain_point_mappings,
            "industry_default_ai": {
                "ai_types": best_ai,
                "ai_names": [AI_APPLICATION_TYPES.get(t, t) for t in best_ai],
            },
            "priority_order": {
                "ai_types": priority_ai,
                "ai_names": [AI_APPLICATION_TYPES.get(t, t) for t in priority_ai],
            },
            "rag_query_ai_type": primary_ai,
            "rag_query_ai_name": AI_APPLICATION_TYPES.get(primary_ai, primary_ai),
        }

        logger.info("[Step B] 완료: AI 우선순위 %d개 도출, RAG 소스 %d건",
                    len(ai_priorities), len(rag_sources))
        return {
            "ai_priorities": ai_priorities,
            "rag_sources":   rag_sources,
            "decision_trace": decision_trace,
        }

    def _build_step_b_prompt(
        self,
        company_profile: dict,
        step_a: dict,
        rag_sources: list[dict],
        priority_ai: list[str],
    ) -> str:
        industry_code = company_profile["industry_code"]
        industry_name = INDUSTRY_NAMES.get(industry_code, industry_code)
        company_size  = company_profile["company_size"]
        size_label    = "소기업 (50인 미만)" if company_size == "small" else "중기업 (50~300인)"

        # KPI 텍스트
        kpi_lines = []
        if company_profile.get("defect_rate") is not None:
            kpi_lines.append(f"- 불량률: {company_profile['defect_rate']}%")
        if company_profile.get("operating_rate") is not None:
            kpi_lines.append(f"- 설비 가동률: {company_profile['operating_rate']}%")
        if company_profile.get("energy_cost_ratio") is not None:
            kpi_lines.append(f"- 에너지 비용 비율: {company_profile['energy_cost_ratio']}%")
        if company_profile.get("equipment_age") is not None:
            kpi_lines.append(f"- 설비 노후도: {company_profile['equipment_age']}년")
        kpi_text = "\n".join(kpi_lines) if kpi_lines else "- 입력값 없음"

        # Pain point 텍스트
        pain_points = company_profile.get("pain_points", [])
        pain_text = "\n".join(
            f"- {_PAIN_POINT_LABELS.get(p, p)}" for p in pain_points
        ) if pain_points else "- 미입력"

        # 벤치마크 텍스트
        peer = step_a.get("peer_data") or {}
        bench_lines = []
        if peer.get("avg_operating_rate"):
            bench_lines.append(f"- 동종업계 평균 가동률(KICOX 실측): {peer['avg_operating_rate']}%")
        if peer.get("avg_defect_rate"):
            bench_lines.append(f"- 동종업계 평균 불량률(참고 추정치, 확정 근거 아님): {peer['avg_defect_rate']}%")
        if peer.get("avg_labor_cost_per_person"):
            bench_lines.append(f"- 인당 인건비: {peer['avg_labor_cost_per_person']:,.0f}만원/년")
        if peer.get("avg_energy_cost_ratio"):
            bench_lines.append(f"- 에너지 비용 비율: {peer['avg_energy_cost_ratio']}%")
        if peer.get("ai_adoption_rate"):
            bench_lines.append(f"- 동종업계 AI 도입률: {peer['ai_adoption_rate']}%")
        benchmark_text = "\n".join(bench_lines) if bench_lines else "- 데이터 없음 (seed_db.py 실행 필요)"

        # 갭 텍스트
        gaps = step_a.get("improvement_priorities", [])
        gap_text = "\n".join(f"- {g}" for g in gaps) if gaps else "- 갭 분석 데이터 없음"

        # 우선 AI 유형
        best_ai_text = "\n".join(
            f"- {AI_APPLICATION_TYPES.get(ai, ai)}" for ai in priority_ai[:3]
        )

        # RAG 텍스트 — 실패사례·주의점도 놓치지 않도록 top4까지 포함
        if rag_sources:
            rag_lines = []
            for i, r in enumerate(rag_sources[:4], 1):
                content = r.get("content") or r.get("snippet", "")
                case_type = r.get("case_type", "일반정보")
                rag_lines.append(
                    f"[사례 {i} · {case_type}] {r.get('title', '')}\n"
                    f"출처: {r.get('url', '')}\n"
                    f"내용: {content[:400]}"
                )
            rag_text = "\n\n".join(rag_lines)
        else:
            rag_text = "- 검색 결과 없음 (API 키 설정 후 재실행 권장)"

        return _USER_PROMPT_TEMPLATE.format(
            industry_name=industry_name,
            industry_code=industry_code,
            company_size_label=size_label,
            headcount=company_profile.get("headcount", 0),
            annual_production=company_profile.get("annual_production", 0),
            annual_revenue=company_profile.get("annual_revenue", 0),
            kpi_text=kpi_text,
            pain_points_text=pain_text,
            benchmark_text=benchmark_text,
            gap_text=gap_text,
            best_ai_text=best_ai_text,
            rag_text=rag_text,
        )

    def _call_claude_for_priorities(
        self, prompt: str, priority_ai: list[str], industry_code: str,
    ) -> list[dict]:
        """LLM 호출 → AI 우선순위 JSON 파싱"""
        try:
            raw = call_llm(user=prompt, system=_SYSTEM_PROMPT, max_tokens=1500)

            # ```json ... ``` 또는 순수 JSON 배열 추출
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            start = raw.find("[")
            end   = raw.rfind("]") + 1
            priorities: list[dict] = json.loads(raw[start:end])

            # ai_name 보완
            for p in priorities:
                if not p.get("ai_name") and p.get("ai_type"):
                    p["ai_name"] = AI_APPLICATION_TYPES.get(p["ai_type"], p["ai_type"])

            return priorities

        except Exception as e:
            logger.error("[Step B] Claude 호출 실패: %s → 규칙 기반 우선순위 사용", e)
            return self._fallback_priorities(priority_ai, industry_code)

    @staticmethod
    def _fallback_priorities(priority_ai: list[str], industry_code: str) -> list[dict]:
        """
        LLM 일시 장애 시 대체 우선순위.

        고정된 예측유지보수 1건짜리 하드코딩 대신, 이미 계산된
        priority_ai(사장님이 체크한 pain_point + 업종 best_ai 기반, run_step_b
        에서 산출) 순서를 그대로 살려 Top3을 구성한다. RAG 실시간 사례
        인용만 못 할 뿐, "이 회사·이 업종엔 이 AI가 맞다"는 근거는
        LLM 없이도 이미 갖고 있는 데이터로 정확히 반영된다.
        """
        params = INDUSTRY_ROI_PARAMS.get(industry_code, INDUSTRY_ROI_PARAMS["C25"])
        cost_min, cost_max = params.get("implementation_cost_range", (4000, 8000))
        mid_cost = int((cost_min + cost_max) / 2)

        types = priority_ai[:3] if priority_ai else ["predictive_maintenance"]
        results = []
        for i, ai_type in enumerate(types, 1):
            tmpl = _FALLBACK_TEMPLATES.get(ai_type, _FALLBACK_TEMPLATES["predictive_maintenance"])
            results.append({
                "rank": i,
                "ai_type": ai_type,
                "ai_name": AI_APPLICATION_TYPES.get(ai_type, ai_type),
                "target_process": tmpl["target_process"],
                "expected_effect": tmpl["expected_effect"],
                "implementation_period": "3~6개월",
                "estimated_cost": mid_cost,
                "rationale": "실시간 사례 검색이 일시적으로 지연되어, 체크하신 현장 문제와 업종 특성 기반 규칙으로 대신 추천했습니다.",
            })
        return results

    # ──────────────────────────────────────────────
    # Step C: ROI 시뮬레이션
    # ──────────────────────────────────────────────

    def run_step_c(
        self,
        company_profile: dict,
        peer_data: dict,
        ai_priorities: list[dict],
        subsidies: list[dict],
    ) -> dict:
        """
        ROICalculator에 위임하여 각 AI 항목별 ROI 계산.

        Returns
        -------
        dict
            roi_results: list[ROIResult]
        """
        roi_results = self.roi_calculator.calculate(
            company_profile, peer_data, ai_priorities, subsidies
        )
        logger.info("[Step C] 완료: ROI 계산 %d건", len(roi_results))
        return {"roi_results": roi_results}
