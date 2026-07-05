"""
collectors/ksnpc_collector.py
=============================
Factory AI Navi — 한국산업단지공단(KSNPC) 수집기

데이터: 국가산업단지 산업동향정보 — 업종별 가동률/생산실적/수출실적
  - 수집 방식: 공공데이터포털(data.go.kr) 파일데이터 API (odcloud.kr), 월별 갱신
  - 활용: 업종별 생산성 비교 (avg_operating_rate 실측값)

odcloud.kr 데이터셋 3종 (namespace)
-----------------------------------
  15085895 : 업종별 가동률   (%)
  15085898 : 업종별 생산실적 (억원)
  15085899 : 업종별 수출실적 (백만달러)

각 namespace는 월별로 별도 UUID 엔드포인트를 가짐 (Swagger 카탈로그 참고).
공식 목록 API가 없어 최신월 UUID를 아래에 하드코딩 — 분기별로 갱신 필요.

업종 매핑 한계
--------------
이 데이터는 KSIC 세부코드가 아니라 10개 대분류(기계/전기전자/석유화학/
섬유의복/운송장비/음식료/철강/비금속/목재종이/기타)로만 제공됨.
우리 12개 KSIC 업종을 아래 CATEGORY_MAP으로 근사 매핑함 (완전 일치 아님).

작성일: 2026-04-28
버전: v2.0 (2026-07-05: odcloud.kr 실제 API 연동)
"""

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import KSNPC_API_KEY, KSNPC_BASE_URL, logger

# 최신월 UUID (2026-03-31 기준, https://infuser.odcloud.kr/oas/docs 참고)
LATEST_REFERENCE_MONTH = "2026-03"
UUID_OPERATING_RATE = "3582d2d0-6225-4bb9-a0bf-af93044529c5"   # 15085895
UUID_PRODUCTION     = "2225ede9-4f93-4b31-98c9-bf8a2e87c2a7"   # 15085898
UUID_EXPORT         = "4ecd5d39-19c6-480a-ac95-dc8b8b5b841b"   # 15085899

NAMESPACE_OPERATING_RATE = "15085895"
NAMESPACE_PRODUCTION     = "15085898"
NAMESPACE_EXPORT         = "15085899"

KSNPC_CATEGORIES = [
    "기계", "전기전자", "석유화학", "섬유의복", "운송장비",
    "음식료", "철강", "비금속", "목재종이", "기타",
]

# 우리 12개 KSIC 업종 → KSNPC 대분류 근사 매핑
CATEGORY_MAP: dict[str, str] = {
    "C243": "철강",     # 주조
    "C251": "기계",     # 금형
    "C259": "기계",     # 소성가공
    "C289": "기계",     # 용접
    "C301": "기타",     # 표면처리
    "C302": "철강",     # 열처리
    "C10":  "음식료",   # 식품제조
    "C22":  "석유화학", # 사출성형 (고무·플라스틱)
    "C25":  "기계",     # 금속가공
    "C26":  "전기전자", # 전자부품
    "C29":  "기계",     # 산업기계
    "C30":  "운송장비", # 자동차부품
}


