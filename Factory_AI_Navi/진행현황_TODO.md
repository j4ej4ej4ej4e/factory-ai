# Factory AI Navi — 진행 현황 & 할 일 목록

> **공모전**: 제14회 산업통상부 공공데이터 활용 아이디어 공모전  
> **마감**: 2026년 7월 6일 (**D-0, 접수 당일**) | 2차 심사: 7월 27~31일  
> **서비스**: 중소 제조기업 AI 공정진단 & 정부지원 매칭 원스톱 플랫폼  
> **최종 수정**: 2026-07-06

---

## 전체 아키텍처

| 레이어 | 기술 | 상태 |
|--------|------|------|
| Layer 1 — ETL/DB | SQLAlchemy + SQLite(dev) / PostgreSQL(prod) | ✅ 완료 |
| Layer 2 — AI 엔진 | Gemini 2.5 Flash + 네이버 RAG + ROI 계산 | ✅ 완료 |
| Layer 3 — 서비스 | FastAPI (SSE 스트리밍) + Next.js 14 | ✅ 완료 |

---

## ✅ 완료된 작업

### Layer 1 — 데이터 수집 & ETL

- `layer1_etl/models/` — SQLAlchemy ORM 모델 3종 (industry_stats, subsidies, benchmark)
- `layer1_etl/collectors/` — 아래 "실데이터 연동 현황" 참고
- `layer1_etl/transformers/` — 표준화, 단위변환, 결측처리
- `layer1_etl/loaders/` — PostgreSQL/SQLite 자동 전환
- `layer1_etl/dags/` — Airflow DAG 3종 (주간/일간/정리)
- `layer1_etl/config.py` — `DATABASE_URL` 환경변수 우선 처리 (SQLite/PostgreSQL 자동 전환)
- `scripts/seed_db.py` — 12업종 × 2규모 = 24행 벤치마크 데이터 + 지원사업 적재
- `dev_local.db` — SQLite 로컬 개발 DB

**실데이터 연동 현황 (2026-07-05 기준)**

| 수집기 | 상태 | 비고 |
|---|---|---|
| KSNPC (KICOX 가동률·생산·수출) | ✅ 실데이터 (v2.0) | odcloud.kr 연동, 업종 대분류 매핑, 2026-03 기준 |
| BIZINFO (기업마당) | ✅ 실데이터 | 실시간 공고 API, AI/제조 키워드 필터링 |
| K-Startup (창업진흥원) | ✅ 실데이터 | 실시간 공고 API |
| KEIT | ❌ 제외 | mock만 존재, 실크롤링 미구현 — BIZINFO/K-Startup으로 대체 |
| NTIS | ⚠️ 키 검증만 | API 키·XML 응답 확인, 파싱 로직(`ntis_collector.py`) 미구현 |
| KIAT / KOITA (PDF) | 🔍 확인 후 보류 | 필요한 업종별 세분류 데이터 없음 확인, 시장성 근거로만 인용 |
| KOSIS 광업제조업조사 | 🔍 확인 후 폐기 | 실제 API 존재 확인했으나 2019년 데이터까지만 존재 — 최신성 미충족 |
| KOSIS 사업체노동력조사(인건비) | 🔍 탐색 중, 미구현 | `orgId=118/tblId=DT_118N_MON051` 조회 성공, 2025-12 최신 데이터 확인(C25 30~99인 상용임금 398~497만원/월). 일반 제조업 6개는 2자리 KSIC 직접매칭, 뿌리업종 6개는 상위업종(주조→C24, 나머지→C25) 근사대체 필요. 규모구간(30~99/100~299 등)도 소/중 기준과 불일치 — 수집기 미구현 |

**확정 업종 12개 × 규모 2개 = 24행 벤치마크**

| 그룹 | KSIC | 업종 |
|------|------|------|
| 뿌리업종 (6) | C243, C251, C259, C289, C301, C302 | 주조, 금형, 소성가공, 용접, 표면처리, 열처리 |
| 일반 제조 (6) | C10, C22, C25, C26, C29, C30 | 식품, 사출, 금속가공, 전자부품, 산업기계, 자동차부품 |

### Layer 2 — AI 분석 엔진

- `layer2_ai/llm_client.py` — Claude / Gemini 통합 래퍼 (`LLM_PROVIDER` env로 전환)
- `layer2_ai/agents/matching.py` — 지원사업 매칭 에이전트
- `layer2_ai/agents/diagnostic.py` — 공정 진단 에이전트 (Step A: 벤치마크 갭 / Step B: AI 우선순위 / Step C: ROI)
- `layer2_ai/rag/retriever.py` — 온라인 RAG (Naver Multi-Query → RRF → Gemini Reranker)
- `layer2_ai/rag/search_clients.py` — 네이버 검색 API 클라이언트

