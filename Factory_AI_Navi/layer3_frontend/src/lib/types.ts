// Layer 3 Frontend — 공통 TypeScript 타입 정의

export interface CompanyProfile {
  industry_code: string
  company_size: 'small' | 'medium'
  headcount: number
  annual_revenue: number
  annual_production: number
  defect_rate?: number
  operating_rate?: number
  energy_cost_ratio?: number
  equipment_age?: number
  production_per_person?: number
  pain_points: string[]
}

export interface GapEntry {
  label: string
  company: number
  peer_avg: number
  gap_pp?: number
  gap_pct?: number
  unit: string
  assessment: string
  is_estimate?: boolean
}

export interface AIPriority {
  rank: number
  ai_type: string
  ai_name: string
  target_process: string
  expected_effect: string
  implementation_period: string
  estimated_cost: number
  rationale: string
}

export interface ROIResult {
  ai_type: string
  ai_name: string
  implementation_cost: string
  net_investment: string
  labor_savings: string
  energy_savings: string
  operating_uplift_savings: string
  total_annual_savings: string
  payback_months: string
  three_year_profit: string
  roi_pct: string
  implementation_cost_raw?: number
  net_investment_raw?: number
  total_annual_savings_raw?: number
  three_year_profit_raw?: number
}

export interface Subsidy {
  program_name: string
  agency: string
  max_support_amount?: number
  co_funding_rate?: number
  application_end?: string
  urgency_label?: string
  support_amount_label?: string
  is_roots_priority?: boolean
  is_industry_specific?: boolean
  apply_url?: string
  description?: string
}

export interface RAGSource {
  url?: string
  title?: string
  relevance_score?: number
  case_type?: '성공사례' | '실패사례·주의점' | '일반정보'
}

export interface IndustryWeather {
  icon: string
  label: string
  message: string
  energy_warning?: string | null
  basis?: string | null
}

export interface PeerRanking {
  percentile: number | null
  sample_size: number
  min_sample_size: number
}

export interface DiagnosisResult {
  report_id: string
  industry_name: string
  company: CompanyProfile
  peer_data: Record<string, unknown>
  gap_analysis: Record<string, GapEntry>
  improvement_priorities: string[]
  industry_weather?: IndustryWeather | null
  peer_ranking?: PeerRanking | null
  ai_priorities: AIPriority[]
  roi_results: ROIResult[]
  subsidies: Subsidy[]
  rag_sources: RAGSource[]
}

export interface SSEProgress {
  step: string
  message: string
  pct: number
}

export interface SSEStepResult {
  step: string
  data: unknown
}
