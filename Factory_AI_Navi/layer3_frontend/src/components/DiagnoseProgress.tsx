'use client'

import { useEffect, useRef, useState } from 'react'
import type { CompanyProfile, DiagnosisResult, AIPriority, Subsidy } from '@/lib/types'

const STEPS = [
  { id: 'matching', label: '지원사업 매칭',      icon: '🔍' },
  { id: 'step_a',   label: '벤치마크 갭 분석',   icon: '📊' },
  { id: 'step_b',   label: 'AI 우선순위 도출',   icon: '🤖' },
  { id: 'step_c',   label: 'ROI 시뮬레이션',     icon: '💰' },
]

interface StepState {
  status: 'pending' | 'running' | 'done' | 'error'
  message?: string
  pct?: number
}

interface Props {
  profile: CompanyProfile
  onComplete: (result: DiagnosisResult & { report_id: string }) => void
  onError: (msg: string) => void
}

export default function DiagnoseProgress({ profile, onComplete, onError }: Props) {
  const [steps, setSteps] = useState<Record<string, StepState>>(
    Object.fromEntries(STEPS.map(s => [s.id, { status: 'pending' }]))
  )
  const [logs, setLogs] = useState<string[]>([])
  const [totalPct, setTotalPct] = useState(0)
  const accRef = useRef<Partial<DiagnosisResult>>({})

  // 실제 진행률(targetPct)과 화면에 보여줄 진행률(totalPct)을 분리해서
  // 부드럽게 채워지는 것처럼 보이게 함 — 백엔드 응답이 몰아서 빨리 오면
  // (예: LLM 실패로 폴백이 즉시 처리되는 경우) 게이지가 순간이동하는 걸 방지
  const targetPctRef = useRef(0)
  const displayPctRef = useRef(0)

  useEffect(() => {
    let raf: number
    const tick = () => {
      const diff = targetPctRef.current - displayPctRef.current
      if (Math.abs(diff) > 0.4) {
        displayPctRef.current += diff * 0.12
      } else {
        displayPctRef.current = targetPctRef.current
      }
      setTotalPct(Math.round(displayPctRef.current))
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  const addLog = (msg: string) =>
    setLogs(prev => [...prev.slice(-19), `${new Date().toLocaleTimeString()} ${msg}`])

  const setStep = (id: string, state: Partial<StepState>) =>
    setSteps(prev => ({ ...prev, [id]: { ...prev[id], ...state } }))

  useEffect(() => {
    const ctrl = new AbortController()

    async function run() {
      addLog('진단을 시작합니다...')

      let res: Response
      try {
        res = await fetch('/api/v1/diagnose', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(profile),
          signal: ctrl.signal,
        })
      } catch (e: unknown) {
        if ((e as Error).name !== 'AbortError') {
          onError('서버 연결 실패. FastAPI가 실행 중인지 확인하세요.')
        }
        return
      }

      if (!res.ok || !res.body) {
        onError(`API 오류: ${res.status}`)
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        let done: boolean, value: Uint8Array | undefined
        try {
          const result = await reader.read()
          done = result.done
          value = result.value
        } catch (e: unknown) {
          if ((e as Error).name === 'AbortError') return
          throw e
        }
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          const eventMatch = part.match(/^event: (\w+)/)
          const dataMatch = part.match(/^data: (.+)/m)
          if (!eventMatch || !dataMatch) continue

          const event = eventMatch[1]
          let data: Record<string, unknown>
          try {
            data = JSON.parse(dataMatch[1])
          } catch { continue }

          if (event === 'progress') {
            const { step, message, pct } = data as { step: string; message: string; pct: number }
            setStep(step, { status: 'running', message, pct })
            targetPctRef.current = pct
            addLog(message)

          } else if (event === 'step_result') {
            const { step, data: stepData } = data as { step: string; data: unknown }
            setStep(step, { status: 'done' })

            if (step === 'matching') {
              accRef.current.subsidies = stepData as Subsidy[]
            } else if (step === 'step_a') {
              const d = stepData as Record<string, unknown>
              accRef.current.peer_data = d.peer_data as Record<string, unknown>
              accRef.current.gap_analysis = d.gap_analysis as DiagnosisResult['gap_analysis']
              accRef.current.improvement_priorities = d.improvement_priorities as string[]
              accRef.current.industry_weather = d.industry_weather as DiagnosisResult['industry_weather']
              accRef.current.peer_ranking = d.peer_ranking as DiagnosisResult['peer_ranking']
            } else if (step === 'step_b') {
              const d = stepData as Record<string, unknown>
              accRef.current.ai_priorities = d.ai_priorities as AIPriority[]
              accRef.current.rag_sources = d.rag_sources as DiagnosisResult['rag_sources']
              accRef.current.decision_trace = d.decision_trace as DiagnosisResult['decision_trace']
            } else if (step === 'step_c') {
              const d = stepData as Record<string, unknown>
              accRef.current.roi_results = (d.roi_results ?? []) as DiagnosisResult['roi_results']
            }

          } else if (event === 'complete') {
            const { report_id } = data as { report_id: string }
            targetPctRef.current = 100
            addLog('진단 완료!')
            // 게이지가 실제로 100%까지 차오르는 걸 눈으로 볼 시간을 준 뒤 화면 전환
            await new Promise(resolve => setTimeout(resolve, 500))
            onComplete({ ...accRef.current, report_id, company: profile } as DiagnosisResult & { report_id: string })

          } else if (event === 'error') {
            onError((data as { message: string }).message)
          }
        }
      }
    }

    run()
    return () => ctrl.abort()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      {/* 전체 진행률 */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-bold text-navy text-lg">AI 진단 진행 중...</h2>
          <span className="text-brand font-bold text-xl">{totalPct}%</span>
        </div>
        <div className="w-full bg-gray-100 rounded-full h-3">
          <div
            className="bg-brand h-3 rounded-full transition-[width] duration-100 ease-linear"
            style={{ width: `${totalPct}%` }}
          />
        </div>
      </div>

      {/* 단계별 상태 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {STEPS.map(step => {
          const state = steps[step.id]
          return (
            <div
              key={step.id}
              className={`card text-center transition-all ${
                state.status === 'done'    ? 'border-green-200 bg-green-50' :
                state.status === 'running' ? 'border-brand bg-blue-50 animate-pulse' :
                state.status === 'error'   ? 'border-red-200 bg-red-50' :
                'border-gray-100 opacity-60'
              }`}
            >
              <div className="text-3xl mb-2">{step.icon}</div>
              <div className="text-sm font-medium text-gray-700">{step.label}</div>
              <div className={`text-xs mt-1 font-medium ${
                state.status === 'done'    ? 'text-green-600' :
                state.status === 'running' ? 'text-brand' :
                state.status === 'error'   ? 'text-red-600' :
                'text-gray-400'
              }`}>
                {state.status === 'done'    ? '✓ 완료' :
                 state.status === 'running' ? '분석 중...' :
                 state.status === 'error'   ? '오류' :
                 '대기 중'}
              </div>
            </div>
          )
        })}
      </div>

      {/* 실시간 로그 */}
      <div className="card">
        <h3 className="text-sm font-medium text-gray-500 mb-3">분석 로그</h3>
        <div className="bg-gray-900 rounded-lg p-4 h-40 overflow-y-auto font-mono text-xs text-green-400 space-y-1">
          {logs.map((log, i) => <div key={i}>{log}</div>)}
          {logs.length === 0 && <div className="text-gray-500">초기화 중...</div>}
        </div>
      </div>
    </div>
  )
}
