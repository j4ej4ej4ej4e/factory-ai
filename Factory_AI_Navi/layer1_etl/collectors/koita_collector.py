"""
collectors/koita_collector.py
=============================
Factory AI Navi — 한국로봇산업진흥원(KOITA) 수집기

데이터: 로봇산업 실태조사 (업종별 도입률·비용·성과)
  - 수집 방식: 파일 다운로드 (연 1회 갱신)
  - 활용: ROI 계산 벤치마크 (로봇 도입 효과 수치)

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# 로봇진흥원 실태조사 파일 설정 (파일 수령 후 주석 해제)
#
# 접속: https://www.koita.re.kr → 통계/조사 → 로봇산업 실태조사
# 파일명 예시: "2024_로봇산업실태조사.xlsx"
# 배치 경로: layer1_etl/data/raw/koita_robot_survey_2024.xlsx
# ──────────────────────────────────────────────────────────────────────────────

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import RAW_DIR, logger


class KoitaCollector(BaseCollector):
    """
    한국로봇산업진흥원 실태조사 수집기.

    실제 모드: RAW_DIR에 배치된 Excel 파일 파싱
    Mock 모드: MVP 3개 업종 가상 로봇 도입 효과 데이터 반환
    """

    # ──────────────────────────────────────────────
    # 실제 파일 설정 (파일 배치 후 주석 해제)
    # ──────────────────────────────────────────────
    # KOITA_FILE_PATH  = RAW_DIR / "koita_robot_survey_2024.xlsx"
    # KOITA_SHEET_NAME = "업종별현황"
    # COLUMN_MAP = {
    #     "업종코드":           "industry_code",
    #     "업종명":             "industry_name",
    #     "로봇도입률(%)":      "robot_adoption_rate",
    #     "평균도입비용(만원)": "avg_robot_cost",
    #     "회수기간(개월)":     "avg_robot_roi_months",
    #     "불량률감소(%)":      "defect_reduction_rate",
    #     "가동률향상(%)":      "operating_rate_improvement",
    # }
    # ──────────────────────────────────────────────

    def __init__(self):
        super().__init__(source_name="KOITA")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: RAW_DIR의 로봇진흥원 Excel 파일 파싱.
        파일 미배치 시 mock으로 폴백.
        """
        # ─────────────────────────────────────────────────────────────
        # [활성화 방법]
        # 1. 로봇진흥원 웹사이트에서 실태조사 Excel 다운로드
        # 2. RAW_DIR / "koita_robot_survey_2024.xlsx" 로 저장
        # 3. 아래 주석 해제
        # ─────────────────────────────────────────────────────────────

        # file_path = self.KOITA_FILE_PATH
        # if not file_path.exists():
        #     self.logger.warning("[KOITA] 파일 없음 — mock 대체: %s", file_path)
        #     return self.get_mock_data()
        # raw_df = self._load_excel(file_path, sheet_name=self.KOITA_SHEET_NAME)
        # return self._parse_koita_excel(raw_df)

        self.logger.warning(
            "[KOITA] 파일 미배치 — mock 데이터로 대체합니다. "
            "koita_robot_survey_2024.xlsx 파일을 RAW_DIR에 배치하세요."
        )
        return self.get_mock_data()

    def get_mock_data(self) -> pd.DataFrame:
        """
        로봇진흥원 실태조사 2024 기반 가상 수치.
        ROI 계산 시 이 데이터가 기준값으로 활용됩니다.
        """
        rows = [
            {
                "industry_code":              "C25",
                "industry_name":              "금속가공",
                "company_size":               "medium",
                "reference_year":             2024,
                "robot_adoption_rate":        18.0,  # %
                "avg_robot_cost":             8000,  # 만원 (평균 구축비용)
                "avg_robot_roi_months":       16.0,  # 개월
                "defect_reduction_rate":      1.5,   # %p 감소
                "operating_rate_improvement": 9.0,   # %p 향상
                "labor_reduction_rate":       0.15,  # 15% 인건비 절감
                "energy_reduction_rate":      0.07,  # 7% 에너지 절감
                "data_source":                "KOITA_MOCK",
                "raw_file_path":              None,
            },
            {
                "industry_code":              "C10",
                "industry_name":              "식품제조",
                "company_size":               "medium",
                "reference_year":             2024,
                "robot_adoption_rate":        12.0,
                "avg_robot_cost":             6000,
                "avg_robot_roi_months":       14.0,
                "defect_reduction_rate":      0.8,
                "operating_rate_improvement": 7.0,
                "labor_reduction_rate":       0.12,
                "energy_reduction_rate":      0.06,
                "data_source":                "KOITA_MOCK",
                "raw_file_path":              None,
            },
            {
                "industry_code":              "C22",
                "industry_name":              "사출성형",
                "company_size":               "medium",
                "reference_year":             2024,
                "robot_adoption_rate":        21.0,
                "avg_robot_cost":             7000,
                "avg_robot_roi_months":       13.0,
                "defect_reduction_rate":      1.8,
                "operating_rate_improvement": 10.0,
                "labor_reduction_rate":       0.18,
                "energy_reduction_rate":      0.08,
                "data_source":                "KOITA_MOCK",
                "raw_file_path":              None,
            },
        ]
        df = pd.DataFrame(rows)
        self.logger.info("[KOITA] Mock 로봇 실태조사: %d건", len(df))
        return df

    def _parse_koita_excel(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        실제 로봇진흥원 Excel 파싱 로직.
        파일 수령 후 컬럼명 확인하여 COLUMN_MAP 수정 필요.
        """
        # df = raw_df.rename(columns=self.COLUMN_MAP)
        # df["data_source"] = "KOITA"
        # df["reference_year"] = 2024
        # return df
        raise NotImplementedError("실제 KOITA 파일 파싱 — 컬럼 매핑 확인 후 구현")
