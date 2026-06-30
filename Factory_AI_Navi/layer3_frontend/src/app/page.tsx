'use client'

import { useState } from 'react'
import type { CompanyProfile, DiagnosisResult } from '@/lib/types'
import LandingPage from '@/components/LandingPage'
import InputForm from '@/components/InputForm'
import DiagnoseProgress from '@/components/DiagnoseProgress'
import ResultDashboard from '@/components/ResultDashboard'

type Step = 'landing' | 'input' | 'diagnosing' | 'result'

export default function HomePage() {
  const [step, setStep] = useState<Step>('landing')
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
    setStep('landing')
    setProfile(null)
    setResult(null)
    setError(null)
  }

  const PROGRESS_STEPS = [
    { label: '기업 정보 입력', key: 'input' },
    { label: 'AI 진단',       key: 'diagnosing' },
    { label: '결과 대시보드',  key: 'result' },
  ] as const

  return (
    <div>
      {/* 랜딩은 전체 너비 레이아웃 */}
      {step === 'landing' && <LandingPage onStart={() => setStep('input')} />}

      {step !== 'landing' && (
        <>
          {/* 단계 표시 바 */}
          <div className="flex items-center justify-center mb-8 gap-0">
            {PROGRESS_STEPS.map((s, i, arr) => (
              <div key={s.key} className="flex items-center">
                <div className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  step === s.key ? 'bg-brand text-white' :
                  (step === 'result' && i < 2) || (step === 'diagnosing' && i === 0) ? 'bg-green-100 text-green-700' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold ${
                    step === s.key ? 'bg-white text-brand' :
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
        </>
      )}
    </div>
  )
}
