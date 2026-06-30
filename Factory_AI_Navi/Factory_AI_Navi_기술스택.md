# Factory AI Navi — 기술 스택 & 분석 과정 상세 기술서

> 제14회 산업통상부 공공데이터 활용 아이디어 공모전 | 제품 및 서비스 개발 부문  
> 최종 수정: 2026-06-29 (v2.0 — 12개 핵심 업종 심화 설계 반영)

---

## 목차

1. [전체 시스템 아키텍처 개요](#1-전체-시스템-아키텍처-개요)
2. [레이어 1 — 데이터 수집 & ETL 파이프라인](#2-레이어-1--데이터-수집--etl-파이프라인)
3. [레이어 2 — AI 분석 엔진 (핵심)](#3-레이어-2--ai-분석-엔진-핵심)
4. [레이어 3 — 서비스 API & 프론트엔드](#4-레이어-3--서비스-api--프론트엔드)
5. [분석 과정 Step-by-Step](#5-분석-과정-step-by-step)
6. [기술 스택 전체 요약표](#6-기술-스택-전체-요약표)
7. [핵심 업종 12개 설계 명세](#7-핵심-업종-12개-설계-명세)

---

## 1. 전체 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                        Factory AI Navi                          │
├──────────────────┬──────────────────────┬───────────────────────┤
│    LAYER 1       │       LAYER 2        │       LAYER 3         │
│  데이터 수집     │    AI 분석 엔진      │    서비스 레이어      │
│                  │                      │                       │
│ 공공데이터 API   │  LangGraph 오케스트  │  REST API (FastAPI)   │
│ ETL 파이프라인   │  레이터              │  Web Dashboard        │
│ PostgreSQL DB    │  RAG Engine          │  (Next.js 14)         │
│ Airflow 스케줄   │  ROI 계산 모델       │  PDF 레포트 생성      │
│                  │  매칭 알고리즘       │  알림 서비스 (카카오) │
└──────────────────┴──────────────────────┴───────────────────────┘
```

### 핵심 설계 원칙

- **데이터 주도**: 모든 진단 결과는 공공데이터 기반 수치 근거 제시 (hallucination 방지)
- **에이전트 자율성**: 업종·공정만 입력하면 진단→분석→추천→레포트 생성까지 자율 수행
- **12개 업종 심화**: 47개 전체 업종 피상적 커버 대신 12개 핵심 업종 엄격한 벤치마크 구축
- **확장 가능한 RAG**: 업종별 케이스 DB를 지속 학습·업데이트하여 정확도 점진 향상

---

## 2. 레이어 1 — 데이터 수집 & ETL 파이프라인

### 2.1 핵심 업종 12개 & 벤치마크 DB 설계

v2.0부터 MVP를 3개 업종에서 12개 핵심 업종으로 확대하되, 각 업종의 수치를 엄격하게 설계합니다.

**그룹 A — 뿌리업종 6개** (정부 특별 지원 대상, AI 도입률 최저)

| KSIC | 업종명 | 핵심 공정 | 주요 AI 적용 | 특이사항 |
|------|--------|-----------|-------------|---------|
| C243 | 주조 | 용해→주입→냉각→탈사→검사 | 용탕온도 AI제어, 기포결함 비전검사 | 에너지 비중 18% 최고 수준 |
| C251 | 금형 | 설계→가공→열처리→측정→검사 | 공구마모 예측, 치수 비전검사 | 뿌리업종 중 사업체 수 1위 |
| C259 | 소성가공 | 가열→단조/압연→트리밍→검사 | 소재온도 프로파일 AI, 금형마모 예측 | 에너지+불량 이중 문제 |
| C289 | 용접 | 준비→용접→비파괴검사→후처리 | 비드품질 실시간 비전, 기공/균열 탐지 | 품질이 작업자 숙련도에 100% 의존 |
| C301 | 표면처리 | 전처리→도금/도장→검사→폐수처리 | 도막두께 AI측정, 약품농도 자동제어 | 환경규제+품질 이중 압박 |
| C302 | 열처리 | 전처리→로 처리→냉각→경도검사 | 로 온도 프로파일 최적화, 경도 예측 | 에너지 매출 대비 28% — ROI 최대 |

**그룹 B — 일반 제조업 6개** (사업체 수 많고 AI 수요 높음)

| KSIC | 업종명 | 핵심 공정 | 주요 AI 적용 | 특이사항 |
|------|--------|-----------|-------------|---------|
| C10 | 식품제조 | 원료→가공→포장→HACCP→출하 | 이물검출 비전, 중량편차 AI모니터링 | HACCP 규제로 AI 도입 명분 명확 |
| C22 | 사출성형 | 수지투입→사출→냉각→취출→검사 | 웰드라인/기포 비전, 수지온도·압력 제어 | 불량률 高, 에너지 낭비 高 |
| C25 | 금속가공 | 소재→절삭/프레스→조립→검사 | 공구마모 예측유지보수, 치수 자동측정 | 국내 중소제조업 사업체 수 1위 |
| C26 | 전자부품 | 기판→SMT 실장→납땜→AOI→완성 | AOI 연계 AI 불량분류, 납땜 비전검사 | AI 도입 성공사례 多 → RAG 케이스 풍부 |
| C29 | 산업기계 | 부품가공→조립→성능시험→출하 | 조립 토크/규격 AI모니터, 납기 수요예측 | 스마트공장 2.0 주요 타겟 |
| C30 | 자동차부품 | 프레스/사출→도장→조립→외관검사 | 외관 비전검사, Cpk 실시간 공정능력 | IATF16949 납품 품질기준 엄격 |

### 2.2 벤치마크 수치 설계 (kiat_industry_stats 테이블 24행)

기업 규모: `small` = 50인 미만 / `medium` = 50~300인 미만

```
KSIC │ 규모   │ 불량% │ 가동% │ AI%  │ 인건비  │ 에너지% │ 로봇% │ ROI월 │ 생산액  │ 재료비%
     │        │       │       │      │(만원/년)│         │       │       │(만원/년)│
─────┼────────┼───────┼───────┼──────┼─────────┼─────────┼───────┼───────┼─────────┼────────
C243 │ small  │  5.2  │  62   │  1.5 │  3,600  │   18    │   3   │  36   │  2,800  │   55
C243 │ medium │  3.8  │  72   │  3.0 │  4,200  │   15    │   8   │  30   │  4,000  │   58
C251 │ small  │  3.0  │  68   │  2.0 │  4,100  │    8    │   2   │  30   │  3,200  │   30
C251 │ medium │  1.8  │  78   │  5.0 │  4,800  │    7    │   6   │  24   │  4,800  │   32
C259 │ small  │  3.5  │  65   │  1.5 │  3,700  │   14    │   2   │  36   │  2,600  │   50
C259 │ medium │  2.2  │  74   │  3.5 │  4,300  │   12    │   6   │  30   │  3,800  │   52
C289 │ small  │  4.2  │  70   │  2.0 │  3,500  │    7    │   5   │  28   │  2,400  │   45
C289 │ medium │  2.8  │  78   │  4.5 │  4,100  │    6    │  15   │  24   │  3,500  │   48
C301 │ small  │  3.3  │  67   │  1.0 │  3,400  │   20    │   1   │  40   │  2,200  │   35
C301 │ medium │  2.0  │  75   │  2.5 │  3,900  │   17    │   3   │  32   │  3,200  │   38
C302 │ small  │  2.5  │  72   │  1.5 │  3,600  │   28    │   1   │  36   │  2,800  │   25
C302 │ medium │  1.5  │  80   │  3.5 │  4,200  │   24    │   2   │  28   │  4,100  │   28
C10  │ small  │  1.8  │  75   │  2.5 │  3,100  │   10    │   2   │  28   │  2,800  │   65
C10  │ medium │  0.9  │  82   │  6.0 │  3,800  │    9    │   5   │  22   │  4,100  │   68
C22  │ small  │  4.0  │  66   │  4.0 │  3,400  │   11    │   4   │  26   │  2,600  │   55
C22  │ medium │  2.5  │  76   │  9.0 │  4,000  │    9    │  12   │  20   │  3,800  │   58
C25  │ small  │  3.2  │  68   │  3.5 │  3,800  │    9    │   5   │  24   │  3,200  │   45
C25  │ medium │  1.8  │  78   │ 11.0 │  4,400  │    8    │  16   │  18   │  4,700  │   48
C26  │ small  │  1.2  │  80   │ 12.0 │  4,100  │    6    │   8   │  18   │  4,800  │   52
C26  │ medium │  0.5  │  87   │ 22.0 │  5,000  │    5    │  22   │  14   │  7,200  │   55
C29  │ small  │  2.0  │  72   │  4.5 │  4,100  │    5    │   4   │  26   │  3,800  │   40
C29  │ medium │  1.2  │  80   │  9.0 │  4,800  │    5    │  12   │  20   │  5,600  │   42
C30  │ small  │  0.8  │  84   │ 10.0 │  4,200  │    7    │  15   │  18   │  4,500  │   50
C30  │ medium │  0.3  │  90   │ 20.0 │  5,100  │    6    │  35   │  12   │  7,000  │   53
```

> **데이터 출처**: 인건비 → KOSIS 사업체노동력조사 / 인당생산액 → KIAT 산업기술통계집 p.169 /
> 불량률·가동률·AI도입률·에너지비율 → 연구 기반 추정값 (data_source: 'KIAT_MANUAL_2024')

### 2.3 데이터 소스 매핑

| 지표 | 소스 파일 | 위치 | 수집 방식 |
|-----|---------|------|---------|
| 인당 인건비, 근로시간 | KOSIS 사업체노동력조사 Excel | A~C열 (업종/규모/측정값) | KOSIS 재다운로드 (C26/C29/C30/100~299인 추가) |
| 인당 생산액 (노동생산성) | 2025년 산업기술통계집.pdf | PART3 p.169 (4-27항) | PDF 파싱 or 수동 추출 |
| 로봇 도입 현황 | 2024년 기준 로봇산업 실태조사.pdf | p.52 [표 4-11], p.62 [표 4-22] | 적용산업별 생산·출하 → 간접 추정 |
| 불량률, 가동률 | 없음 (별도 수집 필요) | - | 수동 입력 (연구 기반 추정) |
| AI 도입률 | 없음 (별도 수집 필요) | - | 수동 입력 (중기부 스마트공장 현황 참고) |
| 지원사업 공고 | KEIT 웹사이트 + 국가R&D API | - | 실시간 수집 (매일 갱신) |

### 2.4 KOSIS Excel 재다운로드 사양

```
URL: https://kosis.kr/statHtml/statHtml.do?orgId=118&tblId=DT_118N_MON051

체크 항목:
  [업종] C10 식료품 / C22 고무 및 플라스틱제품 / C25 금속가공제품
         C26 전자부품 / C29 기타 기계 및 장비 / C30 자동차 및 트레일러  ← 추가 필요

  [규모] 1~4인 / 5~9인 / 10~29인 / 30~99인                     ← 기존
         100~299인                                              ← 추가 필요

  ※ 뿌리업종(C243/C251/C259/C289/C301/C302)은 이 표에 없음
     → 인건비는 상위 업종(C24/C25/C28/C30) 참고값으로 대체
```

### 2.5 ETL 파이프라인 구성

```
[수집 단계]
공공데이터 API 호출 / 파일 다운로드 / PDF 파싱
       ↓
[전처리 단계]
· 업종 코드 표준화 (KSIC 10차 기준 통일)
· 기업 규모 매핑: KOSIS 인원 구간 → small/medium
  (1~4인, 5~9인, 10~29인, 30~49인 → small)
  (50~99인, 100~299인              → medium)
· 결측값 처리 (업종 평균값 imputation)
· 단위 통일 (억원→만원, 천㎡→㎡)
       ↓
[적재 단계]
PostgreSQL (정형 데이터) + pgvector (임베딩)
       ↓
[스케줄링]
Apache Airflow DAG 자동 실행
```

### 2.6 수집 대상 데이터셋 전체

| 기관 | 데이터셋 | 수집 방식 | 갱신 주기 | 활용 목적 |
|-----|---------|---------|---------|---------|
| KOSIS | 산업/규모별 임금 및 근로시간 | 파일 다운로드 | 연 1회 | 업종별 인건비 벤치마크 |
| KIAT | 산업기술통계집 (인당 노동생산성) | PDF 파싱 | 연 1회 | 인당 생산액 벤치마크 |
| KIRIA | 로봇산업 실태조사 (적용산업별) | PDF 파싱 | 연 1회 | 로봇 도입 현황 참고 |
| KEIT | 사업공고 현황 (R&D 과제 목록) | 파일+크롤링 | 주 1회 | 정부지원사업 매칭 |
| 국가R&D | 과제검색 API | Open API | 실시간 | R&D 사업 매칭 |
| 중기부 | 스마트공장 구축기업 수준 DB | 파일 | 반기 | AI 도입 단계 파악 |
| 소진공 | 뿌리업종 업체 현황·지원금 목록 | 파일+API | 반기 | 뿌리업종 특화 지원 |

---

## 3. 레이어 2 — AI 분석 엔진 (핵심)

### 3.1 전체 AI 아키텍처

```
사용자 입력 (업종 / 공정 단계 / 설비 노후도 / 기업 규모)
       ↓
┌──────────────────────────────────────────────┐
│           LangGraph 멀티 에이전트            │
│                                              │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │ 진단 에이전트│    │  매칭 에이전트   │   │
│  │  (3단계)     │───▶│ (지원사업 검색)  │   │
│  └──────┬───────┘    └──────────────────┘   │
│         │                                    │
│  ┌──────▼───────┐    ┌──────────────────┐   │
│  │ RAG 검색    │    │  ROI 계산 에이전트│   │
│  │  엔진       │───▶│                   │   │
│  └─────────────┘    └──────────────────┘   │
└──────────────────────────────────────────────┘
       ↓
Claude API (claude-sonnet-4-6) — 최종 레포트 생성
```

### 3.2 RAG (Retrieval-Augmented Generation) 엔진

공정 진단의 정확도를 높이기 위해 12개 업종별 AI 도입 성공·실패 케이스 DB를 구축하고,
사용자 입력과 유사한 케이스를 검색한 뒤 LLM에게 컨텍스트로 제공합니다.

#### RAG 파이프라인 상세

```
[오프라인 - 문서 인덱싱]

① 소스 문서 수집 (12개 업종 × 3건 이상 = 36건+)
   · 뿌리업종 AI 도입 성공/실패 사례 (소진공·산업부 발행)
   · KIAT 산업기술통계 업종별 리포트
   · 로봇진흥원 실태조사 세부 데이터
   · 제조 공정 개선 가이드라인 (산업부 발행)
   · 스마트공장 우수사례집 (중기부)
       ↓
② 청킹 (Chunking)
   · 단위: 업종별 공정 케이스 1건 ≈ 1 청크
   · 평균 청크 크기: 500~800 토큰
   · 메타데이터: industry_code / process_type / ai_type / effect_pct / roi_months
       ↓
③ 임베딩 & 벡터 저장
   · 임베딩 모델: text-embedding-3-small (OpenAI)
   · 벡터DB: pgvector (PostgreSQL 확장)
   · 인덱스: HNSW (m=16, ef_construction=64) — 근사 최근접 이웃 검색

[온라인 - 쿼리 처리]
사용자 입력 ▶ 쿼리 임베딩 생성
       ↓
벡터 유사도 검색 (코사인 유사도 Top-10)
       ↓
리랭킹 (BM25 키워드 + 벡터 유사도 하이브리드: 60/40)
       ↓
검색된 케이스 컨텍스트 + 사용자 입력 ▶ LLM 프롬프트 구성
       ↓
Claude API 호출 ▶ 구조화된 진단 결과 JSON 반환
```

```python
from langchain.vectorstores import PGVector
from langchain.embeddings import OpenAIEmbeddings
from langchain.retrievers import BM25Retriever, EnsembleRetriever

vectorstore = PGVector(
    connection_string=DATABASE_URL,
    embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    collection_name="manufacturing_cases"
)

# 하이브리드 검색 (벡터 60% + BM25 키워드 40%)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
bm25_retriever   = BM25Retriever.from_documents(docs)
ensemble = EnsembleRetriever(
    retrievers=[vector_retriever, bm25_retriever],
    weights=[0.6, 0.4]
)

def retrieve_cases(user_input: dict) -> list:
    query = f"{user_input['industry']} {user_input['process']} AI 적용 사례"
    return ensemble.get_relevant_documents(query)[:5]
```

### 3.3 공정 진단 AI 에이전트 (3단계)

사용자가 입력한 기업 프로파일을 기반으로 3단계 분석을 수행합니다.

#### Step A — 동종업계 벤치마크 분석

```python
def benchmark_analysis(industry_code: str, company_size: str) -> dict:
    """
    입력: 업종코드 (KSIC), 기업 규모 (small/medium)
    출력: 동종업계 대비 생산성 갭 분석
    """
    peer_data = db.query("""
        SELECT avg_production_per_person,   -- 인당 생산액
               avg_defect_rate,             -- 평균 불량률
               avg_operating_rate,          -- 평균 가동률
               ai_adoption_rate,            -- AI 도입률
               avg_energy_cost_ratio,       -- 에너지 비용 비율
               robot_adoption_rate,         -- 로봇 도입률
               avg_robot_roi_months         -- 로봇 ROI 회수기간
        FROM kiat_industry_stats
        WHERE industry_code = %s
          AND company_size  = %s
    """, (industry_code, company_size))

    return {
        "peer_avg":     peer_data,
        "gap_analysis": calculate_gap(company_data, peer_data),
        "percentile":   calculate_percentile(company_data, peer_data)
    }
```

**분석 예시 출력 (금속가공 C25 / small)**:
```json
{
  "industry": "금속가공 (C25)",
  "benchmark": {
    "인당_생산액_동종평균": "3,200만원/년",
    "귀사_추정":           "2,450만원/년",
    "갭":                  "-24% (하위 35% 구간)",
    "불량률_동종평균":     "3.2%",
    "에너지비용_동종평균": "생산액의 9%"
  },
  "ai_도입시_개선가능": {
    "불량률_감소":   "1.0~1.5%p (AI 비전검사 기준)",
    "가동률_향상":   "7~12%p (예측유지보수 기준)",
    "에너지절감":    "5~9% (공정최적화 기준)"
  }
}
```

#### Step B — AI 적용 우선순위 도출 (업종별 특화 파라미터)

```python
# 업종별 ROI 파라미터 (constants.py에 정의)
INDUSTRY_ROI_PARAMS = {
    "C243": {  # 주조
        "best_ai": ["process_control", "vision_inspection"],
        "labor_reduction_rate":  0.08,
        "energy_reduction_rate": 0.12,  # 에너지 18% → 12% 절감 효과
        "defect_improvement":    1.5,   # 불량률 5.2% → 3.7%p 개선 가능
    },
    "C302": {  # 열처리 — 에너지 ROI 최대
        "best_ai": ["energy_optimization", "process_control"],
        "labor_reduction_rate":  0.05,
        "energy_reduction_rate": 0.18,  # 에너지 28% → 18% 절감 (가장 큰 효과)
        "defect_improvement":    0.8,
    },
    "C10": {   # 식품 — HACCP 연계
        "best_ai": ["vision_inspection", "quality_control"],
        "labor_reduction_rate":  0.10,
        "energy_reduction_rate": 0.06,
        "defect_improvement":    0.7,   # 1.8% → 1.1%p 개선
    },
    "C26": {   # 전자부품 — 고정밀 AI 비전
        "best_ai": ["vision_inspection", "quality_control"],
        "labor_reduction_rate":  0.12,
        "energy_reduction_rate": 0.04,
        "defect_improvement":    0.4,   # 1.2% → 0.8%p (이미 낮은 불량률)
    },
    "C30": {   # 자동차부품 — 외관검사 + 공정능력
        "best_ai": ["vision_inspection", "quality_control", "robot_automation"],
        "labor_reduction_rate":  0.15,
        "energy_reduction_rate": 0.05,
        "defect_improvement":    0.3,   # 0.8% → 0.5%p (IATF 기준)
    },
    # ... 나머지 7개 업종 동일 패턴
}
```

```python
SYSTEM_PROMPT = """
당신은 중소 제조기업 AI 도입 전문 컨설턴트입니다.
주어진 기업 데이터와 동종업계 케이스를 분석하여
다음 형식으로 AI 적용 우선순위를 제시하세요:

[출력 형식]
{
  "priority_1": {
    "ai_type": "예측유지보수 (Predictive Maintenance)",
    "target_process": "CNC 가공 공정",
    "expected_effect": "설비 다운타임 40% 감소",
    "implementation_period": "3~6개월",
    "estimated_cost": "3,000~5,000만원",
    "reference_case": "동종업계 A사 적용 사례"
  },
  ...
}

반드시 공공데이터 기반 수치를 근거로 제시하세요.
"""
```

#### Step C — ROI 시뮬레이션 모델

```python
def calculate_roi(company_profile: dict, ai_recommendation: dict) -> dict:
    """
    로봇진흥원 실태조사 + 고용노동부 인건비 통계 기반
    AI 도입 투자 수익률 자동 계산
    """
    params = INDUSTRY_ROI_PARAMS[company_profile["industry_code"]]

    labor_cost   = peer_data["avg_labor_cost_per_person"] * company_profile["headcount"]
    energy_cost  = peer_data["avg_energy_cost_ratio"] * company_profile["annual_revenue"]
    defect_value = peer_data["avg_defect_rate"] * company_profile["annual_production_value"]

    # 연간 절감액 계산
    labor_savings  = labor_cost  * params["labor_reduction_rate"]
    energy_savings = energy_cost * params["energy_reduction_rate"]
    defect_savings = params["defect_improvement"] / 100 * company_profile["annual_production_value"]

    total_annual_saving = labor_savings + energy_savings + defect_savings

    # 정부지원금 반영
    gov_subsidy     = get_applicable_subsidy(company_profile)  # KEIT 매칭
    net_investment  = ai_recommendation["implementation_cost"] - gov_subsidy

    return {
        "연간_절감액":    f"{total_annual_saving:,.0f}만원",
        "투자_회수_기간": f"{net_investment / total_annual_saving * 12:.1f}개월",
        "3년_순이익":     f"{total_annual_saving * 3 - net_investment:,.0f}만원",
        "정부지원금":     f"{gov_subsidy:,.0f}만원 (자부담 {ai_recommendation['co_funding_rate']*100:.0f}%)",
        "근거_데이터":    ["KIAT 산업기술통계", "고용노동부 인건비 통계", "로봇진흥원 실태조사"]
    }
```

**ROI 계산 예시 출력 (열처리 C302 / 50인 / 에너지 최적화 AI)**:
```
============================================================
Factory AI Navi — AI 도입 ROI 분석 결과
[ 열처리 | 50인 규모 | 에너지 최적화 AI 적용 ]
============================================================

연간 예상 절감액
├ 인건비 절감:    800만원 (간접 인력 1인 재배치)
├ 설비 다운타임:  1,200만원 (비계획 중단 30% 감소)
└ 에너지 절감:    3,360만원 (매출 대비 28% → 20%, 연매출 4.2억 기준)
  소계:           5,360만원/년

투자 비용
├ 총 구축비용:   8,000만원
├ 정부지원금:   -4,000만원 (에너지절감 스마트공장 지원)
└ 실 자부담:     4,000만원

투자 수익성
├ 투자 회수 기간: 8.9개월
├ 3년 순이익:    12,080만원
└ ROI (3년):     302%

근거 데이터
  KIAT 산업기술통계 / 고용노동부 인건비 통계 / 로봇진흥원 실태조사 2024
============================================================
```

### 3.4 정부지원사업 매칭 에이전트

```python
class SubsidyMatchingAgent:
    """
    KEIT 사업공고 + 국가R&D API + 중기부 스마트공장 지원사업
    실시간 수집·분류 후 기업 프로파일과 매칭
    """
    def match(self, company_profile: dict, diagnosis: dict) -> list:
        # 기업 프로파일 + 진단 결과 → 임베딩 벡터
        company_vector = embed(
            f"{company_profile['industry']} "
            f"{company_profile['size']} "
            f"{diagnosis['ai_type']}"
        )
        # 코사인 유사도 기반 매칭 (임계값 0.75)
        matches = []
        for subsidy in self.subsidies:
            score = cosine_similarity(company_vector, subsidy["vector"])
            if score > 0.75:
                matches.append({
                    "사업명":   subsidy["name"],
                    "지원금액": subsidy["max_amount"],
                    "신청마감": subsidy["deadline"],
                    "자부담비율": subsidy["co_funding_rate"],
                    "매칭점수": f"{score:.0%}",
                    "신청링크": subsidy["apply_url"]
                })
        # 마감 D-7 이내 긴급 공고 우선 정렬
        return sorted(matches, key=lambda x: (x["마감임박"], -float(x["매칭점수"][:-1])))[:5]
```

---

## 4. 레이어 3 — 서비스 API & 프론트엔드

### 4.1 FastAPI 백엔드 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | /api/v1/diagnose | 스트리밍 진단 응답 (SSE) |
| GET | /api/v1/subsidies | 현재 신청 가능 지원사업 목록 |
| POST | /api/v1/roi-simulate | ROI 시뮬레이션 |
| GET | /api/v1/report/{id}/pdf | PDF 레포트 다운로드 |

### 4.2 사용자 입력 화면 (Step 1)

```
업종 선택 (12개):
  뿌리업종 그룹: 주조 / 금형 / 소성가공 / 용접 / 표면처리 / 열처리
  일반 제조업:   식품 / 사출성형 / 금속가공 / 전자부품 / 산업기계 / 자동차부품

기업 규모:
  소기업 (50인 미만) / 중기업 (50~300인)

공정 정보:
  현재 불량률 (%) / 설비 가동률 (%) / 설비 노후도 (년) / 연간 생산액 (억원)
  에너지 비용 비율 (%) / 종업원 수 (인)

현재 가장 큰 문제 (복수 선택):
  □ 불량률 높음  □ 설비 자주 고장  □ 에너지 비용  □ 품질 균일성
  □ 납기 지연    □ 인력 부족       □ 재료비 과다
```

### 4.3 진단 결과 대시보드 (Step 3)

```
┌─────────────────────────────────────────────────────┐
│  [레이더 차트]              [벤치마크 갭 분석]       │
│  불량률 / 가동률 /           내 회사 vs 동종업계     │
│  에너지 / AI도입률 /         하위 35% 구간 위치      │
│  인당생산액                                          │
├─────────────────────────────────────────────────────┤
│  [AI 적용 우선순위 Top3]                             │
│  1위: 예측유지보수 — CNC 공정 / 회수 8.9개월        │
│  2위: AI 비전검사 — 출하검사 / 회수 14개월          │
│  3위: 에너지 최적화 — 로 공정 / 회수 12개월         │
├─────────────────────────────────────────────────────┤
│  [ROI 그래프]               [정부지원사업 Top5]      │
│  3년 누적 순이익 그래프      마감일 / 지원금 / 자부담│
│                              신청 바로가기 버튼       │
└─────────────────────────────────────────────────────┘
```

---

## 5. 분석 과정 Step-by-Step

```
STEP 1: 기업 입력
  업종(12개 중 선택) + 공정단계 + 설비노후도 + 기업규모 + 현재 KPI 수치

STEP 2: 동종업계 벤치마크 분석
  kiat_industry_stats 조회 → 갭 분석 → 하위 몇 % 구간 산출

STEP 3: RAG 케이스 검색
  12개 업종 × 3건+ AI 도입 케이스 DB → 유사 케이스 Top5 검색

STEP 4: Claude AI 진단
  벤치마크 + 케이스 컨텍스트 → Claude 프롬프트 → AI 우선순위 Top3 JSON

STEP 5: ROI 시뮬레이션
  업종별 ROI 파라미터 + 정부지원금 매칭 → 투자회수기간 / 3년 순이익

STEP 6: 지원사업 매칭
  벡터 유사도 기반 Top5 매칭 → 마감 D-7 긴급 우선 정렬

STEP 7: 레포트 생성
  전체 결과 → PDF 레포트 → 다운로드 / 카카오 알림
```

---

## 6. 기술 스택 전체 요약표

| 영역 | 기술 | 버전/모델 |
|-----|-----|---------|
| **언어** | Python | 3.11+ |
| **AI LLM** | Claude claude-sonnet-4-6 (Anthropic) | claude-sonnet-4-6 |
| **임베딩** | text-embedding-3-small (OpenAI) | - |
| **에이전트 프레임워크** | LangGraph | 0.1+ |
| **RAG 프레임워크** | LangChain | 0.2+ |
| **벡터DB** | pgvector (PostgreSQL 확장) | 0.5+ |
| **RDB** | PostgreSQL (GCP Cloud SQL) | 15 |
| **ORM** | SQLAlchemy | 2.0+ |
| **ETL 스케줄러** | Apache Airflow | 2.9+ |
| **API 프레임워크** | FastAPI | 0.110+ |
| **프론트엔드** | Next.js 14 | 14.x |
| **차트** | Recharts | - |
| **PDF 생성** | ReportLab / WeasyPrint | - |
| **알림** | 카카오 알림톡 API | - |
| **컨테이너** | Docker + docker-compose | - |
| **CI/CD** | GitHub Actions | - |
| **클라우드** | GCP (Cloud Run + Cloud SQL) | - |
| **모니터링** | Sentry + GCP Cloud Monitoring | - |

---

## 7. 핵심 업종 12개 설계 명세

### 업종별 AI 적용 매트릭스

| KSIC | 업종 | 예측유지보수 | AI비전검사 | 에너지최적화 | 공정제어 | 품질관리AI | 로봇자동화 |
|------|------|:-----------:|:---------:|:-----------:|:-------:|:---------:|:---------:|
| C243 | 주조 | ○ | ● | ● | ● | ○ | - |
| C251 | 금형 | ● | ● | - | ○ | ○ | - |
| C259 | 소성가공 | ● | - | ○ | ● | - | ○ |
| C289 | 용접 | - | ● | - | ● | ○ | ● |
| C301 | 표면처리 | - | ○ | ● | ● | ○ | - |
| C302 | 열처리 | - | - | ● | ● | ○ | - |
| C10 | 식품 | - | ● | ○ | - | ● | - |
| C22 | 사출성형 | ● | ● | ○ | ● | - | - |
| C25 | 금속가공 | ● | ● | - | ○ | - | ○ |
| C26 | 전자부품 | - | ● | - | - | ● | ○ |
| C29 | 산업기계 | ● | - | - | ● | - | ○ |
| C30 | 자동차부품 | - | ● | - | ● | ● | ● |

> ● = 최우선 적용 / ○ = 차순위 적용 / - = 해당 없음

### 뿌리업종 특화 처리

뿌리업종 6개(C243/C251/C259/C289/C301/C302)는 소진공(SBC) 뿌리업종 특화 지원사업과
우선 매칭합니다. 일반 지원사업 매칭 전에 뿌리업종 전용 공고를 먼저 검색합니다.

```python
def get_applicable_subsidy(company_profile: dict) -> list:
    subsidies = []
    # 뿌리업종은 전용 지원사업 우선 검색
    if company_profile["industry_code"] in ROOTS_INDUSTRY_CODES:
        subsidies += search_roots_industry_subsidies(company_profile)
    # 일반 지원사업 검색
    subsidies += search_general_subsidies(company_profile)
    return subsidies[:5]
```

---

*작성: Factory AI Navi Team | v2.0 | 2026-06-29*
*이 문서를 PDF로 변환하려면: `pandoc Factory_AI_Navi_기술스택.md -o Factory_AI_Navi_기술스택.md.pdf --pdf-engine=weasyprint`*
