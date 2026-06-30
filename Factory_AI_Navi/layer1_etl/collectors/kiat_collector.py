"""
collectors/kiat_collector.py
============================
Factory AI Navi — KIAT 산업기술통계 수집기

데이터: 한국산업기술진흥원(KIAT) 산업기술통계
  - 업종별 R&D 투자액, 생산성, 기업 수, AI 도입률 등
  - 수집 방식: 파일 다운로드 (연 1회 갱신)
  - 활용: 동종업계 벤치마크 기준값

수집 방법
---------
1. 실제 모드: KIAT 통계 시스템(https://www.kiat.or.kr)에서 수동 다운로드한
   Excel/CSV 파일을 RAW_DIR에 배치 후 실행
2. Mock 모드: 3개 MVP 업종 (금속가공C25, 식품C10, 사출성형C22) 가상 데이터 반환

작성일: 2026-04-28
버전: v1.0
"""

# ──────────────────────────────────────────────────────────────────────────────
# KIAT 실제 다운로드 경로 (수동 파일 배치 후 주석 해제)
#
# 접속: https://www.kiat.or.kr → 정보마당 → 통계/조사
# 파일명 예시: "2024년_산업기술통계_업종별.xlsx"
# 배치 경로: layer1_etl/data/raw/kiat_industry_2024.xlsx
#
# KIAT_FILE_PATH = RAW_DIR / "kiat_industry_2024.xlsx"
# KIAT_SHEET_NAME = "업종별_생산성"
# ──────────────────────────────────────────────────────────────────────────────

from pathlib import Path

import pandas as pd

from layer1_etl.collectors.base_collector import BaseCollector
from layer1_etl.config import RAW_DIR, logger
from layer1_etl.constants import INDUSTRY_MAP, MVP_INDUSTRY_CODES


class KiatCollector(BaseCollector):
    """
    KIAT 산업기술통계 수집기.

    실제 모드: RAW_DIR에 배치된 Excel 파일 파싱
    Mock 모드: MVP 3개 업종 가상 통계 데이터 반환
    """

    # ──────────────────────────────────────────────
    # 실제 파일 설정 (파일 수령 후 주석 해제)
    # ──────────────────────────────────────────────
    # KIAT_FILE_PATH  = RAW_DIR / "kiat_industry_2024.xlsx"
    # KIAT_SHEET_NAME = "업종별_생산성"
    # COLUMN_MAP = {
    #     "KSIC코드":         "industry_code",
    #     "업종명":           "industry_name",
    #     "기업규모":         "company_size",
    #     "인당생산액(만원)": "avg_production_per_person",
    #     "불량률(%)":        "avg_defect_rate",
    #     "가동률(%)":        "avg_operating_rate",
    #     "AI도입률(%)":      "ai_adoption_rate",
    #     "인건비(만원/인)":  "avg_labor_cost_per_person",
    #     "에너지비용비율(%)": "avg_energy_cost_ratio",
    # }
    # ──────────────────────────────────────────────

    def __init__(self):
        super().__init__(source_name="KIAT")

    def collect(self) -> pd.DataFrame:
        """
        실제 모드: RAW_DIR 의 KIAT Excel 파일 파싱.

        ── 파일이 준비되면 아래 주석 코드를 활성화하세요 ──
        """
        # ─────────────────────────────────────────────────────────────
        # [활성화 방법]
        # 1. KIAT 통계 시스템에서 업종별 산업기술통계 Excel 다운로드
        # 2. RAW_DIR / "kiat_industry_2024.xlsx" 로 저장
        # 3. 아래 주석 해제 후 실행
        # ─────────────────────────────────────────────────────────────

        # file_path = RAW_DIR / "kiat_industry_2024.xlsx"
        # if not file_path.exists():
        #     raise FileNotFoundError(
        #         f"KIAT 파일 없음: {file_path}\n"
        #         "https://www.kiat.or.kr 에서 다운로드 후 배치하세요."
        #     )
        # raw_df = self._load_excel(file_path, sheet_name=self.KIAT_SHEET_NAME)
        # return self._parse_kiat_excel(raw_df)

        self.logger.warning(
            "[KIAT] 실제 파일 미배치 — mock 데이터로 대체합니다. "
            "kiat_industry_2024.xlsx 파일을 RAW_DIR에 배치하세요."
        )
        return self.get_mock_data()

    def get_mock_data(self) -> pd.DataFrame:
        """
        MVP 3개 업종 × 3개 기업규모 = 9건 가상 벤치마크 데이터.
        실제 KIAT 통계 수준의 합리적 수치 사용.
        """
        rows = []
        mock_stats = {
            # (업종코드, 업종명): {규모: {지표: 값}}
            ("C25", "금속가공"): {
                "small":     {"prod": 3100, "defect": 3.8, "op_rate": 68, "ai": 4,  "labor": 3800, "energy": 9.5},
                "medium":    {"prod": 4200, "defect": 2.3, "op_rate": 78, "ai": 12, "labor": 4200, "energy": 8.2},
                "mid_large": {"prod": 6100, "defect": 1.5, "op_rate": 85, "ai": 28, "labor": 5500, "energy": 7.0},
            },
            ("C10", "식품제조"): {
                "small":     {"prod": 2800, "defect": 2.1, "op_rate": 72, "ai": 3,  "labor": 3200, "energy": 11.0},
                "medium":    {"prod": 3900, "defect": 1.4, "op_rate": 80, "ai": 10, "labor": 3900, "energy": 9.8},
                "mid_large": {"prod": 5500, "defect": 0.9, "op_rate": 88, "ai": 22, "labor": 5100, "energy": 8.5},
            },
            ("C22", "사출성형"): {
                "small":     {"prod": 2600, "defect": 4.2, "op_rate": 65, "ai": 5,  "labor": 3400, "energy": 10.2},
                "medium":    {"prod": 3700, "defect": 2.8, "op_rate": 75, "ai": 14, "labor": 4000, "energy": 8.9},
                "mid_large": {"prod": 5200, "defect": 1.8, "op_rate": 83, "ai": 30, "labor": 5200, "energy": 7.5},
            },
        }

        for (code, name), sizes in mock_stats.items():
            for size, vals in sizes.items():
                rows.append({
                    "industry_code":              code,
                    "industry_name":              name,
                    "company_size":               size,
                    "reference_year":             2024,
                    "avg_production_per_person":  vals["prod"],
                    "avg_defect_rate":            vals["defect"],
                    "avg_operating_rate":         vals["op_rate"],
                    "ai_adoption_rate":           vals["ai"],
                    "avg_labor_cost_per_person":  vals["labor"],
                    "avg_energy_cost_ratio":      vals["energy"],
                    "avg_energy_consumption_toe": None,
                    "robot_adoption_rate":        vals["ai"] * 1.5,  # AI 도입률 연동 추정
                    "avg_robot_roi_months":       18.0,
                    "data_source":                "KIAT_MOCK",
                    "raw_file_path":              None,
                })

        df = pd.DataFrame(rows)
        self.logger.info("[KIAT] Mock 데이터 생성: %d건", len(df))
        return df

    def _parse_kiat_excel(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        실제 KIAT Excel 파싱 로직.
        파일 수령 후 실제 컬럼명 확인하여 COLUMN_MAP 수정 필요.
        """
        # df = raw_df.rename(columns=self.COLUMN_MAP)
        # df = df[list(self.COLUMN_MAP.values())].copy()
        # df["data_source"] = "KIAT"
        # df["reference_year"] = 2024
        # return df
        raise NotImplementedError("실제 KIAT 파일 파싱 — 컬럼 매핑 확인 후 구현")
