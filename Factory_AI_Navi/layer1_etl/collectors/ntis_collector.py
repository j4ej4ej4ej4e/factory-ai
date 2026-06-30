"""
collectors/ntis_collector.py
============================
Factory AI Navi — 국가R&D 과제검색 API (NTIS) 수집기

데이터: 국가과학기술지식정보서비스(NTIS) R&D 과제
  - 수집 방식: Open API (실시간)
  - API: https://apis.data.go.kr/B552735/rdTrnsInfo/getRdTrnsInfo
  - 활용: 정부 R&D 지원사업 매칭

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# NTIS API 설정 (API 키 수령 후 .env 에 NTIS_API_KEY 입력)
#
# 신청: https://www.ntis.go.kr → API 활용 신청
# 문서: https://apis.data.go.kr → B552735 (과학기술정보통신부)
# ──────────────────────────────────────────────────────────────────────────────

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import NTIS_API_KEY, NTIS_BASE_URL, logger
from layer1_etl.constants import MVP_INDUSTRY_CODES


class NtisCollector(BaseCollector):
    """
    국가R&D 과제검색 API 수집기.

    실제 모드: NTIS Open API 호출 (제조업 관련 R&D 과제 검색)
    Mock 모드: 가상 R&D 과제 3건 반환
    """

    def __init__(self):
        super().__init__(source_name="NTIS")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: NTIS API 호출.
        NTIS_API_KEY가 PLACEHOLDER 상태면 mock으로 폴백.
        """
        if "PLACEHOLDER" in NTIS_API_KEY:
            self.logger.warning(
                "[NTIS] API 키 미설정 — mock 데이터로 대체. "
                ".env 에 NTIS_API_KEY 를 설정하세요."
            )
            return self.get_mock_data()

        # ─────────────────────────────────────────────────────────────
        # 실제 API 호출 (API 키 준비 후 자동 활성화)
        # ─────────────────────────────────────────────────────────────
        params = {
            "serviceKey": NTIS_API_KEY,
            "numOfRows":  100,
            "returnType": "json",
            # "prjNm":    "제조",        # 과제명 키워드 검색 (선택)
            # "techCode": "C25",         # 기술분야 코드 (선택)
        }

        all_items = self._paginated_get(
            url=NTIS_BASE_URL,
            params=params,
            page_param="pageNo",
            size_param="numOfRows",
            page_size=100,
        )

        if not all_items:
            return self.get_mock_data()

        return self._normalize(all_items)

    def get_mock_data(self) -> pd.DataFrame:
        """가상 국가R&D 과제 데이터 3건"""
        from datetime import date, timedelta
        today = date.today()

        rows = [
            {
                "subsidy_id":            "NTIS-2026-M001",
                "source":                "NTIS",
                "program_name":          "제조공정 AI 비전검사 기술 개발",
                "program_category":      "R&D",
                "target_industry_codes": "C25,C22",
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "vision_inspection",
                "max_support_amount":    25000,
                "min_support_amount":    5000,
                "co_funding_rate":       0.4,
                "application_start":     today - timedelta(days=7),
                "application_end":       today + timedelta(days=90),
                "announcement_date":     today - timedelta(days=7),
                "apply_url":             "https://www.ntis.go.kr",
                "description":           "금속·사출 공정 AI 비전검사 시스템 개발 R&D",
                "requirements":          "중소기업 기술개발 역량 보유",
                "is_active":             True,
            },
            {
                "subsidy_id":            "NTIS-2026-M002",
                "source":                "NTIS",
                "program_name":          "식품제조 스마트 품질관리 AI 플랫폼",
                "program_category":      "R&D",
                "target_industry_codes": "C10",
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "quality_control",
                "max_support_amount":    15000,
                "min_support_amount":    3000,
                "co_funding_rate":       0.45,
                "application_start":     today - timedelta(days=14),
                "application_end":       today + timedelta(days=76),
                "announcement_date":     today - timedelta(days=14),
                "apply_url":             "https://www.ntis.go.kr",
                "description":           "식품 제조 HACCP 연계 AI 실시간 품질 모니터링",
                "requirements":          "식품제조 허가 보유 기업",
                "is_active":             True,
            },
            {
                "subsidy_id":            "NTIS-2026-M003",
                "source":                "NTIS",
                "program_name":          "산업용 IoT·AI 융합 예측유지보수 기술",
                "program_category":      "R&D",
                "target_industry_codes": "C25,C24,C29",
                "target_company_sizes":  "medium,mid_large",
                "target_ai_types":       "predictive_maintenance",
                "max_support_amount":    40000,
                "min_support_amount":    10000,
                "co_funding_rate":       0.35,
                "application_start":     today - timedelta(days=3),
                "application_end":       today + timedelta(days=120),
                "announcement_date":     today - timedelta(days=3),
                "apply_url":             "https://www.ntis.go.kr",
                "description":           "IoT 센서 + AI 기반 설비 고장 예측 시스템 R&D",
                "requirements":          "기업부설연구소 보유, 제조업 영위",
                "is_active":             True,
            },
        ]
        df = pd.DataFrame(rows)
        self.logger.info("[NTIS] Mock R&D 과제 데이터: %d건", len(df))
        return df

    def _normalize(self, items: list[dict]) -> pd.DataFrame:
        """
        NTIS API 응답 → 표준 subsidies 컬럼으로 정규화.
        실제 API 응답 필드명 확인 후 매핑 수정 필요.
        """
        rows = []
        for item in items:
            rows.append({
                "subsidy_id":            item.get("prjNo", ""),
                "source":                "NTIS",
                "program_name":          item.get("prjNm", ""),
                "program_category":      "R&D",
                "target_industry_codes": item.get("indutyCode", ""),
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "",
                "max_support_amount":    self.safe_int(item.get("totBdgt"), 0),
                "min_support_amount":    None,
                "co_funding_rate":       None,
                "application_start":     None,
                "application_end":       None,
                "announcement_date":     None,
                "apply_url":             "https://www.ntis.go.kr",
                "description":           item.get("prjSumry", ""),
                "requirements":          "",
                "is_active":             True,
            })
        return pd.DataFrame(rows)
