'use client'

import type { DiagnosisResult } from '@/lib/types'
import BenchmarkRadar from './BenchmarkRadar'
import IndustryWeather from './IndustryWeather'
import PeerRanking from './PeerRanking'
import ROIBarChart from './ROIBarChart'
import ROISimulatorPanel from './ROISimulatorPanel'
import SubsidyCalendar from './SubsidyCalendar'
import SubsidyTable from './SubsidyTable'

interface Props {
  result: DiagnosisResult & { report_id: string }
  onReset: () => void
}

const GAP_ASSESS_COLOR = (assessment: string | undefined) => {
  if (!assessment) return 'text-gray-600 bg-gray-50'
  if (assessment.includes('개선 필요') || assessment.includes('열위')) return 'text-red-600 bg-red-50'
  if (assessment.includes('양호') || assessment.includes('우수')) return 'text-green-600 bg-green-50'
  return 'text-gray-600 bg-gray-50'
}

export default function ResultDashboard({ result, onReset }: Props) {
  const {
    report_id, industry_name, company, gap_analysis, ai_priorities,
    roi_results, subsidies, rag_sources, industry_weather, peer_ranking,
  } = result

  const handleDownloadPDF = () => {
    window.open(`/api/v1/report/${report_id}/pdf`, '_blank')
  }

  return (
    <div className="space-y-6">
      {/* 상단 배너 */}
      <div className="bg-gradient-to-r from-navy to-brand rounded-xl p-6 text-white">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold mb-1">AI 공정 진단 완료</h2>
            <p className="text-blue-200 text-sm">
              {industry_name} | {company.company_size === 'small' ? '소기업' : '중기업'} ({company.headcount}인)
            </p>
          </div>
          <div className="flex gap-3">
            <button onClick={handleDownloadPDF} className="btn-outline bg-white/10 border-white/30 text-white hover:bg-white/20 text-sm">
              PDF 다운로드
            </button>
            <button onClick={onReset} className="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-lg text-sm transition-colors">
              새 진단
            </button>
          </div>
        </div>
      </div>

      {/* 업종 날씨예보 + 동종업계 순위 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <IndustryWeather weather={industry_weather} />
        <PeerRanking ranking={peer_ranking} />
      </div>

      {/* 섹션 1: 벤치마크 갭 분석 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">📊 동종업계 벤치마크 분석</h3>
          <BenchmarkRadar gapAnalysis={gap_analysis ?? {}} />
        </div>

        <div className="card">
          <h3 className="section-title">📋 갭 분석 결과</h3>
          <div className="space-y-3">
            {Object.entries(gap_analysis ?? {}).map(([key, g]) => (
              <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-gray-50">
                <div>
                  <div className="text-sm font-medium">{g.label}</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    귀사 {g.company}{g.unit} / 업종평균 {g.peer_avg}{g.unit}
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${GAP_ASSESS_COLOR(g.assessment)}`}>
                  {g.assessment}
                </span>
              </div>
            ))}
            {Object.keys(gap_analysis ?? {}).length === 0 && (
              <div className="text-center text-gray-400 text-sm py-4">
                KPI 입력 시 갭 분석이 표시됩니다
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 섹션 2: AI 적용 우선순위 */}
      <div className="card">
        <h3 className="section-title">🤖 AI 적용 우선순위 Top3</h3>
        {!ai_priorities?.length ? (
          <div className="text-center text-gray-400 text-sm py-4">AI 분석 결과 없음</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {ai_priorities.map((p, i) => (
              <div key={i} className={`rounded-xl p-5 border-2 ${
                i === 0 ? 'border-brand bg-blue-50' :
                i === 1 ? 'border-green-400 bg-green-50' :
                'border-orange-400 bg-orange-50'
              }`}>
                <div className={`text-xs font-bold mb-2 px-2 py-0.5 rounded-full inline-block ${
                  i === 0 ? 'bg-brand text-white' :
                  i === 1 ? 'bg-green-500 text-white' :
                  'bg-orange-500 text-white'
                }`}>
                  #{p.rank} 우선순위
                </div>
                <h4 className="font-bold text-gray-800 mb-3">{p.ai_name}</h4>
                <div className="space-y-2 text-sm">
                  <div><span className="text-gray-500">적용 공정:</span> {p.target_process}</div>
                  <div><span className="text-gray-500">기대 효과:</span> {p.expected_effect}</div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">구현 기간: {p.implementation_period}</span>
                    <span className="font-medium text-brand">{p.estimated_cost?.toLocaleString()}만원</span>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
                  {p.rationale}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 섹션 3: ROI */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">💰 ROI 시뮬레이션</h3>
          <ROIBarChart roiResults={roi_results ?? []} />
        </div>

        <div className="card">
          <h3 className="section-title">📈 ROI 수치 상세</h3>
          <div className="space-y-3">
            {(roi_results ?? []).map((r, i) => (
              <div key={i} className="p-3 rounded-lg border border-gray-100 hover:border-brand transition-colors">
                <div className="font-medium text-sm mb-2">{r.ai_name}</div>
                <div className="grid grid-cols-3 gap-2 text-xs text-center">
                  <div className="bg-blue-50 rounded p-2">
                    <div className="text-gray-500">연간 절감</div>
                    <div className="font-bold text-brand">{r.total_annual_savings}</div>
                  </div>
                  <div className="bg-green-50 rounded p-2">
                    <div className="text-gray-500">투자 회수</div>
                    <div className="font-bold text-green-600">{r.payback_months}</div>
                  </div>
                  <div className="bg-purple-50 rounded p-2">
                    <div className="text-gray-500">3년 순이익</div>
                    <div className="font-bold text-purple-600">{r.three_year_profit}</div>
                  </div>
                </div>
              </div>
            ))}
            {!(roi_results?.length) && (
              <div className="text-center text-gray-400 text-sm py-4">ROI 데이터 없음</div>
            )}
          </div>
        </div>
      </div>

      {/* 섹션 3-1: 인터랙티브 ROI 시뮬레이터 */}
      {ai_priorities?.length > 0 && (
        <ROISimulatorPanel company={company} aiPriorities={ai_priorities} />
      )}

      {/* 섹션 4: 지원사업 */}
      <div className="card">
        <h3 className="section-title">📅 지원금 마감 캘린더</h3>
        <SubsidyCalendar subsidies={subsidies ?? []} company={company} />
      </div>

      <div className="card">
        <h3 className="section-title">🏛️ 추천 정부지원사업 Top5</h3>
        <SubsidyTable subsidies={(subsidies ?? []).slice(0, 5)} />
      </div>

      {/* 섹션 5: RAG 출처 */}
      {rag_sources?.length > 0 && (
        <div className="card">
          <h3 className="section-title">🔗 AI 분석 참고 자료</h3>
          <div className="space-y-2">
            {rag_sources.map((s, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full min-w-fit">
                  {s.relevance_score != null ? `관련도 ${s.relevance_score.toFixed(1)}` : `#${i+1}`}
                </span>
                {s.case_type && (
                  <span className={`text-xs px-2 py-0.5 rounded-full min-w-fit font-medium ${
                    s.case_type === '실패사례·주의점' ? 'bg-red-100 text-red-700' :
                    s.case_type === '성공사례' ? 'bg-green-100 text-green-700' :
                    'bg-blue-50 text-blue-600'
                  }`}>
                    {s.case_type}
                  </span>
                )}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                    className="text-brand hover:underline truncate"
                  >
                    {s.title ?? s.url}
                  </a>
                ) : (
                  <span className="text-gray-600 truncate">{s.title ?? '-'}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
