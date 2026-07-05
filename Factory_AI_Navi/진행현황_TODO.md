# Factory AI Navi — 진행 현황 & 할 일 목록

> **공모전**: 제14회 산업통상부 공공데이터 활용 아이디어 공모전  
> **마감**: 2026년 7월 6일 (**D-1**) | 2차 심사: 7월 27~31일  
> **서비스**: 중소 제조기업 AI 공정진단 & 정부지원 매칭 원스톱 플랫폼  
> **최종 수정**: 2026-07-05

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
- `layer1_etl/collectors/` — KIAT, KEIT, NTIS, KSNPC, KOITA 수집기
- `layer1_etl/transformers/` — 표준화, 단위변환, 결측처리
- `layer1_etl/loaders/` — PostgreSQL/SQLite 자동 전환
- `layer1_etl/dags/` — Airflow DAG 3종 (주간/일간/정리)
- `layer1_etl/config.py` — `DATABASE_URL` 환경변수 우선 처리 (SQLite/PostgreSQL 자동 전환)
- `scripts/seed_db.py` — 12업종 × 2규모 = 24행 Mock 벤치마크 데이터 + 지원사업 5건 적재 완료
- `dev_local.db` — SQLite 로컬 개발 DB (시드 데이터 포함)

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

## ⏳ 남은 작업 (D-1 기준 — 오늘 7월 5일)

### D-1 / 7월 5일 — 제출 준비 ← **오늘**

- [ ] 서비스 데모 영상 또는 스크린샷 캡처 (공모전 제출용)
- [ ] `기획서.pdf` 최종본 완성
- [ ] `README.md` 실행 가이드 작성
- [ ] 엔드투엔드 최종 확인 (백엔드 + 프론트 연동)

### D-0 / 7월 6일 — 접수 마감

- [ ] datacontest.kr 접수 완료
- [ ] 기획서.pdf + 기술스택 문서 첨부 확인

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| LLM | Gemini 2.5 Flash (dev) / Claude Sonnet 4.6 (prod 전환 가능) |
| RAG | 네이버 검색 API → Multi-Query → RRF → LLM Reranker |
| DB | SQLite (dev) / PostgreSQL + pgvector (prod) |
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
