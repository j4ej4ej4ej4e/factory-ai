"""
collectors/keit_collector.py
============================
Factory AI Navi — KEIT 사업공고 수집기

데이터: 한국산업기술평가관리원(KEIT) 사업공고 현황
  - 수집 방식: 파일 다운로드 + 웹 크롤링 (주 1회 갱신)
  - 활용: 정부지원사업 매칭 (SubsidyMatchingAgent)

수집 방법
---------
1. 실제 모드: KEIT 사업공고 페이지 크롤링 또는 파일 파싱
2. Mock 모드: 현실적인 가상 사업공고 5건 반환

참고 URL (실제 모드 활성화 시 사용)
------------------------------------
- KEIT 사업공고: https://www.keit.re.kr/business/businessAnnouce.do
- 중기부 스마트공장: https://www.smart-factory.kr
- 소진공 뿌리업종: https://www.sbiz.or.kr

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# 실제 크롤링 설정 (크롤링 구현 후 주석 해제)
#
# KEIT_BASE_URL      = "https://www.keit.re.kr"
# KEIT_ANNOUNCE_URL  = f"{KEIT_BASE_URL}/business/businessAnnouce.do"
# MSS_SMART_URL      = "https://www.smart-factory.kr/board/list.do?menuId=M10"
# SBC_ROOTS_URL      = "https://www.sbiz.or.kr"
#
# Selenium 또는 requests-html 사용 검토 필요 (JavaScript 렌더링 여부 확인)
# ──────────────────────────────────────────────────────────────────────────────

from datetime import date, timedelta

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import logger


class KeitCollector(BaseCollector):
    """
    KEIT 사업공고 수집기.

    실제 모드: KEIT 웹사이트 크롤링 + 파일 파싱
    Mock 모드: 공모전 심사 시점 기준 현실적 가상 공고 5건 반환
    """

    def __init__(self):
        super().__init__(source_name="KEIT")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: KEIT 사업공고 페이지 크롤링.

        ── 크롤링 코드 준비 완료 후 주석 해제 ──
        """
        # ─────────────────────────────────────────────────────────────
        # [활성화 방법]
        # 1. KEIT 공고 페이지 구조 확인 (JavaScript 렌더링 여부)
        # 2. requests + BeautifulSoup 또는 Selenium으로 파싱
        # 3. 공고 목록 → 상세 페이지 순차 방문
        # 4. 프로그램명, 지원금액, 마감일, 신청링크 추출
        # ─────────────────────────────────────────────────────────────

        # from bs4 import BeautifulSoup
        # response = self._get(self.KEIT_ANNOUNCE_URL)
        # soup = BeautifulSoup(response.text, "html.parser")
        # rows = self._parse_announce_table(soup)
        # return pd.DataFrame(rows)

        self.logger.warning(
            "[KEIT] 크롤링 미구현 — mock 데이터로 대체합니다. "
            "KEIT 공고 페이지 구조 확인 후 크롤링 코드를 추가하세요."
        )
        return self.get_mock_data()

    def get_mock_data(self) -> pd.DataFrame:
        """
        2026년 7월 공모전 시연 기준 현실적 가상 공고 데이터.
        실제 KEIT·중기부 공고명과 지원 금액 수준 반영.
        """
        today = date.today()

        rows = [
            {
                "subsidy_id":            "KEIT-2026-0501",
                "source":                "KEIT",
                "program_name":          "제조AI특화 스마트공장 구축 지원",
                "program_category":      "스마트공장",
                "target_industry_codes": "C25,C10,C22,C243",
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "predictive_maintenance,vision_inspection",
                "max_support_amount":    20000,
                "min_support_amount":    3000,
                "co_funding_rate":       0.5,
                "application_start":     today - timedelta(days=30),
                "application_end":       today + timedelta(days=63),
                "announcement_date":     today - timedelta(days=30),
                "apply_url":             "https://www.smart-factory.kr",
                "description":           "중소 제조기업 AI 기반 스마트공장 구축 지원. 예측유지보수·품질검사 AI 우선 지원.",
                "requirements":          "종업원 300인 미만 제조업, 스마트공장 1~2수준 기업",
                "is_active":             True,
            },
            {
                "subsidy_id":            "KEIT-2026-0502",
                "source":                "KEIT",
                "program_name":          "배터리·전기전자 분야 기술개발 과제",
                "program_category":      "R&D",
                "target_industry_codes": "C26,C27,C28",
                "target_company_sizes":  "small,medium,mid_large",
                "target_ai_types":       "quality_control,process_control",
                "max_support_amount":    50000,
                "min_support_amount":    10000,
                "co_funding_rate":       0.35,
                "application_start":     today - timedelta(days=20),
                "application_end":       today + timedelta(days=77),
                "announcement_date":     today - timedelta(days=20),
                "apply_url":             "https://www.keit.re.kr",
                "description":           "배터리·전기전자 업종 AI 공정최적화 R&D 지원. 기업부설연구소 필수.",
                "requirements":          "기업부설연구소 보유, 기술개발 의지 확인",
                "is_active":             True,
            },
            {
                "subsidy_id":            "SBC-2026-0301",
                "source":                "KEIT",
                "program_name":          "뿌리업종 AI 응용상용화 지원",
                "program_category":      "뿌리업종",
                "target_industry_codes": "C243,C251,C259,C289,C301,C302",
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "vision_inspection,predictive_maintenance",
                "max_support_amount":    30000,
                "min_support_amount":    5000,
                "co_funding_rate":       0.4,
                "application_start":     today - timedelta(days=10),
                "application_end":       today + timedelta(days=62),
                "announcement_date":     today - timedelta(days=10),
                "apply_url":             "https://www.sbiz.or.kr",
                "description":           "주조·금형·소성가공 등 뿌리업종 AI 비전검사 및 공정개선 지원.",
                "requirements":          "뿌리산업진흥법 제2조 해당 뿌리업종 영위 기업",
                "is_active":             True,
            },
            {
                "subsidy_id":            "MSS-2026-0401",
                "source":                "KEIT",
                "program_name":          "대중소 상생형 AI트랙 (삼성전자 협력)",
                "program_category":      "상생협력",
                "target_industry_codes": "C25,C26,C30",
                "target_company_sizes":  "small",
                "target_ai_types":       "process_control,robot_automation",
                "max_support_amount":    30000,
                "min_support_amount":    5000,
                "co_funding_rate":       0.3,
                "application_start":     today - timedelta(days=5),
                "application_end":       today + timedelta(days=10),
                "announcement_date":     today - timedelta(days=5),
                "apply_url":             "https://www.mss.go.kr",
                "description":           "삼성전자 협력사 대상 AI 자동화 솔루션 구축 지원. 마감 임박.",
                "requirements":          "삼성전자 1·2차 협력사, 종업원 50인 미만 소기업",
                "is_active":             True,
            },
            {
                "subsidy_id":            "MOTIE-2026-0601",
                "source":                "KEIT",
                "program_name":          "지역특화 스마트공장 보급·확산",
                "program_category":      "스마트공장",
                "target_industry_codes": "C10,C22,C25,C24",
                "target_company_sizes":  "small,medium",
                "target_ai_types":       "predictive_maintenance,energy_optimization",
                "max_support_amount":    10000,
                "min_support_amount":    2000,
                "co_funding_rate":       0.5,
                "application_start":     today - timedelta(days=15),
                "application_end":       today + timedelta(days=62),
                "announcement_date":     today - timedelta(days=15),
                "apply_url":             "https://www.smart-factory.kr",
                "description":           "지역 산업단지 입주 중소기업 스마트공장 구축. 에너지 절감 우선.",
                "requirements":          "국가산업단지 또는 일반산업단지 입주 기업",
                "is_active":             True,
            },
        ]

        df = pd.DataFrame(rows)
        self.logger.info("[KEIT] Mock 공고 데이터 생성: %d건", len(df))
        return df
