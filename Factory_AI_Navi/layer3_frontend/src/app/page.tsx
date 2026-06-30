'use client'

import { useState } from 'react'
import type { CompanyProfile, DiagnosisResult } from '@/lib/types'
import InputForm from '@/components/InputForm'
import DiagnoseProgress from '@/components/DiagnoseProgress'
import ResultDashboard from '@/components/ResultDashboard'

type Step = 'input' | 'diagnosing' | 'result'

export default function HomePage() {
  const [step, setStep] = useState<Step>('input')
  const [profile, setProfile] = useState<CompanyProfile | null>(null)
  const [result, setResult] = useState<(DiagnosisResult & { report_id: string }) | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFormSubmit = (p: CompanyProfile) => {
    setProfile(p)
    setError(null)
    setStep('diagnosing')
  }

  const handleComplete = (r: DiagnosisResult & { report_id: string }) => {
    setResult(r)
    setStep('result')
  }

  const handleError = (msg: string) => {
    setError(msg)
    setStep('input')
  }

  const handleReset = () => {
    setStep('input')
    setProfile(null)
    setResult(null)
    setError(null)
  }

  return (
    <div>
      {/* 단계 표시 바 */}
      <div className="flex items-center justify-center mb-8 gap-0">
        {[
          { label: '기업 정보 입력', step: 'input' },
          { label: 'AI 진단',        step: 'diagnosing' },
          { label: '결과 대시보드',   step: 'result' },
        ].map((s, i, arr) => (
          <div key={s.step} className="flex items-center">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              step === s.step ? 'bg-brand text-white' :
              (step === 'result' && i < 2) || (step === 'diagnosing' && i === 0) ? 'bg-green-100 text-green-700' :
              'bg-gray-100 text-gray-400'
            }`}>
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                step === s.step ? 'bg-white text-brand' :
                (step === 'result' && i < 2) || (step === 'diagnosing' && i === 0) ? 'bg-green-500 text-white' :
                'bg-gray-300 text-gray-500'
              }`}>
                {(step === 'result' && i < 2) || (step === 'diagnosing' && i === 0) ? '✓' : i + 1}
              </span>
              {s.label}
            </div>
            {i < arr.length - 1 && (
              <div className={`w-8 h-0.5 ${
                (step === 'result') || (step === 'diagnosing' && i === 0) ? 'bg-green-400' : 'bg-gray-200'
              }`} />
            )}
          </div>
        ))}
      </div>

      {/* 오류 메시지 */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          <strong>오류:</strong> {error}
        </div>
      )}

      {/* 랜딩 소개 (입력 폼 위) */}
      {step === 'input' && (
        <div className="mb-8 text-center">
          <h2 className="text-3xl font-bold text-navy mb-3">
            AI로 우리 공장의 문제를 진단받으세요
          </h2>
          <p className="text-gray-500 text-base max-w-2xl mx-auto leading-relaxed">
            업종·규모·KPI 입력 → Claude AI가 동종업계 대비 갭 분석 →
            AI 도입 우선순위 + ROI 계산 + 정부지원사업 매칭까지 <strong>한 번에</strong>
          </p>
          <div className="flex justify-center gap-6 mt-4 text-sm text-gray-400">
            <span>📊 KIAT 산업기술통계 기반</span>
            <span>🤖 Claude 3.5 Sonnet 분석</span>
            <span>🏛️ KEIT/NTIS 지원사업 연계</span>
          </div>
        </div>
      )}

      {/* 단계별 컴포넌트 */}
      {step === 'input' && (
        <InputForm onSubmit={handleFormSubmit} />
      )}

      {step === 'diagnosing' && profile && (
        <DiagnoseProgress
          profile={profile}
          onComplete={handleComplete}
          onError={handleError}
        />
      )}

      {step === 'result' && result && (
        <ResultDashboard result={result} onReset={handleReset} />
      )}
    </div>
  )
}
