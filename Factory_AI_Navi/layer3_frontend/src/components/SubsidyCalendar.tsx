'use client'

import { useMemo, useState } from 'react'
import type { Subsidy } from '@/lib/types'

interface Props {
  subsidies: Subsidy[]
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function dayOfMonth(dateStr: string | undefined): number | null {
  if (!dateStr) return null
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return null
  return d.getDate()
}

function isSameMonth(dateStr: string | undefined, year: number, month: number): boolean {
  if (!dateStr) return false
  const d = new Date(dateStr)
  return !isNaN(d.getTime()) && d.getFullYear() === year && d.getMonth() === month
}

export default function SubsidyCalendar({ subsidies }: Props) {
  const today = useMemo(() => new Date(), [])
  const year = today.getFullYear()
  const month = today.getMonth() // 0-indexed

  const [selectedDay, setSelectedDay] = useState<number | null>(today.getDate())

  const byDay = useMemo(() => {
    const map = new Map<number, Subsidy[]>()
    for (const s of subsidies) {
      if (!isSameMonth(s.application_end, year, month)) continue
      const d = dayOfMonth(s.application_end)
      if (d == null) continue
      if (!map.has(d)) map.set(d, [])
      map.get(d)!.push(s)
    }
    return map
  }, [subsidies, year, month])

  const firstWeekday = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (cells.length % 7 !== 0) cells.push(null)

  const selectedItems = selectedDay != null ? (byDay.get(selectedDay) ?? []) : []

  if (!subsidies.length) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm">
        검색된 지원사업이 없습니다.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="font-bold text-navy">{year}년 {month + 1}월 지원금 마감 캘린더</div>
        <div className="flex gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-brand inline-block" />업종전용</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-gray-400 inline-block" />제조업 전체</span>
        </div>
      </div>

      <div className="grid grid-cols-7 text-center text-xs text-gray-400 mb-1">
        {WEEKDAYS.map(w => <div key={w} className="py-1">{w}</div>)}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (day == null) return <div key={i} className="h-16" />
          const items = byDay.get(day) ?? []
          const isToday = day === today.getDate()
          const isPast = day < today.getDate()
          const isSelected = day === selectedDay

          return (
            <button
              key={i}
              onClick={() => setSelectedDay(day)}
              className={`h-16 rounded-lg border text-left p-1 transition-colors ${
                isSelected ? 'border-brand bg-blue-50' :
                isToday ? 'border-brand/50 bg-blue-50/40' :
                'border-gray-100 hover:border-gray-300'
              } ${isPast ? 'opacity-40' : ''}`}
            >
              <div className={`text-xs ${isToday ? 'font-bold text-brand' : 'text-gray-500'}`}>{day}</div>
              <div className="flex flex-wrap gap-0.5 mt-0.5">
                {items.slice(0, 3).map((s, j) => (
                  <span
                    key={j}
                    className={`w-1.5 h-1.5 rounded-full ${s.is_industry_specific ? 'bg-brand' : 'bg-gray-400'}`}
                  />
                ))}
                {items.length > 3 && (
                  <span className="text-[10px] text-gray-400">+{items.length - 3}</span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* 선택한 날짜의 지원사업 상세 */}
      <div className="mt-4 border-t border-gray-100 pt-4">
        <div className="text-sm font-medium text-gray-700 mb-2">
          {selectedDay != null ? `${month + 1}월 ${selectedDay}일 마감` : '날짜를 선택하세요'}
          <span className="text-gray-400 font-normal"> ({selectedItems.length}건)</span>
        </div>
        {selectedItems.length === 0 && (
          <div className="text-sm text-gray-400">이 날짜에 마감되는 지원사업이 없습니다.</div>
        )}
        <div className="space-y-2">
          {selectedItems.map((s, i) => (
            <a
              key={i}
              href={s.apply_url || undefined}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-gray-100 hover:border-brand/40 hover:bg-blue-50/30 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-2 h-2 rounded-full shrink-0 ${s.is_industry_specific ? 'bg-brand' : 'bg-gray-400'}`} />
                <span className="text-sm text-gray-800 truncate">{s.program_name}</span>
              </div>
              <span className="text-xs text-brand font-medium shrink-0">
                {s.support_amount_label ?? (s.max_support_amount ? `${s.max_support_amount.toLocaleString()}만원` : '-')}
              </span>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
