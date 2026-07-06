'use client'

import type { PeerRanking as PeerRankingType } from '@/lib/types'

interface Props {
  ranking: PeerRankingType | null | undefined
}

function tierFor(pct: number): { label: string; style: string } {
  if (pct <= 20) return { label: '우수', style: 'bg-green-50 border-green-300 text-green-800' }
  if (pct <= 50) return { label: '평균 이상', style: 'bg-blue-50 border-blue-300 text-blue-800' }
  if (pct <= 80) return { label: '평균 이하', style: 'bg-orange-50 border-orange-300 text-orange-800' }
  return { label: '개선 필요', style: 'bg-red-50 border-red-300 text-red-800' }
}

export default function PeerRanking({ ranking }: Props) {
  if (!ranking) return null

  if (ranking.percentile == null) {
    return (
      <div className="rounded-xl border-2 border-gray-200 bg-gray-50 p-5 flex items-center gap-4">
        <div className="text-4xl leading-none">🌱</div>
        <div>
          <div className="font-bold text-gray-700 mb-1">동종업계 순위표 — 데이터 쌓는 중</div>
          <div className="text-sm text-gray-500">
            같은 업종·규모 진단이 {ranking.min_sample_size}건 이상 쌓이면 순위를 보여드립니다
            (현재 {ranking.sample_size}건). 서비스가 커질수록 정확해지는 실측 기반 순위입니다.
          </div>
        </div>
      </div>
    )
  }

  const { label, style } = tierFor(ranking.percentile)

  return (
    <div className={`rounded-xl border-2 p-5 flex items-start gap-4 ${style}`}>
      <div className="text-4xl leading-none">🏆</div>
      <div className="flex-1">
        <div className="font-bold text-lg mb-1">동종업계 상위 {ranking.percentile}% — {label}</div>
        <div className="text-sm">
          같은 업종·규모로 진단받은 {ranking.sample_size}개 사업체의 가동률 중 귀사의 위치입니다.
        </div>
        <div className="text-xs opacity-60 mt-2">사용자 실측 입력값 기반 (표본 {ranking.sample_size}건)</div>
      </div>
    </div>
  )
}
