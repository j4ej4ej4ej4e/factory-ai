'use client'

import { useState } from 'react'
import type { CompanyProfile } from '@/lib/types'

// ⚠️ 이 목록은 반드시 DB에 실제 시드된 12개 업종(kiat_industry_stats)과
// 정확히 일치해야 함 — 하나라도 다르면 "벤치마크 데이터 없음"으로 빈 결과가 뜬다.
const INDUSTRY_OPTIONS = [
  { value: 'C243', label: 'C243 주조업 (뿌리)' },
  { value: 'C251', label: 'C251 금형 제조업 (뿌리)' },
  { value: 'C259', label: 'C259 소성가공업 (뿌리)' },
  { value: 'C289', label: 'C289 용접업 (뿌리)' },
  { value: 'C301', label: 'C301 표면처리업 (뿌리)' },
  { value: 'C302', label: 'C302 열처리업 (뿌리)' },
  { value: 'C10',  label: 'C10 식료품 제조업' },
  { value: 'C22',  label: 'C22 사출성형(고무·플라스틱) 제조업' },
  { value: 'C25',  label: 'C25 금속가공제품 제조업' },
  { value: 'C26',  label: 'C26 전자부품·컴퓨터·영상·통신 제조업' },
  { value: 'C29',  label: 'C29 기타 기계 및 장비(산업기계) 제조업' },
  { value: 'C30',  label: 'C30 자동차 및 트레일러 제조업' },
]

// ⚠️ value는 반드시 layer2_ai/constants.py의 PAIN_POINT_TO_AI 키와 정확히
// 일치해야 함 — 하나라도 다르면 그 체크박스는 AI 우선순위 결정에 전혀
// 반영되지 않고 조용히 무시된다 (매핑 실패 시 에러 없이 빈 결과 반환).
const PAIN_POINT_OPTIONS = [
  { value: 'defect_high',           label: '불량률이 높음' },
  { value: 'equipment_breakdown',   label: '설비 고장이 잦음' },
  { value: 'energy_cost',           label: '에너지 비용이 높음' },
  { value: 'quality_inconsistency', label: '품질 균일성이 떨어짐' },
  { value: 'delivery_delay',        label: '납기 지연이 잦음' },
  { value: 'labor_shortage',        label: '인력 부족·인건비 부담' },
  { value: 'material_waste',        label: '재료비·폐기물 과다' },
]

interface Props {
  onSubmit: (profile: CompanyProfile) => void
  loading?: boolean
}

export default function InputForm({ onSubmit, loading }: Props) {
  const [form, setForm] = useState<Partial<CompanyProfile>>({
    industry_code: 'C25',
    company_size: 'small',
    headcount: 35,
    annual_revenue: 150000,
    annual_production: 130000,
    defect_rate: 5.1,
    operating_rate: 60,
    energy_cost_ratio: 11,
    equipment_age: 8,
    pain_points: [],
  })

  const set = (key: string, value: unknown) =>
    setForm(prev => ({ ...prev, [key]: value }))

  const togglePainPoint = (v: string) => {
    const cur = form.pain_points ?? []
    set('pain_points', cur.includes(v) ? cur.filter(x => x !== v) : [...cur, v])
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.industry_code || !form.company_size || !form.headcount) return
    onSubmit(form as CompanyProfile)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 기업 기본 정보 */}
      <div className="card">
        <h2 className="section-title">
          <span className="w-7 h-7 bg-brand text-white rounded-full text-xs flex items-center justify-center font-bold">1</span>
          기업 기본 정보
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="md:col-span-2">
            <label className="label">업종 선택 *</label>
            <select
              className="input"
              value={form.industry_code}
              onChange={e => set('industry_code', e.target.value)}
              required
            >
              {INDUSTRY_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">기업 규모 *</label>
            <div className="flex gap-4 pt-2">
              {[
                { v: 'small', l: '소기업 (50인 미만)' },
                { v: 'medium', l: '중기업 (50~300인)' },
              ].map(({ v, l }) => (
                <label key={v} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="company_size"
                    value={v}
                    checked={form.company_size === v}
                    onChange={() => set('company_size', v)}
                    className="accent-brand"
                  />
                  <span className="text-sm">{l}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="label">종업원 수 *</label>
            <input
              type="number" className="input" min={1} required
              value={form.headcount}
              onChange={e => set('headcount', Number(e.target.value))}
              placeholder="예: 35"
            />
          </div>

          <div>
            <label className="label">연간 매출액 (만원) *</label>
            <input
              type="number" className="input" min={1} required
              value={form.annual_revenue}
              onChange={e => set('annual_revenue', Number(e.target.value))}
              placeholder="예: 150000"
            />
          </div>

          <div>
            <label className="label">연간 생산액 (만원) *</label>
            <input
              type="number" className="input" min={1} required
              value={form.annual_production}
              onChange={e => set('annual_production', Number(e.target.value))}
              placeholder="예: 130000"
            />
          </div>
        </div>
      </div>

      {/* 현재 KPI */}
      <div className="card">
        <h2 className="section-title">
          <span className="w-7 h-7 bg-brand text-white rounded-full text-xs flex items-center justify-center font-bold">2</span>
          현재 생산 KPI <span className="text-sm font-normal text-gray-400">(선택 — 미입력 시 업종 평균 사용)</span>
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { key: 'defect_rate',       label: '불량률 (%)',        placeholder: '예: 5.1' },
            { key: 'operating_rate',    label: '설비 가동률 (%)',    placeholder: '예: 60' },
            { key: 'energy_cost_ratio', label: '에너지 비용 비율 (%)', placeholder: '예: 11' },
            { key: 'equipment_age',     label: '설비 노후도 (년)',   placeholder: '예: 8' },
          ].map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="label">{label}</label>
              <input
                type="number" className="input" step="0.1" min={0}
                value={(form as Record<string, unknown>)[key] as number ?? ''}
                onChange={e => set(key, e.target.value ? Number(e.target.value) : undefined)}
                placeholder={placeholder}
              />
            </div>
          ))}
        </div>
      </div>

      {/* 주요 문제점 */}
      <div className="card">
        <h2 className="section-title">
          <span className="w-7 h-7 bg-brand text-white rounded-full text-xs flex items-center justify-center font-bold">3</span>
          주요 문제점 (복수 선택)
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {PAIN_POINT_OPTIONS.map(({ value, label }) => {
            const checked = (form.pain_points ?? []).includes(value)
            return (
              <label
                key={value}
                className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer text-sm transition-colors
                  ${checked ? 'border-brand bg-blue-50 text-brand font-medium' : 'border-gray-200 hover:border-gray-300'}`}
              >
                <input
                  type="checkbox" className="accent-brand"
                  checked={checked}
                  onChange={() => togglePainPoint(value)}
                />
                {label}
              </label>
            )
          })}
        </div>
      </div>

      <div className="flex justify-center pt-2">
        <button type="submit" className="btn-primary w-full max-w-md text-base py-4" disabled={loading}>
          {loading ? '분석 중...' : 'AI 공정 진단 시작하기'}
        </button>
      </div>
    </form>
  )
}
