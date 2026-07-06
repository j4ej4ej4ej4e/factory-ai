'use client'

import type { DecisionTrace as DecisionTraceType } from '@/lib/types'

interface Props {
  trace: DecisionTraceType | null | undefined
}

export default function DecisionTrace({ trace }: Props) {
  if (!trace) return null

  const hasPainPoints = trace.pain_point_mappings.length > 0

  return (
    <div className="card">
      <h3 className="section-title">🔍 판단 근거 트레이스 — 왜 이렇게 추천했나</h3>
      <p className="text-xs text-gray-500 mb-4">
        블랙박스로 결과만 던지지 않고, AI가 어떤 규칙과 근거를 거쳐 이 추천에 도달했는지 그대로 보여드립니다.
      </p>

      <div className="space-y-3">
        {/* STEP 1: 입력 */}
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold shrink-0">1</div>
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-700">사장님이 체크한 현장 문제</div>
            {hasPainPoints ? (
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {trace.pain_point_mappings.map((m, i) => (
                  <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">
                    {m.pain_point_label}
                  </span>
                ))}
              </div>
            ) : (
              <div className="text-xs text-gray-400 mt-1">체크된 문제 없음 — 업종 기본 추천으로 진행</div>
            )}
          </div>
        </div>

        <div className="ml-3.5 border-l-2 border-dashed border-gray-200 h-4" />

        {/* STEP 2: 규칙 매핑 */}
        {hasPainPoints && (
          <>
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold shrink-0">2</div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-700">규칙 기반 매핑 (룰 엔진 — LLM 아님)</div>
                <div className="space-y-1 mt-1.5">
                  {trace.pain_point_mappings.map((m, i) => (
                    <div key={i} className="text-xs text-gray-600 flex items-center gap-1.5 flex-wrap">
                      <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">{m.pain_point_label}</span>
                      <span className="text-gray-400">→</span>
                      {m.mapped_ai_names.map((name, j) => (
                        <span key={j} className="bg-green-50 text-green-700 px-1.5 py-0.5 rounded">{name}</span>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="ml-3.5 border-l-2 border-dashed border-gray-200 h-4" />
          </>
        )}

        {/* STEP 3: 업종 기본 추천 (보조) */}
        {trace.industry_default_ai.ai_names.length > 0 && (
          <>
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-gray-300 text-white flex items-center justify-center text-xs font-bold shrink-0">+</div>
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-700">업종 기본 추천 (보조 후보)</div>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {trace.industry_default_ai.ai_names.map((name, i) => (
                    <span key={i} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full">{name}</span>
                  ))}
                </div>
              </div>
            </div>
            <div className="ml-3.5 border-l-2 border-dashed border-gray-200 h-4" />
          </>
        )}

        {/* STEP 4: 최종 후보 순서 */}
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold shrink-0">3</div>
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-700">최종 후보 순서 (pain point 우선)</div>
            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
              {trace.priority_order.ai_names.map((name, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  <span className="text-xs bg-navy text-white px-2 py-1 rounded-full font-medium">{i + 1}. {name}</span>
                  {i < trace.priority_order.ai_names.length - 1 && <span className="text-gray-300">·</span>}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="ml-3.5 border-l-2 border-dashed border-gray-200 h-4" />

        {/* STEP 5: RAG 검색 */}
        <div className="flex items-start gap-3">
          <div className="w-7 h-7 rounded-full bg-brand text-white flex items-center justify-center text-xs font-bold shrink-0">4</div>
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-700">실시간 웹 검색 근거 수집</div>
            <div className="text-xs text-gray-500 mt-1">
              <span className="bg-navy text-white px-2 py-0.5 rounded-full font-medium">{trace.rag_query_ai_name}</span>
              {' '}키워드로 Naver·Tavily 실시간 검색 → 성공사례·실패사례 균형 수집 → LLM이 그 근거로 최종 Top3 확정 (아래 &quot;AI 분석 참고 자료&quot; 참고)
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
