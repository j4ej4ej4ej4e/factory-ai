"""
transformers/unit_converter.py
==============================
Factory AI Navi — 단위 통일 변환 모듈

각 기관의 공공데이터는 단위가 다릅니다.
  - KIAT: 억원, KSNPC: 천만원, 고용노동부: 천원
  - 에너지: TOE, kWh, MJ 혼재
모든 수치를 Factory AI Navi 내부 기준으로 통일합니다.

내부 기준 단위
--------------
  금액: 만원 (萬圓)
  면적: ㎡
  에너지: TOE (Tonne of Oil Equivalent)
  비율: % (0~100)

작성일: 2026-04-28
버전: v1.0
"""

import pandas as pd

from layer1_etl.config import logger
from layer1_etl.constants import UNIT_CONVERSIONS


class UnitConverter:
    """
    공공데이터 단위 통일 변환기.

    사용법
    ------
    uc  = UnitConverter()
    df  = uc.transform(df, source="KIAT")

    또는 개별 변환:
    val = UnitConverter.억원_to_만원(3.5)   # → 35000.0
    """

    # 데이터 출처별 금액 단위 (만원 환산 계수)
    SOURCE_AMOUNT_UNIT: dict[str, float] = {
        "KIAT":   10_000.0,   # 억원 → 만원
        "KSNPC":  10.0,       # 천만원 → 만원
        "MOL":    0.1,        # 천원 → 만원
        "KOSTAT": 10_000.0,   # 억원 → 만원
        "KEMCO":  10_000.0,   # 억원 → 만원
        "KOITA":  1.0,        # 이미 만원 단위
        "KEIT":   10_000.0,   # 억원 → 만원
        "NTIS":   10_000.0,   # 억원 → 만원
        # Mock 데이터 (이미 만원 기준)
        "KIAT_MOCK":  1.0,
        "KSNPC_MOCK": 1.0,
        "KOITA_MOCK": 1.0,
    }

    # 금액 관련 컬럼 목록 (단위 변환 대상)
    AMOUNT_COLUMNS: list[str] = [
        "avg_production_per_person",
        "avg_labor_cost_per_person",
        "max_support_amount",
        "min_support_amount",
        "avg_robot_cost",
    ]

    # 비율 컬럼 목록 (0~100% 정규화 대상)
    RATIO_COLUMNS: list[str] = [
        "avg_defect_rate",
        "avg_operating_rate",
        "avg_energy_cost_ratio",
        "ai_adoption_rate",
        "robot_adoption_rate",
        "co_funding_rate",           # 이 컬럼은 0.0~1.0 이 표준
        "defect_reduction_rate",
        "operating_rate_improvement",
        "labor_reduction_rate",
        "energy_reduction_rate",
    ]

    def __init__(self):
        self.logger = logger.getChild("UnitConverter")

    # ──────────────────────────────────────────────
    # 메인 변환 메서드
    # ──────────────────────────────────────────────

    def transform(
        self,
        df: pd.DataFrame,
        source: str = "UNKNOWN",
    ) -> pd.DataFrame:
        """
        DataFrame의 금액·비율 컬럼을 내부 기준 단위로 변환.

        Parameters
        ----------
        df     : pd.DataFrame
        source : str
            데이터 출처 식별자 (SOURCE_AMOUNT_UNIT 키 참조)

        Returns
        -------
        pd.DataFrame
        """
        df = df.copy()
        factor = self.SOURCE_AMOUNT_UNIT.get(source, 1.0)

        if factor != 1.0:
            for col in self.AMOUNT_COLUMNS:
                if col in df.columns:
                    original_sum = df[col].sum()
                    df[col] = pd.to_numeric(df[col], errors="coerce") * factor
                    self.logger.debug(
                        "[UnitConverter] %s.%s × %.1f (합계: %.0f → %.0f)",
                        source, col, factor, original_sum, df[col].sum()
                    )

        # 비율 컬럼 정규화
        df = self._normalize_ratios(df, source)

        self.logger.info(
            "[UnitConverter] 단위 변환 완료: source=%s, factor=%.1f, rows=%d",
            source, factor, len(df)
        )
        return df

    def _normalize_ratios(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """
        비율 컬럼 정규화:
        - co_funding_rate: % → 0.0~1.0 (예: 50 → 0.5)
        - 나머지: 이미 % 단위면 그대로 유지
        """
        if "co_funding_rate" in df.columns:
            sr = pd.to_numeric(df["co_funding_rate"], errors="coerce")
            # 1 초과 값은 % 단위로 입력된 것 → 100 나누기
            mask_pct = sr > 1.0
            df.loc[mask_pct, "co_funding_rate"] = sr[mask_pct] / 100.0
            df["co_funding_rate"] = pd.to_numeric(df["co_funding_rate"], errors="coerce")

        return df

    # ──────────────────────────────────────────────
    # 정적 단위 변환 헬퍼
    # ──────────────────────────────────────────────

    @staticmethod
    def uk_to_man(value: float | None) -> float | None:
        """억원 -> 만원 변환 (x10000)"""
        if value is None:
            return None
        return value * 10_000.0

    @staticmethod
    def chun_to_man(value: float | None) -> float | None:
        """천원 -> 만원 변환 (x0.1)"""
        if value is None:
            return None
        return value * 0.1

    @staticmethod
    def chun_sqm_to_sqm(value: float | None) -> float | None:
        """천㎡ -> ㎡ 변환 (x1000)"""
        if value is None:
            return None
        return value * 1_000.0

    @staticmethod
    def toe_to_kwh(value: float | None) -> float | None:
        """TOE -> kWh 변환"""
        if value is None:
            return None
        return value * 11_630.0

    @staticmethod
    def mw_to_kw(value: float | None) -> float | None:
        """MW -> kW 변환"""
        if value is None:
            return None
        return value * 1_000.0

    @staticmethod
    def percent_to_ratio(value: float | None) -> float | None:
        """% -> 0.0~1.0 비율 변환 (예: 50 -> 0.5)"""
        if value is None:
            return None
        return value / 100.0

    @staticmethod
    def ratio_to_percent(value: float | None) -> float | None:
        """0.0~1.0 -> % 변환 (예: 0.5 -> 50)"""
        if value is None:
            return None
        return value * 100.0
