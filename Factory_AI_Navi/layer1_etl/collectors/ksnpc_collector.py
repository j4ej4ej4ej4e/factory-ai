"""
collectors/ksnpc_collector.py
=============================
Factory AI Navi — 한국산업단지공단(KSNPC) 수집기

데이터: 국가산업단지 업종별 생산·수출·가동률, 전국 산단 현황통계
  - 수집 방식: Open API + 파일 다운로드 (분기 갱신)
  - 활용: 업종별 생산성 비교, 지역 산단 입지 분석

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# KSNPC API 설정 (API 키 수령 후 .env 에 KSNPC_API_KEY 입력)
#
# 신청: https://www.kicox.or.kr → 정보서비스 → 데이터 개방
# 문서: 한국산업단지공단 공공데이터 활용 가이드
# ──────────────────────────────────────────────────────────────────────────────

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import KSNPC_API_KEY, KSNPC_BASE_URL, logger


class KsnpcCollector(BaseCollector):
    """
    한국산업단지공단 Open API 수집기.

    실제 모드: KSNPC API 호출 (업종별 생산·수출·가동률)
    Mock 모드: MVP 3개 업종 가상 산단 통계 반환
    """

    def __init__(self):
        super().__init__(source_name="KSNPC")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: KSNPC Open API 호출.
        API 키 미설정 시 mock으로 폴백.
        """
        if "PLACEHOLDER" in KSNPC_API_KEY:
            self.logger.warning(
                "[KSNPC] API 키 미설정 — mock 데이터로 대체. "
                ".env 에 KSNPC_API_KEY 를 설정하세요."
            )
            return self.get_mock_data()

        # ─────────────────────────────────────────────────────────────
        # 실제 API 호출 (API 키 수령 후 자동 활성화)
        #
        # KSNPC API 엔드포인트 및 파라미터는 공식 가이드 문서 참조:
        # https://www.kicox.or.kr → 데이터 개방 → API 활용 가이드
        # ─────────────────────────────────────────────────────────────

        # params = {
        #     "serviceKey": KSNPC_API_KEY,
        #     "numOfRows":  100,
        #     "returnType": "json",
        #     "year":       2024,
        #     "indutyCode": "C25",   # 업종코드별 조회
        # }
        # items = self._paginated_get(KSNPC_BASE_URL + "/industryStats", params=params)
        # return self._normalize(items)

        self.logger.warning("[KSNPC] API 미구현 — mock 데이터 반환")
        return self.get_mock_data()

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

    def _normalize(self, items: list[dict]) -> pd.DataFrame:
        """
        KSNPC API 응답 → kiat_industry_stats 컬럼으로 정규화.
        실제 API 응답 필드명 확인 후 매핑 수정 필요.
        """
        rows = []
        for item in items:
            rows.append({
                "industry_code":             item.get("indutyCode", ""),
                "industry_name":             item.get("indutyNm", ""),
                "company_size":              "medium",
                "reference_year":            int(item.get("year", 2024)),
                "avg_production_per_person": self.safe_float(item.get("prdtnPerPerson")),
                "avg_operating_rate":        self.safe_float(item.get("oprRate")),
                "avg_defect_rate":           None,
                "avg_energy_cost_ratio":     None,
                "ai_adoption_rate":          None,
                "avg_labor_cost_per_person": None,
                "data_source":               "KSNPC",
                "raw_file_path":             None,
            })
        return pd.DataFrame(rows)
