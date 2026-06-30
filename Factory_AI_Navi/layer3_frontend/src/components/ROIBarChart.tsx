'use client'

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts'
import type { ROIResult } from '@/lib/types'

interface Props {
  roiResults: ROIResult[]
}

const COLORS = ['#2563EB', '#059669', '#D97706']

function parseNum(s?: string): number {
  if (!s) return 0
  const n = parseFloat(s.replace(/[^0-9.\-]/g, ''))
  return isNaN(n) ? 0 : n
}

export default function ROIBarChart({ roiResults }: Props) {
  if (!roiResults.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        ROI 데이터 없음
      </div>
    )
  }

  const data = roiResults.map(r => ({
    name: r.ai_name.replace(/\(.*?\)/g, '').trim().slice(0, 12),
    연간절감액: parseNum(r.total_annual_savings),
    투자회수: parseNum(r.net_investment),
    삼년순이익: parseNum(r.three_year_profit),
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={v => `${(v/10000).toFixed(0)}억`} tick={{ fontSize: 10 }} />
        <Tooltip
          formatter={(v: number, name: string) => [`${v.toLocaleString()}만원`, name]}
        />
        <Legend />
        <Bar dataKey="연간절감액" radius={[4, 4, 0, 0]}>
          {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
        </Bar>
        <Bar dataKey="삼년순이익" fill="#6366F1" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
