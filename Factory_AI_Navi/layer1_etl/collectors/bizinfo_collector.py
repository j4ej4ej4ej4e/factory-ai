"""
collectors/bizinfo_collector.py
================================
Factory AI Navi — 기업마당(BIZINFO) 지원사업정보 수집기

데이터: 중소벤처기업부 「기업마당」 지원사업 공고 통합포털
  - 수집 방식: Open API (실시간, data.go.kr 활용신청 승인키)
  - API: https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do
  - 활용: 정부 지원사업 매칭 (SubsidyMatchingAgent) — 실제 신청 가능한 공고

NTIS(국가R&D 과제검색)와의 차이
--------------------------------
NTIS는 이미 종료/진행 중인 R&D 과제 이력(수행기관·집행내역)만 제공해
"신청 마감일" 개념이 없다. 기업마당은 반대로 실시간 공고이며
`reqstBeginEndDe`(신청기간)가 실제로 존재해 우리 서비스의
"지금 신청 가능한 지원사업" 요구사항에 맞는 유일한 실데이터 소스다.

한계
----
- 분야 대분류(searchLclasId)만 필터 가능, 자유 키워드 검색 파라미터 없음
  → "기술" 대분류로 조회 후 AI/제조 관련 키워드로 클라이언트 측 필터링
- 업종(KSIC)·지원금액·자부담률이 구조화된 필드로 오지 않고 자유 텍스트
  (bsnsSumryCn) 안에 섞여 있음 → 키워드/정규식으로 최대한 추출, 실패 시 None

작성일: 2026-07-05
버전: v1.0
"""

import re
from datetime import date, datetime

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import BIZINFO_API_KEY, BIZINFO_BASE_URL, logger

# 대분류: 01금융 02기술 03인력 04수출 05내수 06창업 07경영 09기타
SEARCH_LCLAS_ID = "02"   # 기술 — AI/스마트공장/자동화 공고가 가장 많이 분류되는 대분류
PAGE_UNIT = 100
MAX_PAGES = 3

# 공고명·사업개요에 이 키워드가 하나라도 있으면 "우리 서비스와 관련있는 공고"로 채택
RELEVANT_KEYWORDS = [
    "AI", "인공지능", "스마트공장", "스마트팩토리", "자동화", "로봇",
    "예지보전", "예측유지보수", "비전검사", "품질관리", "품질검사",
    "에너지절감", "에너지효율", "탄소중립", "공정개선", "공정혁신",
    "디지털전환", "DX", "제조데이터", "설비진단", "IoT", "사물인터넷",
]

AI_TYPE_KEYWORDS: dict[str, list[str]] = {
    "vision_inspection":     ["비전검사", "외관검사", "AOI", "이미지 검사"],
    "predictive_maintenance": ["예지보전", "예측유지보수", "설비진단", "고장예측"],
    "quality_control":       ["품질관리", "품질검사", "불량검출"],
    "energy_optimization":   ["에너지절감", "에너지효율", "탄소중립"],
    "robot_automation":      ["로봇", "자동화", "협동로봇"],
    "process_control":       ["공정개선", "공정혁신", "스마트공장", "스마트팩토리", "제조데이터"],
}

# 공고명·사업개요에 이 업종 키워드가 있으면 해당 KSIC 코드로 태깅 (근사 매핑, 명시 없으면 미태깅=전업종 대상)
INDUSTRY_KEYWORDS: dict[str, str] = {
    "식품": "C10", "사출": "C22", "플라스틱": "C22", "금속가공": "C25",
    "전자부품": "C26", "반도체": "C26", "기계": "C29", "자동차": "C30",
    "주조": "C243", "금형": "C251", "소성가공": "C259", "용접": "C289",
    "표면처리": "C301", "열처리": "C302",
}

_AMOUNT_PATTERN = re.compile(r"([\d,]+)\s*(천원|백만원|억원)")
_RATE_PATTERN = re.compile(r"(\d{1,3})\s*%\s*(?:내외\s*)?지원")


