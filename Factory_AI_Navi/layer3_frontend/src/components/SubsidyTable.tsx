'use client'

import type { Subsidy } from '@/lib/types'

interface Props {
  subsidies: Subsidy[]
}

export default function SubsidyTable({ subsidies }: Props) {
  if (!subsidies.length) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        검색된 지원사업이 없습니다.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-navy text-white">
            <th className="px-4 py-3 text-left font-medium rounded-tl-lg">#</th>
            <th className="px-4 py-3 text-left font-medium">사업명</th>
            <th className="px-4 py-3 text-right font-medium">최대 지원금</th>
            <th className="px-4 py-3 text-right font-medium">자부담</th>
            <th className="px-4 py-3 text-center font-medium rounded-tr-lg">마감일</th>
          </tr>
        </thead>
        <tbody>
          {subsidies.map((s, i) => (
            <tr
              key={i}
              className={`border-b border-gray-100 hover:bg-blue-50 transition-colors ${i % 2 === 1 ? 'bg-gray-50' : ''}`}
            >
              <td className="px-4 py-3 text-gray-500">{i + 1}</td>
              <td className="px-4 py-3">
                <div className="font-medium text-gray-800">{s.program_name}</div>
                <div className="flex gap-1 mt-1">
                  {s.urgency_label && (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                      {s.urgency_label}
                    </span>
                  )}
                  {s.is_roots_priority && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">
                      뿌리업종 우선
                    </span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3 text-right font-medium text-brand">
                {s.support_amount_label ?? (
                  s.max_support_amount ? `${s.max_support_amount.toLocaleString()}만원` : '-'
                )}
              </td>
              <td className="px-4 py-3 text-right text-gray-600">
                {s.co_funding_rate != null ? `${(s.co_funding_rate * 100).toFixed(0)}%` : '-'}
              </td>
              <td className="px-4 py-3 text-center">
                <span className={`text-xs px-2 py-1 rounded-full ${
                  s.urgency_label?.includes('긴급') ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {s.application_end ?? '-'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
