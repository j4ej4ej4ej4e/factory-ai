'use client'

import { useEffect, useRef, useState } from 'react'
import type { CompanyProfile, AIPriority } from '@/lib/types'

interface SimResult {
  ai_name: string
  total_annual_savings: string
  payback_months: string
  three_year_profit: string
  roi_pct: string
}

interface Defaults {
  labor_reduction_rate: number
  energy_reduction_rate: number
  operating_rate_gain_pp: number
  operating_rate_baseline: number | null
}

interface Props {
  company: CompanyProfile
  aiPriorities: AIPriority[]
}

function parseMonths(s?: string): number | null {
  if (!s) return null
  const n = parseFloat(s)
  return isNaN(n) ? null : n
}

function debounce<T extends (...args: never[]) => void>(fn: T, ms: number) {
  let t: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(t)
    t = setTimeout(() => fn(...args), ms)
  }
}

export default function ROISimulatorPanel({ company, aiPriorities }: Props) {
  const [selected, setSelected] = useState(0)
  const [laborRate, setLaborRate] = useState(8)
  const [energyRate, setEnergyRate] = useState(10)
  const [operatingGainPp, setOperatingGainPp] = useState(5)
  const [defaults, setDefaults] = useState<Defaults | null>(null)
  const [result, setResult] = useState<SimResult | null>(null)
  const [loading, setLoading] = useState(false)

  const ai = aiPriorities[selected]
  const debouncedSimulate = useRef(
    debounce((body: Record<string, unknown>) => simulate(body), 300)
  ).current

  async function simulate(body: Record<string, unknown>) {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/roi-simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) return
      const data = await res.json()
      if (data.defaults) {
        setDefaults(data.defaults)
        if (body.labor_reduction_rate === undefined) {
          setLaborRate(Math.round(data.defaults.labor_reduction_rate * 100))
          setEnergyRate(Math.round(data.defaults.energy_reduction_rate * 100))
          setOperatingGainPp(data.defaults.operating_rate_gain_pp)
        }
      }
      setResult(data.results?.[0] ?? null)
    } catch {
      // 서버 미기동 등 — 조용히 무시 (진단 결과는 이미 있으므로 시뮬레이터만 비활성)
    } finally {
      setLoading(false)
    }
  }

  const baseBody = () => ({
    industry_code:      company.industry_code,
    company_size:        company.company_size,
    headcount:            company.headcount,
    annual_revenue:      company.annual_revenue,
    annual_production:  company.annual_production,
    operating_rate:      company.operating_rate,
    ai_type:              ai?.ai_type,
    estimated_cost:      ai?.estimated_cost,
    co_funding_rate:      0.5,
  })

  // 최초 로드 + AI 유형 변경 시 — 기본값으로 재계산
  useEffect(() => {
    if (!ai) return
    simulate(baseBody())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  // 슬라이더 3개 중 방금 바뀐 값만 반영하고 나머지는 현재 state 유지
  const handleSlider = (setter: (v: number) => void) => (v: number) => {
    setter(v)
    const isLabor  = setter === setLaborRate
    const isEnergy = setter === setEnergyRate
    debouncedSimulate({
      ...baseBody(),
      labor_reduction_rate:   (isLabor  ? v : laborRate) / 100,
      energy_reduction_rate:  (isEnergy ? v : energyRate) / 100,
      operating_rate_gain_pp:  !isLabor && !isEnergy ? v : operatingGainPp,
    })
  }

  if (!aiPriorities.length) return null

  return (
    <div className="card">
      <h3 className="section-title">🕒 회수 타이머 — 가상 시나리오 시뮬레이터</h3>
      <p className="text-xs text-gray-500 mb-4">
        가정치(절감률·가동률 개선폭)를 직접 조정하며 ROI가 실시간으로 어떻게 바뀌는지 확인하세요.
        {defaults?.operating_rate_baseline != null && (
          <> 가동률 기준선 <b>{defaults.operating_rate_baseline}%</b>는 KICOX 실측 동종평균입니다.</>
        )}
      </p>

      {aiPriorities.length > 1 && (
        <div className="flex gap-2 mb-4">
          {aiPriorities.map((p, i) => (
            <button
              key={i}
              onClick={() => setSelected(i)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                selected === i ? 'bg-brand text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}
            >
              {p.ai_name}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-5">
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>인건비 절감률</span><span className="font-medium text-gray-700">{laborRate}%</span>
          </div>
          <input type="range" min={0} max={30} value={laborRate}
            onChange={e => handleSlider(setLaborRate)(Number(e.target.value))}
            className="w-full accent-brand" />
        </div>
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>에너지 절감률</span><span className="font-medium text-gray-700">{energyRate}%</span>
          </div>
          <input type="range" min={0} max={30} value={energyRate}
            onChange={e => handleSlider(setEnergyRate)(Number(e.target.value))}
            className="w-full accent-brand" />
        </div>
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>가동률 개선폭</span><span className="font-medium text-gray-700">{operatingGainPp}%p</span>
          </div>
          <input type="range" min={0} max={20} value={operatingGainPp}
            onChange={e => handleSlider(setOperatingGainPp)(Number(e.target.value))}
            className="w-full accent-brand" />
        </div>
      </div>

      <div className={`grid grid-cols-4 gap-2 transition-opacity ${loading ? 'opacity-50' : 'opacity-100'}`}>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500">연간 절감</div>
          <div className="font-bold text-brand text-sm">{result?.total_annual_savings ?? '-'}</div>
        </div>
        <div className="bg-green-50 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500">투자 회수</div>
          <div className="font-bold text-green-600 text-sm">{result?.payback_months ?? '-'}</div>
        </div>
        <div className="bg-purple-50 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500">3년 순이익</div>
          <div className="font-bold text-purple-600 text-sm">{result?.three_year_profit ?? '-'}</div>
        </div>
        <div className="bg-orange-50 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500">ROI</div>
          <div className="font-bold text-orange-600 text-sm">{result?.roi_pct ?? '-'}</div>
        </div>
      </div>

      {/* 회수 시점 타임라인 — 숫자보다 그림 한 장이 더 직관적 */}
      {(() => {
        const months = parseMonths(result?.payback_months)
        if (months == null) return null
        const HORIZON = 36 // 3년
        const markerPct = Math.min(96, Math.max(2, (months / HORIZON) * 100))
        return (
          <div className="mt-5">
            <div className="flex justify-between text-xs text-gray-500 mb-1.5">
              <span>오늘 투자</span>
              <span className="font-medium text-green-700">
                {months < 1 ? `${(months * 30).toFixed(0)}일 만에 회수` : `${months.toFixed(1)}개월 만에 회수`}
              </span>
              <span>3년 후</span>
            </div>
            <div className="relative w-full h-4 rounded-full overflow-hidden bg-gray-100">
              <div className="absolute inset-y-0 left-0 bg-orange-300" style={{ width: `${markerPct}%` }} />
              <div className="absolute inset-y-0 bg-green-300" style={{ left: `${markerPct}%`, right: 0 }} />
              <div
                className="absolute -top-1 h-6 w-1 bg-gray-800 rounded-full"
                style={{ left: `calc(${markerPct}% - 2px)` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-gray-400 mt-1">
              <span>🟧 투자금 회수 전</span>
              <span>🟩 순이익 구간 (약 {Math.max(0, HORIZON - months).toFixed(0)}개월)</span>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
