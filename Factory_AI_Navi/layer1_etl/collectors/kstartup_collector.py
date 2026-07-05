"""
collectors/kstartup_collector.py
=================================
Factory AI Navi — 창업진흥원 K-Startup 사업공고 수집기

데이터: K-Startup(창업지원사업 통합공고) 지원사업 공고 정보
  - 수집 방식: Open API (실시간, data.go.kr 활용신청 승인키)
  - API: https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01
  - 활용: 정부 지원사업 매칭 (SubsidyMatchingAgent) — 기업마당(BIZINFO) 보완

기업마당(BIZINFO)과의 차이
--------------------------
K-Startup은 "창업" 중심 포털이라 예비창업자·초기 창업기업(업력 10년 미만) 대상
공고 비중이 매우 높다. 우리 서비스가 타겟하는 기존 중소 제조기업(종업원 30~50인,
기창업 다년차)과는 일부 안 맞을 수 있어 AI/제조 키워드로 한 번 더 필터링한다.

한계
----
- 대상 조건이 "업력"(창업 연차) 기준이라 우리 시스템의 "기업규모"(소/중기업)
  축과 다른 차원 — company_size는 보수적으로 넓게(small,medium) 잡음
- 지원금액·자부담률이 구조화 필드로 오지 않음 — bsnsSumryCn 격 필드인
  pbanc_ctnt 텍스트에서 정규식으로 최대한 추출, 실패 시 None

작성일: 2026-07-05
버전: v1.0
"""

from datetime import date, datetime

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import KSTARTUP_API_KEY, KSTARTUP_BASE_URL, logger
from layer1_etl.collectors.bizinfo_collector import RELEVANT_KEYWORDS, BizinfoCollector

PAGE_SIZE = 100
MAX_PAGES = 5


class KstartupCollector(BaseCollector):
    """
    창업진흥원 K-Startup 사업공고 API 수집기.

    실제 모드: getAnnouncementInformation01 호출 → AI/제조 키워드 필터링
    Mock 모드: API 키 미설정 시 가상 공고 반환
    """

    def __init__(self):
        super().__init__(source_name="KSTARTUP")

    def collect(self) -> pd.DataFrame:
        if "PLACEHOLDER" in KSTARTUP_API_KEY:
            self.logger.warning(
                "[KSTARTUP] API 키 미설정 — mock 데이터로 대체. "
                ".env 에 KSTARTUP_API_KEY 를 설정하세요."
            )
            return self.get_mock_data()

        try:
            raw_items = self._fetch_all()
        except Exception as e:
            self.logger.error("[KSTARTUP] API 호출 실패 — mock 데이터로 대체: %s", e)
            return self.get_mock_data()

        relevant = [item for item in raw_items if self._is_relevant(item)]
        self.logger.info(
            "[KSTARTUP] 조회 %d건 중 AI/제조 관련 %d건 필터링", len(raw_items), len(relevant)
        )

        if not relevant:
            return self.get_mock_data()

        return self._normalize(relevant)

    def _fetch_all(self) -> list[dict]:
        """최신순(공고번호 내림차순) 공고를 페이지네이션하며 수집"""
        endpoint = f"{KSTARTUP_BASE_URL}/getAnnouncementInformation01"
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            params = {
                "ServiceKey": KSTARTUP_API_KEY,
                "page":       page,
                "perPage":    PAGE_SIZE,
                "returnType": "json",
            }
            data = self._get_json(endpoint, params=params)
            page_items = data.get("data", [])
            if not page_items:
                break
            items.extend(page_items)
            if len(page_items) < PAGE_SIZE:
                break
        return items

    @staticmethod
    def _is_relevant(item: dict) -> bool:
        text = " ".join([
            item.get("biz_pbanc_nm", "") or "",
            item.get("pbanc_ctnt", "") or "",
        ])
        return any(kw in text for kw in RELEVANT_KEYWORDS)

    def _normalize(self, items: list[dict]) -> pd.DataFrame:
        rows = []
        for item in items:
            text = " ".join([item.get("biz_pbanc_nm", "") or "", item.get("pbanc_ctnt", "") or ""])

            start = self._parse_yyyymmdd(item.get("pbanc_rcpt_bgng_dt", ""))
            end   = self._parse_yyyymmdd(item.get("pbanc_rcpt_end_dt", ""))
            recruiting = (item.get("rcrt_prgs_yn") == "Y")
            is_active = recruiting and (end is None or end >= date.today())

            rows.append({
                "subsidy_id":            str(item.get("pbanc_sn", "")),
                "source":                "KSTARTUP",
                "program_name":          item.get("biz_pbanc_nm", ""),
                "program_category":      item.get("supt_biz_clsfc", ""),
                "target_industry_codes": BizinfoCollector._match_industries(text),
                "target_company_sizes":  "small,medium",
                "target_ai_types":       BizinfoCollector._match_ai_types(text),
                "max_support_amount":    BizinfoCollector._extract_amount(item.get("pbanc_ctnt", "") or ""),
                "min_support_amount":    None,
                "co_funding_rate":       BizinfoCollector._extract_rate(item.get("pbanc_ctnt", "") or ""),
                "application_start":     start,
                "application_end":       end,
                "announcement_date":     start,
                "apply_url":             item.get("detl_pg_url", ""),
                "description":           item.get("pbanc_ctnt", ""),
                "requirements":          item.get("aply_trgt_ctnt", "") or "",
                "is_active":             is_active,
            })

        df = pd.DataFrame(rows)
        self.logger.info("[KSTARTUP] 실공고 정규화 완료: %d건", len(df))
        return df

    @staticmethod
    def _parse_yyyymmdd(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return datetime.strptime(raw.strip()[:8], "%Y%m%d").date()
        except ValueError:
            return None

    def get_mock_data(self) -> pd.DataFrame:
        """API 키 미설정 시 가상 공고 1건 반환 (구조 검증용)"""
        today = date.today()
        rows = [{
            "subsidy_id":            "KSTARTUP-MOCK-0001",
            "source":                "KSTARTUP",
            "program_name":          "(Mock) 창업기업 AI 제조 스마트화 지원사업",
            "program_category":      "사업화",
            "target_industry_codes": "",
            "target_company_sizes":  "small,medium",
            "target_ai_types":       "process_control",
            "max_support_amount":    3000,
            "min_support_amount":    None,
            "co_funding_rate":       0.5,
            "application_start":     today,
            "application_end":       today,
            "announcement_date":     today,
            "apply_url":             "https://www.k-startup.go.kr",
            "description":           "KSTARTUP_API_KEY 미설정 상태의 mock 데이터",
            "requirements":          "",
            "is_active":             True,
        }]
        df = pd.DataFrame(rows)
        self.logger.info("[KSTARTUP] Mock 데이터: %d건", len(df))
        return df