class KsnpcCollector(BaseCollector):
    """
    한국산업단지공단 국가산업단지 산업동향정보(odcloud.kr) 수집기.

    실제 모드: 가동률/생산실적/수출실적 3개 API를 호출해 전국 산업단지
    데이터를 업종 대분류별로 집계(생산가중평균 가동률, 총생산·총수출)
    Mock 모드: API 키 미설정 시 MVP 3개 업종 가상 통계 반환
    """

    def __init__(self):
        super().__init__(source_name="KSNPC")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: odcloud.kr 3개 데이터셋 호출 → 업종 대분류별 집계 →
        우리 12개 KSIC 업종에 매핑.
        API 키 미설정 시 mock으로 폴백.
        """
        if "PLACEHOLDER" in KSNPC_API_KEY:
            self.logger.warning(
                "[KSNPC] API 키 미설정 — mock 데이터로 대체. "
                ".env 에 KSNPC_API_KEY 를 설정하세요."
            )
            return self.get_mock_data()

        try:
            rate_rows = self._fetch_odcloud(NAMESPACE_OPERATING_RATE, UUID_OPERATING_RATE)
            prod_rows = self._fetch_odcloud(NAMESPACE_PRODUCTION, UUID_PRODUCTION)
            export_rows = self._fetch_odcloud(NAMESPACE_EXPORT, UUID_EXPORT)
        except Exception as e:
            self.logger.error("[KSNPC] API 호출 실패 — mock 데이터로 대체: %s", e)
            return self.get_mock_data()

        category_stats = self._aggregate_by_category(rate_rows, prod_rows, export_rows)
        return self._to_industry_rows(category_stats)

    def _fetch_odcloud(self, namespace: str, uuid: str) -> list[dict]:
        """odcloud.kr 파일데이터 API 단건 호출 (전체 산업단지 행 반환)"""
        url = f"{KSNPC_BASE_URL}/{namespace}/v1/uddi:{uuid}"
        params = {"page": 1, "perPage": 100, "serviceKey": KSNPC_API_KEY}
        response = self._get(url, params=params)
        return response.json().get("data", [])

    def _aggregate_by_category(
        self, rate_rows: list[dict], prod_rows: list[dict], export_rows: list[dict],
    ) -> dict[str, dict]:
        """
        업종 대분류별 전국 집계.

        - 가동률: 생산실적(억원)으로 가중평균 (단순평균보다 대표성 있음)
        - 생산실적/수출실적: 전국 합계
        """
        prod_by_park = {row.get("산업단지"): row for row in prod_rows}
        stats = {cat: {"weighted_rate_sum": 0.0, "weight": 0.0,
                       "production": 0.0, "export": 0.0} for cat in KSNPC_CATEGORIES}

        for cat in KSNPC_CATEGORIES:
            rate_key = f"{cat}(퍼센트)"
            prod_key = f"{cat}(억원)"
            export_key = f"{cat}(백만달러)"

            for row in rate_rows:
                park = row.get("산업단지")
                rate = self.safe_float(row.get(rate_key))
                prod = self.safe_float(prod_by_park.get(park, {}).get(prod_key))
                if rate is None or prod is None or prod <= 0:
                    continue
                stats[cat]["weighted_rate_sum"] += rate * prod
                stats[cat]["weight"] += prod

            for row in prod_rows:
                val = self.safe_float(row.get(prod_key))
                if val is not None:
                    stats[cat]["production"] += val

            for row in export_rows:
                val = self.safe_float(row.get(export_key))
                if val is not None:
                    stats[cat]["export"] += val

        return stats

    def _to_industry_rows(self, category_stats: dict[str, dict]) -> pd.DataFrame:
        """
        업종 대분류 집계 → 우리 12개 KSIC 업종 행으로 변환.

        reference_year=2024로 고정 — seed_db.py가 심어둔 기존 24행(KSIC ×
        small/medium)과 동일한 키로 upsert되어 avg_operating_rate만 실데이터로
        갱신되도록 함 (규모별 구분이 없는 데이터라 두 규모 모두 동일값 적용).
        """
        rows = []
        for ksic_code, category in CATEGORY_MAP.items():
            cs = category_stats.get(category, {})
            weight = cs.get("weight", 0.0)
            operating_rate = (cs["weighted_rate_sum"] / weight) if weight > 0 else None

            for size in ("small", "medium"):
                rows.append({
                    "industry_code":               ksic_code,
                    "company_size":                size,
                    "reference_year":               2024,
                    "avg_operating_rate":           operating_rate,
                    "ksnpc_production_billion_krw": cs.get("production"),
                    "ksnpc_export_million_usd":     cs.get("export"),
                    "ksnpc_reference_month":        LATEST_REFERENCE_MONTH,
                    "raw_file_path":                None,
                })

        df = pd.DataFrame(rows)
        self.logger.info("[KSNPC] 실데이터 집계 완료: %d개 업종 (%s 기준)",
                          len(CATEGORY_MAP), LATEST_REFERENCE_MONTH)
        return df

    def get_mock_data(self) -> pd.DataFrame:
        """MVP 3개 업종 가상 산단 통계 (2024년 기준)"""
        rows = [
            {
                "industry_code":             "C25",
                "industry_name":             "금속가공",
                "company_size":              "medium",
                "reference_year":            2024,
                "avg_production_per_person": 4200,
                "avg_operating_rate":        78.0,
                "avg_defect_rate":           2.3,
                "avg_energy_cost_ratio":     8.2,
                "ai_adoption_rate":          12.0,
                "avg_labor_cost_per_person": 4200,
                "data_source":               "KSNPC_MOCK",
                "raw_file_path":             None,
            },
            {
                "industry_code":             "C10",
                "industry_name":             "식품제조",
                "company_size":              "medium",
                "reference_year":            2024,
                "avg_production_per_person": 3900,
                "avg_operating_rate":        80.0,
                "avg_defect_rate":           1.4,
                "avg_energy_cost_ratio":     9.8,
                "ai_adoption_rate":          10.0,
                "avg_labor_cost_per_person": 3900,
                "data_source":               "KSNPC_MOCK",
                "raw_file_path":             None,
            },
            {
                "industry_code":             "C22",
                "industry_name":             "사출성형",
                "company_size":              "medium",
                "reference_year":            2024,
                "avg_production_per_person": 3700,
                "avg_operating_rate":        75.0,
                "avg_defect_rate":           2.8,
                "avg_energy_cost_ratio":     8.9,
                "ai_adoption_rate":          14.0,
                "avg_labor_cost_per_person": 4000,
                "data_source":               "KSNPC_MOCK",
                "raw_file_path":             None,
            },
        ]
        df = pd.DataFrame(rows)
        self.logger.info("[KSNPC] Mock 산단 통계: %d건", len(df))
        return df
