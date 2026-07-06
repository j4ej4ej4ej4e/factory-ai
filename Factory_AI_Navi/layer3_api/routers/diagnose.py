"""
layer3_api/routers/diagnose.py
================================
POST /api/v1/diagnose — SSE 스트리밍 AI 진단
"""

import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from layer2_ai.agents.diagnostic import DiagnosticAgent
from layer2_ai.agents.matching import MatchingAgent
from layer2_ai.constants import INDUSTRY_NAMES
from layer3_api.schemas import CompanyProfileRequest
from layer3_api.services.report_cache import report_cache

router = APIRouter()
_diagnostic = DiagnosticAgent()
_matching = MatchingAgent()


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.post("/diagnose")
async def diagnose(company: CompanyProfileRequest):
    """
    기업 프로파일 수신 → 4단계 AI 진단 → SSE 이벤트 스트리밍

    이벤트 종류:
      progress   : 단계 시작 알림  { step, message, pct }
      step_result: 단계 결과      { step, data }
      error      : 오류           { step, message }
      complete   : 완료           { report_id, elapsed, pct:100 }
    """
    profile = company.model_dump()

    async def generate():
        loop = asyncio.get_event_loop()

        try:
            # ── 매칭 ─────────────────────────────────────
            yield _sse("progress", {"step": "matching", "message": "지원사업 검색 중...", "pct": 10})
            # top_n=100 — "마감 캘린더"에서 매칭되는 공고를 사실상 전부 보여주기 위해 넉넉히 조회
            subsidies = await loop.run_in_executor(
                None, lambda: _matching.match(profile, ai_priorities=None, top_n=100)
            )
            yield _sse("step_result", {"step": "matching", "data": subsidies})

            # ── Step A ───────────────────────────────────
            yield _sse("progress", {"step": "step_a", "message": "동종업계 벤치마크 분석 중...", "pct": 30})
            step_a = await loop.run_in_executor(
                None, lambda: _diagnostic.run_step_a(profile)
            )
            yield _sse("step_result", {"step": "step_a", "data": step_a})

            # ── Step B ───────────────────────────────────
            yield _sse("progress", {"step": "step_b", "message": "AI 우선순위 도출 중 (Claude 분석)...", "pct": 55})
            step_b = await loop.run_in_executor(
                None, lambda: _diagnostic.run_step_b(profile, step_a)
            )
            yield _sse("step_result", {"step": "step_b", "data": {
                "ai_priorities":  step_b.get("ai_priorities", []),
                "rag_sources":    step_b.get("rag_sources", []),
                "decision_trace": step_b.get("decision_trace"),
            }})

            # 재매칭 (AI 유형 반영)
            ai_priorities = step_b.get("ai_priorities", [])
            if ai_priorities:
                subsidies = await loop.run_in_executor(
                    None, lambda: _matching.match(profile, ai_priorities, top_n=100)
                )

            # ── Step C ───────────────────────────────────
            yield _sse("progress", {"step": "step_c", "message": "ROI 시뮬레이션 계산 중...", "pct": 80})
            step_c = await loop.run_in_executor(
                None,
                lambda: _diagnostic.run_step_c(
                    profile,
                    step_a.get("peer_data") or {},
                    ai_priorities,
                    subsidies,
                ),
            )
            roi_results = [r.to_dict() for r in step_c.get("roi_results", [])]
            yield _sse("step_result", {"step": "step_c", "data": {"roi_results": roi_results}})

            # ── 캐시 저장 ────────────────────────────────
            report_id = str(uuid4())
            report_cache[report_id] = {
                "company":                profile,
                "industry_name":          INDUSTRY_NAMES.get(profile["industry_code"], profile["industry_code"]),
                "peer_data":              step_a.get("peer_data") or {},
                "gap_analysis":           step_a.get("gap_analysis", {}),
                "improvement_priorities": step_a.get("improvement_priorities", []),
                "industry_weather":       step_a.get("industry_weather"),
                "peer_ranking":           step_a.get("peer_ranking"),
                "ai_priorities":          ai_priorities,
                "roi_results":            roi_results,
                "subsidies":              subsidies,
                "rag_sources":            step_b.get("rag_sources", []),
                "decision_trace":         step_b.get("decision_trace"),
            }
            yield _sse("complete", {"report_id": report_id, "pct": 100})

        except Exception as exc:
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
