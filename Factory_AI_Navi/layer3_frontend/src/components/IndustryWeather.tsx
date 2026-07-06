'use client'

import type { IndustryWeather as IndustryWeatherType } from '@/lib/types'

interface Props {
  weather: IndustryWeatherType | null | undefined
}

const LABEL_STYLE: Record<string, string> = {
  '맑음':      'bg-yellow-50 border-yellow-300 text-yellow-800',
  '구름 조금': 'bg-blue-50 border-blue-300 text-blue-800',
  '비':        'bg-slate-50 border-slate-400 text-slate-800',
  '폭풍주의보': 'bg-red-50 border-red-400 text-red-800',
  '관측 불가': 'bg-gray-50 border-gray-300 text-gray-500',
}

export default function IndustryWeather({ weather }: Props) {
  if (!weather) return null
  const style = LABEL_STYLE[weather.label] ?? 'bg-gray-50 border-gray-300 text-gray-600'

  return (
    <div className={`rounded-xl border-2 p-5 flex items-start gap-4 ${style}`}>
      <div className="text-4xl leading-none">{weather.icon}</div>
      <div className="flex-1">
        <div className="font-bold text-lg mb-1">오늘의 업종 날씨: {weather.label}</div>
        <div className="text-sm">{weather.message}</div>
        {weather.energy_warning && (
          <div className="text-sm mt-1">{weather.energy_warning}</div>
        )}
        {weather.basis && (
          <div className="text-xs opacity-60 mt-2">{weather.basis}</div>
        )}
      </div>
    </div>
  )
}
