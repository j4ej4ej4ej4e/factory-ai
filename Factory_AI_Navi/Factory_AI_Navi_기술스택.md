# Factory AI Navi — 기술 스택 & 분석 과정 상세 기술서

> 제14회 산업통상부 공공데이터 활용 아이디어 공모전 | 제품 및 서비스 개발 부문
> 최종 수정: 2026-07-05 (v3.0 — 실제 구현 코드 기준 전면 재작성)

> ⚠️ 이 문서는 실제 저장소 코드(`layer1_etl/`, `layer2_ai/`, `layer3_api/`, `layer3_frontend/`)를
> 직접 확인하여 작성했습니다. 구현되지 않은 기능(예: 이전 버전에서 언급했던 LangGraph, pgvector
> 벡터검색, OpenAI 임베딩, 카카오 알림톡)은 모두 제외했고, 실제로 동작하는 부분만 기술합니다.

---

## 목차

1. [전체 시스템 아키텍처](#1-전체-시스템-아키텍처)
2. [레이어 1 — 데이터 수집 & ETL](#2-레이어-1--데이터-수집--etl)
3. [레이어 2 — AI 분석 엔진](#3-레이어-2--ai-분석-엔진)
4. [레이어 3 — 서비스 API & 프론트엔드](#4-레이어-3--서비스-api--프론트엔드)
5. [분석 과정 Step-by-Step](#5-분석-과정-step-by-step)
6. [기술 스택 전체 요약표](#6-기술-스택-전체-요약표)
7. [데이터 실측/추정 구분표 — 정직성 체크리스트](#7-데이터-실측추정-구분표--정직성-체크리스트)

---

## 1. 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Factory AI Navi                          │
├──────────────────┬──────────────────────┬───────────────────────┤
│    LAYER 1       │       LAYER 2        │       LAYER 3         │
│  데이터 수집     │    AI 분석 엔진      │    서비스 레이어      │
│                  │                      │                       │
│ 공공데이터 API   │  Orchestrator        │  FastAPI (SSE 스트림) │
│ ETL 파이프라인   │  (순수 Python 클래스 │  Next.js 14 대시보드  │
│ SQLite(dev)/     │   기반 순차 실행,    │  PDF 레포트 생성      │
│  PostgreSQL(prod)│   LangGraph 미사용)  │  (ReportLab)          │
│ Airflow DAG      │  온라인 RAG 엔진     │                       │
│ (Docker Compose) │  ROI 계산 모델       │                       │
└──────────────────┴──────────────────────┴───────────────────────┘
```

### 핵심 설계 원칙

- **실측 우선**: 벤치마크 중 KICOX 가동률만 실측 공공데이터이고, 나머지(불량률·AI도입률·인당생산액 등)는
  참고 추정치로 명확히 구분해 표시합니다. AI 우선순위 결정과 ROI 금액 계산에는 실측치(가동률)와
  사용자가 직접 입력한 값(pain point 체크)만 사용하고, 추정치는 화면 참고용으로만 노출합니다.
- **온라인 RAG**: 사전 구축한 벡터 DB 없이, 매 진단 시점에 실시간 웹 검색(Naver+Tavily)으로
  최신 사례를 가져와 근거로 제시합니다.
- **12개 업종 심화**: 47개 전체 업종 대신 12개 핵심 업종(뿌리업종 6 + 일반 제조업 6)에
  집중해 업종별 AI 매핑·ROI 파라미터를 세밀하게 설계했습니다.
- **에이전트 자율성**: 업종·공정·현장 문제만 입력하면 지원사업 매칭→벤치마크 분석→AI 우선순위
  도출→ROI 계산까지 자율 수행합니다 (`Orchestrator.run()` 단일 호출).

---

## 2. 레이어 1 — 데이터 수집 & ETL

### 2.1 핵심 업종 12개

**그룹 A — 뿌리업종 6개** (정부 특별 지원 대상)

| KSIC | 업종명 | 핵심 공정 | 주요 AI 적용 |
|------|--------|-----------|-------------|
| C243 | 주조 | 용해→주입→냉각→탈사→검사 | 공정제어, 비전검사 |
| C251 | 금형 | 설계→가공→열처리→측정→검사 | 예측유지보수, 비전검사 |
| C259 | 소성가공 | 가열→단조/압연→트리밍→검사 | 예측유지보수, 공정제어 |
| C289 | 용접 | 준비→용접→비파괴검사→후처리 | 비전검사, 로봇자동화 |
| C301 | 표면처리 | 전처리→도금/도장→검사→폐수처리 | 에너지최적화, 공정제어 |
| C302 | 열처리 | 전처리→로 처리→냉각→경도검사 | 에너지최적화, 공정제어 |

**그룹 B — 일반 제조업 6개**

| KSIC | 업종명 | 핵심 공정 | 주요 AI 적용 |
|------|--------|-----------|-------------|
| C10 | 식품제조 | 원료→가공→포장→HACCP→출하 | 비전검사, 품질관리 |
| C22 | 사출성형 | 수지투입→사출→냉각→취출→검사 | 예측유지보수, 비전검사 |
| C25 | 금속가공 | 소재→절삭/프레스→조립→검사 | 예측유지보수, 비전검사 |
| C26 | 전자부품 | 기판→SMT 실장→납땜→AOI→완성 | 비전검사, 품질관리 |
| C29 | 산업기계 | 부품가공→조립→성능시험→출하 | 예측유지보수, 로봇자동화 |
| C30 | 자동차부품 | 프레스/사출→도장→조립→외관검사 | 비전검사, 품질관리, 로봇자동화 |

### 2.2 데이터 수집기(Collector) 실제 연동 현황

`layer1_etl/collectors/`의 각 수집기는 `collect()`(실제 API) / `get_mock_data()`(폴백) 구조를
공통으로 가지며, API 키가 플레이스홀더면 자동으로 mock으로 대체합니다.

| 수집기 | 상태 | 상세 |
|---|---|---|
| `ksnpc_collector.py` (KICOX) | ✅ **실데이터 (v2.0)** | odcloud.kr 파일데이터 API 3종(가동률/생산실적/수출실적) 연동. KICOX가 제공하는 업종 대분류 10종을 우리 12개 KSIC 코드로 근사 매핑(`CATEGORY_MAP`), 생산가중평균 가동률 계산. 2026-03 기준 |
| `bizinfo_collector.py` (기업마당) | ✅ **실데이터** | 실시간 공고 API, AI/제조 연관 키워드로 자동 필터링 |
| `kstartup_collector.py` (K-Startup) | ✅ **실데이터** | 실시간 공고 API, `ServiceKey`(대문자 S) 파라미터 필요 |
| `keit_collector.py` (KEIT) | ❌ **미사용** | mock 데이터만 존재, 실제 크롤링 미구현 — 지원사업 파이프라인에서 제외 (BIZINFO·K-Startup으로 대체) |
| `ntis_collector.py` (NTIS) | ⚠️ **키 검증만** | API 키 발급·XML 응답 확인은 완료했으나 실제 파싱 로직 미구현. 지원사업 매칭 파이프라인에는 미포함 |
| `kiat_collector.py` / `koita_collector.py` | ⚠️ **참고 인용만** | KIAT 산업기술통계집, KOITA 로봇산업실태조사 PDF를 페이지 단위로 직접 확인한 결과, 우리가 필요한 업종별 세분류 불량률·AI도입률 데이터는 없음을 확인. 시장 규모 근거(제조업 AI 활용기업 수 추이 등)로만 기획서에 인용하고, 벤치마크 DB에는 mock 값 유지 |

**검토했으나 채택하지 않은 데이터셋**: KOSIS 광업제조업조사(`DT_1FS1104_R` 등) — 실제 Open API 접근에
성공했고 12개 KSIC 업종 코드 전부 확인했으나, **최신 데이터가 2019년까지만 존재**해 최신성 기준을
충족하지 못해 제외.

### 2.3 벤치마크 테이블 스키마 (`kiat_industry_stats`, 24행 = 12업종 × 2규모)

`layer1_etl/models/industry_stats.py`의 `KiatIndustryStat` 모델 기준:

| 컬럼 | 실측 여부 | 출처 |
|---|---|---|
| `avg_operating_rate` (가동률) | ✅ 실측 | KICOX 국가산업단지 산업동향정보 |
| `ksnpc_production_billion_krw` / `ksnpc_export_million_usd` | ✅ 실측 | KICOX (참고용 부가 지표) |
| `avg_defect_rate` (불량률) | ⚠️ 추정 | 업종별 실측 공식 통계 없음 (KIAT/KOITA/KOSIS 모두 확인) |
| `ai_adoption_rate` (AI도입률) | ⚠️ 추정 | 중기부 스마트공장 현황 등 참고 |
| `avg_production_per_person` (인당생산액) | ⚠️ 추정 | — |
| `avg_labor_cost_per_person` (인건비) | ⏳ 재작업 예정 | KOSIS 사업체노동력조사 업종별 재추출 필요 |
| `avg_energy_cost_ratio`, `robot_adoption_rate`, `avg_robot_roi_months` | ⚠️ 추정 | — |

이 구분은 `layer2_ai/tools/benchmark_tool.py`의 `is_estimate` 플래그로 코드에도 그대로 반영되어
있으며, 추정치는 AI 우선순위 결정·ROI 금액 계산에 사용하지 않습니다 (§3.3 참고).

### 2.4 ETL 파이프라인

```
[수집] 공공데이터 API 호출 (odcloud.kr, bizinfo.go.kr, data.go.kr)
   ↓
[전처리] 업종 코드 표준화 · 기업 규모 매핑 · 결측값 처리(업종평균 대체) · 단위 통일
   ↓
[적재] SQLAlchemy ORM → SQLite(dev) / PostgreSQL(prod) — DATABASE_URL 환경변수로 자동 전환
   ↓
[스케줄링] Apache Airflow DAG 3종 (주간 ETL / 일간 지원사업 갱신 / 월간 정리)
           — docker-compose.yml로 Airflow 스케줄러+웹서버만 컨테이너 실행
             (FastAPI/Next.js 앱 자체는 uvicorn/npm으로 로컬 직접 실행, 별도 앱 컨테이너 없음)
```

실행: `python -m layer1_etl.main --source all` (또는 `--source ksnpc`, `--source bizinfo` 등
단일 수집기 지정 가능)

---

## 3. 레이어 2 — AI 분석 엔진

### 3.1 실제 아키텍처

```
company_profile (업종/규모/현재 KPI/체크한 현장 문제)
       ↓
┌───────────────────────────────────────────────────────────┐
│              Orchestrator.run()  (순수 Python)             │
│                                                             │
│  ① MatchingAgent.match()       — 지원사업 1차 매칭         │
│  ② DiagnosticAgent.run_step_a()— 벤치마크 갭 분석          │
│  ③ DiagnosticAgent.run_step_b()— RAG 검색 + LLM 우선순위   │
│  ④ MatchingAgent.match()       — AI유형 반영 재매칭        │
│  ⑤ DiagnosticAgent.run_step_c()— ROI 계산 (ROICalculator)  │
└───────────────────────────────────────────────────────────┘
       ↓
DiagnosisReport (dataclass) → JSON / SSE 스트리밍
```

LangGraph 등 별도 에이전트 프레임워크 없이, `orchestrator.py`가 각 단계를 순서대로 호출하는
단순한 구조입니다. 지원사업 매칭을 벤치마크 분석보다 먼저 1차 실행하는 이유는 ROI 계산에
자부담 비율(`co_funding_rate`)이 필요하기 때문이고, AI 우선순위가 나온 뒤 AI 유형을 반영해
한 번 더 재매칭합니다.

### 3.2 LLM 연동 (`layer2_ai/llm_client.py`)

```python
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude")  # "claude" | "gemini"

def call_llm(user: str, system: str = "", max_tokens: int = 1000) -> str:
    if LLM_PROVIDER == "gemini":
        return _call_gemini(user, system, max_tokens)   # google-genai SDK
    return _call_claude(user, system, max_tokens)        # anthropic SDK
```

개발 중에는 Gemini 2.5 Flash(비용 절감), 운영 전환 시 Claude Sonnet 4.6으로 교체 가능하도록
환경변수 하나로 스위칭됩니다.

> ⚠️ 실행 전제조건: `.env`의 `GEMINI_API_KEY` / `ANTHROPIC_API_KEY`가 실제 키로 설정되어 있어야
> 합니다. 플레이스홀더 상태면 LLM 호출 시 에러가 발생합니다.

### 3.3 온라인 RAG 엔진 (`layer2_ai/rag/`)

사전 구축한 벡터 DB(pgvector 등)를 쓰지 않고, **매 진단 요청마다 실시간 웹 검색**으로 사례를
가져오는 방식입니다. `OnlineRAGRetriever.retrieve()` 5단계 파이프라인:

```
① Multi-Query 생성 (LLM)
   "도입사례" / "비용·ROI" / "기술·공정효과" 3개 각도로 검색 쿼리 3개 생성
       ↓
② 병렬 검색 (ThreadPoolExecutor)
   Naver 검색 API + Tavily API(선택, 키 없으면 자동 비활성화) 동시 호출
       ↓
③ RRF(Reciprocal Rank Fusion) 합산
   score(url) = Σ 1/(k + rank_i) — 여러 쿼리에서 반복 등장한 URL 가중치 상승
       ↓
④ 본문 크롤링
   상위 N건은 BeautifulSoup + lxml로 실제 본문 텍스트 추출 (나머지는 검색 스니펫 사용)
       ↓
⑤ LLM Reranker
   LLM이 "실제 도입사례 포함 여부·구체적 수치 포함 여부·한국 중소제조업 관련성" 기준으로
   0~10점 채점 → 상위 5건만 최종 채택
```

> ⚠️ 실행 전제조건: `.env`의 `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`이 실제 키로 설정되어야
> 검색이 동작합니다. 플레이스홀더 상태면 조용히 빈 결과를 반환합니다(에러는 아님).

**실증 결과 (2026-06-30)**: 금속가공/예지보전 쿼리 → 3개 쿼리 × Naver 10건 = 30건 수집 →
RRF 합산 후 Top10~29건 후보 → Reranker로 관련도 8~10/10인 Top5 선별 (예: saige.ai "ROI 10배
달성" 사례, ZDNet "예지보전 AI" 기사 등 실제 수집 확인).

### 3.4 벤치마크 갭 분석 (`tools/benchmark_tool.py`)

```python
def analyze_gap(company_kpi: dict, peer_data: dict) -> dict:
    # 인당생산액 / 가동률 / 에너지비용비율 갭 계산 (동종평균 대비 %p, %)
    # 불량률은 is_estimate=True 플래그를 붙여 "참고치"로만 반환
    ...

def get_improvement_potential(industry_code, gap_analysis) -> list[str]:
    # 가동률·에너지비용·인당생산액 갭만 우선순위 트리거로 사용
    # 불량률(추정치)은 우선순위 결정에서 제외 — 실측 근거가 없기 때문
```

### 3.5 AI 우선순위 도출 (`agents/diagnostic.py` Step B)

```python
pain_ai = []
for pp in pain_points:                       # 사용자가 직접 체크한 현장 문제
    pain_ai.extend(PAIN_POINT_TO_AI.get(pp, []))
priority_ai = list(dict.fromkeys(pain_ai + best_ai))  # pain point 우선, 업종 기본값 보조

primary_ai = priority_ai[0]
rag_sources = rag_retriever.retrieve(industry_code, primary_ai, company_profile)
# → LLM에 벤치마크(가동률 실측 + 불량률 참고치 구분 표시) + RAG 사례 + pain point를
#   프롬프트로 구성해 AI 우선순위 Top3 JSON 생성
```

`PAIN_POINT_TO_AI` 매핑 예시 (`constants.py`):

| Pain Point | 추천 AI 유형 |
|---|---|
| 설비 자주 고장 | 예측유지보수 |
| 에너지 비용 과다 | 에너지최적화, 공정제어 |
| 인력 부족 | 로봇자동화 |
| 품질 균일성 불량 | 품질관리, 공정제어 |

### 3.6 ROI 시뮬레이션 (`agents/roi_calculator.py`)

```
연간 절감액 = 인건비 절감 + 에너지 절감 + 가동률 개선에 따른 생산증대
투자 회수   = 자부담 / 연간 절감액 × 12 (개월)
3년 순이익  = 연간 절감액 × 3 - 자부담
```

```python
labor_savings  = total_labor  * params["labor_reduction_rate"]   # 가정치
energy_savings = total_energy * params["energy_reduction_rate"]  # 가정치

# 가동률 개선분 — 실측 가동률을 기준선으로 삼아 계산 (불량률 기반 계산 완전 제외)
current_operating_rate = company_profile.get("operating_rate") \
    or peer_data.get("avg_operating_rate") or 75.0   # KICOX 실측 동종평균 우선 사용
operating_gain_pp = params["operating_rate_gain_pp"]              # 가정치
uplift_ratio = operating_gain_pp / current_operating_rate
operating_uplift_savings = uplift_ratio * annual_production
```

**왜 불량률 기반 계산을 뺐는가**: 불량률은 업종별 실측 통계가 전혀 없는 추정치라, 이걸 금액으로
환산하면 근거 없는 숫자가 된다. 반면 가동률은 KICOX 실측 벤치마크가 있어, 그 실측 기준선 위에서
"가동률이 몇 %p 개선되면 생산량이 얼마나 느는가"를 계산하면 최소한 기준선만큼은 실측 데이터에
뿌리를 둔 숫자가 된다. 개선폭(`operating_rate_gain_pp`) 자체는 업계 사례 기반 가정치이며,
이는 인건비·에너지 절감률도 마찬가지로 가정치임을 `calculation_basis` 필드에 항상 명시한다.

### 3.7 지원사업 매칭 (`tools/subsidy_tool.py`)

**벡터 유사도가 아닌 규칙 기반 필터링 + 점수화**입니다:

```python
def _calc_match_score(subsidy, industry_code, company_size, ai_types, is_roots):
    # ① 업종 코드 불일치 → None (탈락)
    # ② 기업 규모 불일치 → None (탈락)
    score = 1.0
    # ③ AI 유형 일치 개수만큼 가점 (+0.3 / 건)
    # ④ 뿌리업종 + 뿌리업종 전용 카테고리면 가점 (+0.5)
    return score
```

정렬 기준: 마감 D-7 이내 긴급 공고 최우선 → 매칭 점수 내림차순 → 마감일 오름차순.
(`keit_subsidies` 테이블에 `embedding` 컬럼이 정의는 되어 있으나 주석 처리된 미사용 상태입니다.)

---

## 4. 레이어 3 — 서비스 API & 프론트엔드

### 4.1 FastAPI 백엔드 (`layer3_api/`)

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/v1/diagnose` | SSE 스트리밍 진단 (`progress`→`step_result`×3→`complete`/`error` 이벤트) |
| GET | `/api/v1/subsidies` | 현재 신청 가능 지원사업 목록 |
| POST | `/api/v1/roi-simulate` | 단일 AI 유형 ROI 재계산 |
| GET | `/api/v1/report/{id}` | 진단 결과 JSON (LRU 캐시, 최대 100개) |
| GET | `/api/v1/report/{id}/pdf` | ReportLab 기반 PDF 레포트 다운로드 |

`diagnose.py`는 `asyncio.get_event_loop().run_in_executor()`로 각 단계를 실행하며, 매 단계마다
SSE 이벤트를 즉시 클라이언트로 흘려보냅니다(사용자가 "지원사업 검색 중... → 벤치마크 분석 중...
→ AI 우선순위 도출 중... → ROI 계산 중..." 진행 상황을 실시간으로 봄).

### 4.2 Next.js 14 프론트엔드 (`layer3_frontend/`)

| 컴포넌트 | 역할 |
|---|---|
| `LandingPage.tsx` | 서비스 소개 랜딩 |
| `InputForm.tsx` | 업종 12개, 기업규모, KPI, 현장 문제(pain point) 체크박스 입력 |
| `DiagnoseProgress.tsx` | SSE `ReadableStream` 수신, 실시간 진행 표시 |
| `ResultDashboard.tsx` | 전체 결과 조합 대시보드 |
| `BenchmarkRadar.tsx` | Recharts 레이더차트 (귀사 vs 업종평균, 추정치 항목은 "(추정)" 라벨 자동 표시) |
| `ROIBarChart.tsx` | Recharts 막대그래프, ROI 비교 |
| `SubsidyTable.tsx` | 지원사업 테이블 (긴급/뿌리업종 배지) |

상태 흐름: `page.tsx`가 `input → diagnosing → result` 3단계 상태머신으로 관리.

---

## 5. 분석 과정 Step-by-Step

```
STEP 1: 기업 입력
  업종(12개 중 선택) + 기업규모 + 현재 KPI(가동률·에너지비용 등) + 현장 문제 체크

STEP 2: 지원사업 1차 매칭
  keit_subsidies 조회 → 업종·규모 필터 → 자부담률 확보 (ROI 계산용)

STEP 3: 동종업계 벤치마크 분석
  kiat_industry_stats 조회 → 가동률(실측) 갭 계산, 불량률 등은 참고치로 별도 표시

STEP 4: 온라인 RAG 검색
  Multi-Query → Naver/Tavily 병렬 검색 → RRF → 크롤링 → LLM Reranker → Top5

STEP 5: LLM 진단
  가동률 갭 + 현장 문제(pain point) + RAG 사례 → LLM 프롬프트 → AI 우선순위 Top3 JSON

STEP 6: 지원사업 재매칭
  AI 유형 반영해 재검색 → Top5 확정

STEP 7: ROI 시뮬레이션
  인건비·에너지·가동률개선 절감액 + 정부지원금 → 투자회수기간 / 3년 순이익

STEP 8: 레포트 생성
  SSE로 실시간 스트리밍 + 완료 후 PDF 다운로드 가능
```

---

## 6. 기술 스택 전체 요약표

| 영역 | 기술 | 비고 |
|-----|-----|---------|
| **언어** | Python 3.11+ | |
| **AI LLM** | Claude Sonnet 4.6 (Anthropic) / Gemini 2.5 Flash (Google) | `LLM_PROVIDER` 환경변수로 전환 |
| **RAG** | Naver 검색 API + Tavily(선택) → RRF → LLM Reranker | 온라인 실시간 검색, 사전 구축 벡터DB 없음 |
| **크롤링** | BeautifulSoup4 + lxml | RAG 후보 본문 추출 |
| **ORM/DB** | SQLAlchemy 2.0 + SQLite(dev) / PostgreSQL(prod, psycopg2) | `DATABASE_URL` 환경변수로 자동 전환 |
| **ETL** | pandas, polars, numpy, openpyxl | |
| **스케줄러** | Apache Airflow 2.9 (DAG 3종) | docker-compose로 Airflow만 컨테이너 실행 |
| **API 프레임워크** | FastAPI 0.111 + SSE 스트리밍 | uvicorn |
| **프론트엔드** | Next.js 14 + Tailwind CSS + Recharts | |
| **PDF 생성** | ReportLab | |
| **테스트** | pytest, pytest-asyncio | |
| **컨테이너** | Docker Compose (Airflow 스케줄러·웹서버·메타DB만) | 앱 서버(FastAPI/Next.js)는 로컬 직접 실행, 별도 컨테이너 없음 |

**이번 버전에서 제외한 항목** (이전 문서에 있었으나 실제 코드에 없음 확인): LangGraph, LangChain,
pgvector 벡터검색, OpenAI 임베딩 파이프라인, GitHub Actions CI/CD, Sentry 모니터링, 카카오
알림톡 연동, WeasyPrint.

---

## 7. 데이터 실측/추정 구분표 — 정직성 체크리스트

공모전 심사 특성상 "공공데이터를 어디까지 실제로 활용했는가"가 핵심 평가 요소이므로, 화면에
노출되는 모든 수치의 실측/추정 여부를 코드 레벨에서 추적합니다.

| 지표 | 실측/추정 | 실제 사용처 |
|---|---|---|
| 가동률 (`avg_operating_rate`) | ✅ 실측 (KICOX) | 벤치마크 비교문, ROI 가동률개선 계산의 기준선 |
| 국가산단 생산·수출실적 | ✅ 실측 (KICOX) | 참고 지표로 노출 |
| 지원사업 공고 (금액/마감일) | ✅ 실측 (BIZINFO/K-Startup 실시간 API) | 지원사업 매칭 전체 |
| 불량률, AI도입률, 인당생산액, 에너지비용비율, 인건비 | ⚠️ 추정 | 화면에 "(추정)" 라벨과 함께 참고 표시만, 우선순위·ROI 금액 계산에는 미사용 |
| 현장 문제(pain point) | ✅ 사용자 입력 (사실) | AI 우선순위 결정의 주 동력 |
| RAG 검색 사례 | ✅ 실시간 웹 검색 결과 (사실) | AI 우선순위 근거, ROI 기대효과 참고 |

이 표는 `Factory_AI_Navi_기획서.md` §SLIDE05/SLIDE10의 출처 표기와 1:1로 대응합니다.

---

*작성: Factory AI Navi Team | v3.0 | 2026-07-05*
*이 문서를 PDF로 변환하려면: `pandoc Factory_AI_Navi_기술스택.md -o Factory_AI_Navi_기술스택.pdf --pdf-engine=weasyprint`*