**⚠️ 미해결: Layer 2 실행 전제조건** — `.env`의 `GEMINI_API_KEY`, `NAVER_CLIENT_ID/SECRET`이 아직
플레이스홀더 상태. 키 입력 전까지 진단/RAG/ROI 파이프라인이 실제로 동작하지 않음 (Naver는 조용히
빈 결과 반환, Gemini는 호출 시 에러). 데모 전 최우선으로 키 발급 필요.

**2026-07-05 로직 수정 — 불량률 추정치 의존도 제거**
- 문제: 불량률은 업종별 실측 공공데이터가 전혀 없는데(KIAT/KOITA/KOSIS 광업제조업조사 모두 확인함),
  기존 로직은 이 추정치로 ①AI 우선순위 순위 결정, ②ROI 금액(`defect_savings`) 계산까지 했음
- 수정: `benchmark_tool.py`(우선순위 트리거에서 불량률 제거, `is_estimate` 플래그 추가) /
  `diagnostic.py`(pain_point가 우선순위를 주도하도록 순서 변경, 프롬프트에 실측·추정 구분 명시) /
  `constants.py`+`roi_calculator.py`(`defect_improvement_pp` → `operating_rate_gain_pp`로 교체,
  ROI의 세 번째 항목을 "가동률 개선에 따른 생산증대"로 재계산 — 기준선은 KICOX 실측 가동률)
- 연쇄 반영: `layer3_api/services/report_generator.py`(PDF 갭 테이블 추정치 라벨),
  `layer3_frontend`(`types.ts`/`BenchmarkRadar.tsx`/`LandingPage.tsx` 필드·문구 동기화),
  `Factory_AI_Navi_기획서.md` v2.1(STEP①②③ 문구, 데모 시나리오, 기대효과 표 전부 동기화)

**2026-07-06 추가 — 인터랙티브 확장 기능 3종**

| 기능 | 내용 | 파일 |
|---|---|---|
| 🕒 회수 타이머 | 인건비/에너지 절감률·가동률 개선폭을 슬라이더로 조정하며 ROI 실시간 재계산 | `roi_calculator.py`(`param_overrides`), `schemas.py`, `routers/subsidies.py`, `ROISimulatorPanel.tsx` |
| ☀️ 업종 날씨예보 | 가동률 갭(KICOX 실측)을 맑음/구름조금/비/폭풍주의보 아이콘으로 직관화 | `benchmark_tool.py`(`get_industry_weather`), `IndustryWeather.tsx` |
| 🏆 동종업계 순위표 | 사용자가 입력한 가동률을 익명 누적(`diagnosis_history` 신규 테이블) → 같은 업종·규모 내 상위 X% 계산. 표본 5건 미만이면 "데이터 쌓는 중" 안내로 대체 | `models/diagnosis_history.py`, `benchmark_tool.py`(`record_and_rank`), `PeerRanking.tsx` |

순위표는 조작된 통계가 아니라 실제 사용자 입력값이 쌓이는 구조라 서비스가 커질수록 정확해지는 성장형 지표. 백엔드(syntax+기능 테스트) / 프론트(tsc + `next build`) 전부 검증 완료.

**RAG 파이프라인 실증 (2026-06-30)**

```
[1] Gemini Multi-Query 생성: 3개 쿼리
[2] 네이버 실검색: 쿼리당 10건 = 총 30건 수집
[3] RRF 합산 후 Top10~29건 후보 풀
[4] Gemini Reranker → 최종 Top5 선별 (관련도 8~10/10)
```

예시: 금속가공 / 예지보전 쿼리 → saige.ai "ROI 10배 달성", ZDNet "예지보전 AI" 등 실제 기사 수집

### Layer 3 — 서비스 API & 프론트엔드

**FastAPI 백엔드** (`layer3_api/`)
- `main.py` — CORS, 3개 라우터 마운트
- `routers/diagnose.py` — `POST /api/v1/diagnose` SSE 스트리밍 (progress → step_result → complete)
- `routers/subsidies.py` — `GET /api/v1/subsidies`, `POST /api/v1/roi-simulate`
- `routers/report.py` — `GET /api/v1/report/{id}` (JSON), `GET /api/v1/report/{id}/pdf` (PDF)
- `services/report_generator.py` — ReportLab PDF 5섹션 생성
- `services/report_cache.py` — LRU 캐시 (최대 100개)

**Next.js 14 프론트엔드** (`layer3_frontend/`)
- `page.tsx` — 3단계 상태머신: `input → diagnosing → result`
- `InputForm.tsx` — 업종 12개, 기업규모, KPI 입력, 문제점 체크박스
- `DiagnoseProgress.tsx` — SSE 실시간 스트리밍 수신 (ReadableStream)
- `ResultDashboard.tsx` — 전체 결과 대시보드
- `BenchmarkRadar.tsx` — Recharts RadarChart (귀사 vs 업종평균)
- `ROIBarChart.tsx` — Recharts BarChart ROI 비교
- `ROISimulatorPanel.tsx` — 회수 타이머 (인터랙티브 ROI 시뮬레이터, 2026-07-06 추가)
- `IndustryWeather.tsx` — 업종 날씨예보 (2026-07-06 추가)
- `PeerRanking.tsx` — 동종업계 순위표 (2026-07-06 추가)
- `SubsidyTable.tsx` — 지원사업 테이블 (긴급/뿌리업종 배지)