class BizinfoCollector(BaseCollector):
    """
    기업마당(BIZINFO) 지원사업정보 API 수집기.

    실제 모드: bizinfoApi.do 호출 (기술 대분류) → AI/제조 키워드 필터링
    Mock 모드: API 키 미설정 시 가상 공고 반환
    """

    def __init__(self):
        super().__init__(source_name="BIZINFO")

    def collect(self) -> pd.DataFrame:
        if "PLACEHOLDER" in BIZINFO_API_KEY:
            self.logger.warning(
                "[BIZINFO] API 키 미설정 — mock 데이터로 대체. "
                ".env 에 BIZINFO_API_KEY 를 설정하세요."
            )
            return self.get_mock_data()

        try:
            raw_items = self._fetch_all()
        except Exception as e:
            self.logger.error("[BIZINFO] API 호출 실패 — mock 데이터로 대체: %s", e)
            return self.get_mock_data()

        relevant = [item for item in raw_items if self._is_relevant(item)]
        self.logger.info(
            "[BIZINFO] 조회 %d건 중 AI/제조 관련 %d건 필터링", len(raw_items), len(relevant)
        )

        if not relevant:
            return self.get_mock_data()

        return self._normalize(relevant)

    def _fetch_all(self) -> list[dict]:
        """기술 대분류 공고를 페이지네이션하며 전체 수집"""
        items: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            params = {
                "crtfcKey":     BIZINFO_API_KEY,
                "dataType":     "json",
                "searchLclasId": SEARCH_LCLAS_ID,
                "pageUnit":     PAGE_UNIT,
                "pageIndex":    page,
            }
            data = self._get_json(BIZINFO_BASE_URL, params=params)
            page_items = data.get("jsonArray", [])
            if not page_items:
                break
            items.extend(page_items)
            if len(page_items) < PAGE_UNIT:
                break
        return items

    @staticmethod
    def _is_relevant(item: dict) -> bool:
        text = " ".join([
            item.get("pblancNm", ""),
            item.get("bsnsSumryCn", ""),
            item.get("hashtags", ""),
        ])
        return any(kw in text for kw in RELEVANT_KEYWORDS)

    def _normalize(self, items: list[dict]) -> pd.DataFrame:
        rows = []
        for item in items:
            text = " ".join([item.get("pblancNm", ""), item.get("bsnsSumryCn", "")])

            start, end = self._parse_period(item.get("reqstBeginEndDe", ""))
            is_active = end is None or end >= date.today()

            rows.append({
                "subsidy_id":            item.get("pblancId", ""),
                "source":                "BIZINFO",
                "program_name":          item.get("pblancNm", ""),
                "program_category":      item.get("pldirSportRealmMlsfcCodeNm")
                                         or item.get("pldirSportRealmLclasCodeNm", ""),
                "target_industry_codes": self._match_industries(text),
                "target_company_sizes":  self._match_company_sizes(item.get("trgetNm", "")),
                "target_ai_types":       self._match_ai_types(text),
                "max_support_amount":    self._extract_amount(item.get("bsnsSumryCn", "")),
                "min_support_amount":    None,
                "co_funding_rate":       self._extract_rate(item.get("bsnsSumryCn", "")),
                "application_start":     start,
                "application_end":       end,
                "announcement_date":     self._parse_date(item.get("creatPnttm", "")),
                "apply_url":             item.get("rceptEngnHmpgUrl") or item.get("pblancUrl", ""),
                "description":           self._strip_html(item.get("bsnsSumryCn", "")),
                "requirements":          item.get("jrsdInsttNm", ""),
                "is_active":             is_active,
            })

        df = pd.DataFrame(rows)
        self.logger.info("[BIZINFO] 실공고 정규화 완료: %d건", len(df))
        return df

    @staticmethod
    def _parse_period(raw: str) -> tuple[date | None, date | None]:
        """'2026-07-02 ~ 2026-07-23' 또는 '20220727 ~ 20220930' 형태 파싱"""
        if not raw or "~" not in raw:
            return None, None
        start_raw, end_raw = [p.strip() for p in raw.split("~", 1)]
        return BizinfoCollector._parse_date(start_raw), BizinfoCollector._parse_date(end_raw)

    @staticmethod
    def _parse_date(raw: str) -> date | None:
        if not raw:
            return None
        raw = raw.strip()[:10].replace(".", "-")
        for fmt in ("%Y-%m-%d", "%Y%m%d"):
            try:
                return datetime.strptime(raw.replace("-", "")[:8], "%Y%m%d").date() \
                    if fmt == "%Y%m%d" else datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _match_industries(text: str) -> str:
        codes = {code for kw, code in INDUSTRY_KEYWORDS.items() if kw in text}
        return ",".join(sorted(codes))

    @staticmethod
    def _match_company_sizes(trget_nm: str) -> str:
        if "소상공인" in trget_nm and "중소기업" not in trget_nm:
            return "small"
        return "small,medium"

    @staticmethod
    def _match_ai_types(text: str) -> str:
        types = {ai for ai, kws in AI_TYPE_KEYWORDS.items() if any(kw in text for kw in kws)}
        return ",".join(sorted(types))

    @staticmethod
    def _extract_amount(text: str) -> int | None:
        """'과제당 최대 20,000천원 이내' 같은 문구에서 만원 단위 금액 추출"""
        m = _AMOUNT_PATTERN.search(text or "")
        if not m:
            return None
        value = int(m.group(1).replace(",", ""))
        unit = m.group(2)
        if unit == "천원":
            return value // 10          # 천원 → 만원
        if unit == "백만원":
            return value * 100          # 백만원 → 만원
        if unit == "억원":
            return value * 10000        # 억원 → 만원
        return None

    @staticmethod
    def _extract_rate(text: str) -> float | None:
        """'소요비용의 70% 지원' 같은 문구에서 자부담률 추출 (100-지원율)"""
        m = _RATE_PATTERN.search(text or "")
        if not m:
            return None
        support_pct = int(m.group(1))
        return round((100 - support_pct) / 100, 2)

    @staticmethod
    def _strip_html(text: str) -> str:
        return re.sub(r"<[^>]+>", " ", text or "").strip()

    def get_mock_data(self) -> pd.DataFrame:
        """API 키 미설정 시 가상 공고 1건 반환 (구조 검증용)"""
        today = date.today()
        rows = [{
            "subsidy_id":            "BIZINFO-MOCK-0001",
            "source":                "BIZINFO",
            "program_name":          "(Mock) 중소기업 스마트공장 AI 도입 지원사업",
            "program_category":      "기술사업화/이전/지도",
            "target_industry_codes": "",
            "target_company_sizes":  "small,medium",
            "target_ai_types":       "process_control",
            "max_support_amount":    5000,
            "min_support_amount":    None,
            "co_funding_rate":       0.5,
            "application_start":     today,
            "application_end":       today,
            "announcement_date":     today,
            "apply_url":             "https://www.bizinfo.go.kr",
            "description":           "BIZINFO_API_KEY 미설정 상태의 mock 데이터",
            "requirements":          "",
            "is_active":             True,
        }]
        df = pd.DataFrame(rows)
        self.logger.info("[BIZINFO] Mock 데이터: %d건", len(df))
        return df
