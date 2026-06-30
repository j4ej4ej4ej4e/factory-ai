'use client'

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Legend, Tooltip,
} from 'recharts'
import type { GapEntry } from '@/lib/types'

interface Props {
  gapAnalysis: Record<string, GapEntry>
}

const LABEL_MAP: Record<string, string> = {
  defect_rate:       '불량률↓',
  operating_rate:    '가동률',
  energy_cost_ratio: '에너지↓',
}

function normalize(key: string, val: number): number {
  if (key === 'defect_rate' || key === 'energy_cost_ratio') {
    return Math.max(0, 100 - val * 5)
  }
  return Math.min(100, val)
}

export default function BenchmarkRadar({ gapAnalysis }: Props) {
  const keys = Object.keys(gapAnalysis).filter(k => k !== 'ai_adoption_rate')

  if (keys.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        벤치마크 데이터 없음
      </div>
    )
  }

  const data = keys.map(k => {
    const g = gapAnalysis[k]
    return {
      label: LABEL_MAP[k] ?? g.label,
      귀사:   normalize(k, g.company),
      업종평균: normalize(k, g.peer_avg),
    }
  })

  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid />
        <PolarAngleAxis dataKey="label" tick={{ fontSize: 12 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
        <Radar
          name="귀사" dataKey="귀사"
          stroke="#2563EB" fill="#2563EB" fillOpacity={0.3}
        />
        <Radar
          name="업종 평균" dataKey="업종평균"
          stroke="#9CA3AF" fill="#9CA3AF" fillOpacity={0.15}
        />
        <Legend />
        <Tooltip />
      </RadarChart>
    </ResponsiveContainer>
  )
}