---

## ✅ 추가 완료 (D-6 ~ D-2 기간)

### D-6 / 6월 30일 — 프론트엔드 통합 테스트
- ✅ 웹 E2E 테스트 3시나리오 (C25/C302/C243)
- ✅ ResultDashboard `assessment.includes` undefined 오류 수정
- ✅ ROIBarChart 빈 데이터 방어 처리

### D-5 / 7월 1일 — 안정화
- ✅ FastAPI 에러 핸들링 (Gemini API fallback)
- ✅ SSE 스트리밍 타임아웃 처리
- ✅ PDF 다운로드 한글 폰트 확인
- ✅ `.env.example` 정리

### D-4~3 / 7월 2~3일 — 완성도
- ✅ 지원사업 Mock 데이터 8건 (seed_db.py)
- ✅ 업종별 ROI 파라미터 확정 (constants.py)
- ✅ Next.js 빌드 성공 확인

---

## ⏳ 남은 작업 (D-0 기준 — 오늘 7월 6일 접수 마감)

### D-1 / 7월 5일 — 완료된 작업

- [x] KICOX(가동률·생산·수출) 실데이터 연동 (`ksnpc_collector.py` v2.0)
- [x] BIZINFO·K-Startup 실시간 지원사업 API 연동, KEIT mock 제거
- [x] `KeitSubsidy.to_dict()` 매칭 필터 누락 버그 수정
- [x] 불량률 추정치를 AI 우선순위·ROI 금액 계산에서 제거, 가동률 실측 기반으로 전환
- [x] 기획서 v2.1 — 위 로직 변경 반영, 과장 수치 톤다운
- [x] 기술스택.md v3.0 전면 재작성 (LangGraph/pgvector 등 미구현 항목 제거)

### D-0 / 7월 6일 — 접수 마감 ← **오늘**

- [ ] **`.env`에 `GEMINI_API_KEY`, `NAVER_CLIENT_ID/SECRET` 실키 입력** (현재 플레이스홀더 — 최우선)
- [ ] 엔드투엔드 최종 확인 (백엔드 + 프론트 연동, 실키 입력 후)
- [ ] 서비스 데모 영상 또는 스크린샷 캡처 (공모전 제출용)
- [ ] `기획서.pdf` 최종본 완성 (md → pdf 변환)
- [ ] `README.md` 실행 가이드 작성
- [ ] datacontest.kr 접수 완료
- [ ] 기획서.pdf + 기술스택 문서 첨부 확인

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| LLM | Gemini 2.5 Flash (dev) / Claude Sonnet 4.6 (prod 전환 가능) |
| RAG | 네이버 검색 API → Multi-Query → RRF → LLM Reranker |
| DB | SQLite (dev) / PostgreSQL (prod) — `keit_subsidies.embedding` 컬럼은 정의만 되어있고 미사용, pgvector 미적용 |
| API | FastAPI 0.111 + SSE 스트리밍 |
| Frontend | Next.js 14 + Tailwind CSS + Recharts |
| PDF | ReportLab |
| 인프라 (예정) | GCP Cloud Run + Cloud SQL |

---

## 실행 방법

```bash
# 백엔드
pip install -r requirements.txt
cp .env.example .env  # 실제 API 키 입력
python scripts/seed_db.py
uvicorn layer3_api.main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd layer3_frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 변경 이력

| 날짜 | 버전 | 내용 |
|------|------|------|
| 2026-04-28 | v1.0 | Layer 1 ETL 전체 초기 작성 |
| 2026-05-28 | v1.1 | Airflow DAG 3종, GCP Cloud SQL 전환 |
| 2026-06-29 | v2.0 | Layer 2 AI 엔진 완성, Gemini 통합, RAG 파이프라인 구현 |
| 2026-06-30 | v3.0 | Layer 3 FastAPI + Next.js 완성, 웹 서비스 실행 완료 |
| 2026-07-05 | v3.1 | D-1 기준 전체 현황 업데이트, 완료 항목 정리 |
| 2026-07-05 | v3.2 | KICOX/BIZINFO/K-Startup 실데이터 연동, KEIT 제거, 불량률 추정치 의존도 제거(ROI·우선순위 로직을 가동률 실측 기반으로 전환), 기획서 v2.1 동기화 |
| 2026-07-06 | v3.3 | 인터랙티브 확장 3종 추가: 회수 타이머(ROI 시뮬레이터), 업종 날씨예보, 동종업계 순위표(`diagnosis_history` 신규 테이블) |
