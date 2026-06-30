import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Factory AI Navi — 중소 제조기업 AI 공정 진단',
  description: '산업부 공공데이터 기반 AI 공정 진단 & 정부지원 매칭 플랫폼',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen">
        <header className="bg-navy text-white shadow-lg">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center text-sm font-bold">
              AI
            </div>
            <div>
              <h1 className="text-lg font-bold leading-tight">Factory AI Navi</h1>
              <p className="text-xs text-blue-200 leading-tight">중소 제조기업 AI 공정 진단 플랫폼</p>
            </div>
            <div className="ml-auto text-xs text-blue-300">
              제14회 산업통상자원부 공공데이터 활용 공모전
            </div>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
        <footer className="border-t border-gray-200 mt-16">
          <div className="max-w-6xl mx-auto px-6 py-6 text-xs text-gray-400 text-center">
            데이터 출처: KIAT 산업기술통계 | 고용노동부 인건비 통계 | 로봇산업진흥원 실태조사 | KEIT/NTIS 지원사업
          </div>
        </footer>
      </body>
    </html>
  )
}
