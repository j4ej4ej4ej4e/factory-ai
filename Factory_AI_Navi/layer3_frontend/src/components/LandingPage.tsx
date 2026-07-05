'use client'

interface Props {
  onStart: () => void
}

const STATS = [
  { value: '12개', label: '핵심 제조 업종', sub: '뿌리업종 6 + 일반 제조 6' },
  { value: '3분', label: '진단 소요 시간', sub: '입력 후 AI 분석까지' },
  { value: '15+', label: '연계 지원사업', sub: 'KEIT · NTIS · 스마트공장' },
  { value: '무료', label: '비용', sub: '공모전 기간 완전 무료' },
]

const STEPS = [
  {
    num: '01',
    title: '기업 정보 입력',
    desc: '업종·규모·불량률·가동률 등 현재 KPI를 입력합니다.',
    icon: '📋',
  },
  {
    num: '02',
    title: 'AI 공정 진단',
    desc: 'KIAT 업종 통계 대비 갭을 분석하고 AI 도입 우선순위를 도출합니다.',
    icon: '🤖',
  },
  {
    num: '03',
    title: '결과 & 정부지원 매칭',
    desc: 'ROI 시뮬레이션과 신청 가능한 정부지원사업을 한눈에 확인합니다.',
    icon: '📊',
  },
]

const DATA_SOURCES = [
  { name: 'KIAT', desc: '산업기술통계 — 업종별 벤치마크' },
  { name: 'KEIT', desc: '연구개발사업 — 지원사업 공고' },
  { name: 'NTIS', desc: '국가R&D — 과제 정보' },
  { name: '고용노동부', desc: 'KOSIS — 규모별 인건비' },
  { name: '로봇진흥원', desc: '로봇산업 실태조사' },
  { name: '스마트공장', desc: '보급·확산 현황' },
]

export default function LandingPage({ onStart }: Props) {
  return (
    <div className="-mt-8 -mx-6">

      {/* ── Hero ── */}
      <section className="bg-gradient-to-br from-navy via-[#1a3355] to-[#0f2340] text-white px-6 py-20 text-center">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-sm text-blue-200 mb-6">
            🏆 제14회 산업통상자원부 공공데이터 활용 공모전 출품작
          </div>
          <h2 className="text-4xl md:text-5xl font-bold leading-tight mb-5">
            우리 공장, <span className="text-[#60A5FA]">AI로 진단</span>받아보세요
          </h2>
          <p className="text-blue-100 text-lg leading-relaxed mb-8 max-w-2xl mx-auto">
            업종·규모·KPI 입력 한 번으로<br/>
            동종업계 대비 갭 분석 · AI 도입 우선순위 · ROI · 정부지원 매칭까지
            <strong className="text-white"> 3분 만에</strong> 확인하세요
          </p>
          <button
            onClick={onStart}
            className="bg-brand hover:bg-blue-500 text-white font-bold text-lg px-10 py-4 rounded-xl shadow-lg shadow-blue-900/40 transition-all hover:scale-105 active:scale-100"
          >
            무료 AI 진단 시작하기 →
          </button>
          <p className="mt-4 text-blue-300 text-sm">별도 회원가입 없이 즉시 사용 가능</p>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="bg-white border-b border-gray-100 px-6 py-8">
        <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {STATS.map((s) => (
            <div key={s.value}>
              <div className="text-3xl font-bold text-brand">{s.value}</div>
              <div className="text-sm font-semibold text-gray-800 mt-1">{s.label}</div>
              <div className="text-xs text-gray-400 mt-0.5">{s.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="bg-gray-50 px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-2xl font-bold text-navy text-center mb-2">이용 방법</h3>
          <p className="text-gray-500 text-center text-sm mb-10">3단계로 완성되는 AI 공정 진단</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map((s, i) => (
              <div key={s.num} className="relative bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 text-gray-300 text-xl z-10">→</div>
                )}
                <div className="text-3xl mb-3">{s.icon}</div>
                <div className="text-xs font-bold text-brand mb-1">STEP {s.num}</div>
                <h4 className="font-bold text-gray-800 mb-2">{s.title}</h4>
                <p className="text-sm text-gray-500 leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── What you get ── */}
      <section className="bg-white px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-2xl font-bold text-navy text-center mb-2">진단 결과로 확인할 수 있는 것</h3>
          <p className="text-gray-500 text-center text-sm mb-10">전문 컨설턴트의 분석을 AI가 대신합니다</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { icon: '📊', title: '동종업계 벤치마크 갭 분석', desc: '한국산업단지공단(KICOX) 실측 가동률을 업종 평균과 비교하고, 불량률·인당생산액은 참고 추정치로 함께 제공합니다.' },
              { icon: '🎯', title: 'AI 도입 우선순위 Top 3', desc: '귀사 상황에 맞는 예측유지보수·비전검사·공정제어 등 최적 솔루션을 추천합니다.' },
              { icon: '💰', title: 'ROI 시뮬레이션', desc: '투자 비용 대비 연간 절감액·투자 회수기간·3년 순이익을 계산합니다.' },
              { icon: '🏛️', title: '정부지원사업 매칭', desc: 'AI바우처·스마트공장·뿌리업종 특화 지원사업 중 신청 가능한 것만 추려드립니다.' },
              { icon: '🔍', title: '실시간 웹 RAG 분석', desc: '네이버 검색 기반 최신 동종업계 AI 도입 사례를 수집·분석해 근거로 제시합니다.' },
              { icon: '📄', title: 'PDF 보고서 다운로드', desc: '분석 결과를 전문가 수준의 보고서로 다운로드해 사내 보고에 활용하세요.' },
            ].map((f) => (
              <div key={f.title} className="flex gap-4 p-5 rounded-xl border border-gray-100 hover:border-brand/30 hover:shadow-sm transition-all">
                <div className="text-2xl shrink-0">{f.icon}</div>
                <div>
                  <div className="font-semibold text-gray-800 text-sm mb-1">{f.title}</div>
                  <div className="text-xs text-gray-500 leading-relaxed">{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 공공데이터 출처 ── */}
      <section className="bg-navy/5 border-t border-navy/10 px-6 py-12">
        <div className="max-w-4xl mx-auto">
          <h3 className="text-sm font-bold text-navy text-center mb-1">활용 공공데이터</h3>
          <p className="text-xs text-gray-400 text-center mb-6">신뢰할 수 있는 정부 공식 통계 데이터를 기반으로 분석합니다</p>
          <div className="flex flex-wrap justify-center gap-3">
            {DATA_SOURCES.map((d) => (
              <div key={d.name} className="flex items-center gap-2 bg-white border border-gray-200 rounded-full px-4 py-2 text-xs shadow-sm">
                <span className="font-bold text-brand">{d.name}</span>
                <span className="text-gray-400">{d.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Bottom ── */}
      <section className="bg-gradient-to-r from-brand to-navy px-6 py-16 text-center text-white">
        <div className="max-w-2xl mx-auto">
          <h3 className="text-2xl font-bold mb-3">지금 바로 무료 진단을 받아보세요</h3>
          <p className="text-blue-100 text-sm mb-8">
            중소 제조기업 전용 · 회원가입 불필요 · 3분 완성
          </p>
          <button
            onClick={onStart}
            className="bg-white text-brand font-bold text-base px-10 py-4 rounded-xl hover:bg-blue-50 transition-all hover:scale-105 active:scale-100 shadow-lg"
          >
            AI 공정 진단 시작하기 →
          </button>
        </div>
      </section>

    </div>
  )
}
