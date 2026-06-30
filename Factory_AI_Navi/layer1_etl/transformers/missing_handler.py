"""
transformers/missing_handler.py
================================
Factory AI Navi — 결측값 처리 모듈

공공데이터에는 특정 업종·규모의 통계가 누락되는 경우가 많습니다.
이 모듈이 결측값을 업종 평균 또는 전체 평균으로 대체합니다.

처리 전략 (config.IMPUTATION_STRATEGY)
---------------------------------------
  'industry_mean' : 동일 업종 내 평균값으로 대체 (기본)
  'global_mean'   : 전체 데이터 평균으로 대체
  'drop'          : 결측 행 제거

작성일: 2026-04-28
버전: v1.0
"""

import pandas as pd
import numpy as np

from layer1_etl.config import IMPUTATION_STRATEGY, logger


class MissingHandler:
    """
    결측값 처리 클래스.

    사용법
    ------
    handler = MissingHandler()
    df      = handler.transform(df)
    """

    # 수치형 결측값 대상 컬럼
    NUMERIC_COLUMNS: list[str] = [
        "avg_production_per_person",
        "avg_defect_rate",
        "avg_operating_rate",
        "avg_energy_cost_ratio",
        "ai_adoption_rate",
        "avg_labor_cost_per_person",
        "avg_energy_consumption_toe",
        "robot_adoption_rate",
        "avg_robot_roi_months",
    ]

    # 필수 컬럼 (결측 시 행 제거)
    REQUIRED_COLUMNS: list[str] = [
        "industry_code",
        "reference_year",
    ]

    def __init__(self, strategy: str | None = None):
        self.strategy = strategy or IMPUTATION_STRATEGY
        self.logger = logger.getChild("MissingHandler")

    # ──────────────────────────────────────────────
    # 메인 변환 메서드
    # ──────────────────────────────────────────────

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame의 결측값을 처리합니다.

        1. 필수 컬럼 결측 행 제거
        2. 수치 컬럼 결측값 → 전략에 따라 대체
        3. 중복 행 제거 (동일 업종+규모+연도)

        Parameters
        ----------
        df : pd.DataFrame

        Returns
        -------
        pd.DataFrame
        """
        df = df.copy()
        original_len = len(df)

        # Step 1: 필수 컬럼 결측 행 제거
        df = self._drop_required_missing(df)

        # Step 2: 수치 컬럼 imputation
        if self.strategy == "industry_mean":
            df = self._impute_by_industry_mean(df)
        elif self.strategy == "global_mean":
            df = self._impute_by_global_mean(df)
        elif self.strategy == "drop":
            df = self._drop_any_missing(df)

        # Step 3: 중복 제거
        df = self._drop_duplicates(df)

        self.logger.info(
            "[MissingHandler] 결측처리 완료: %d → %d건 (strategy=%s)",
            original_len, len(df), self.strategy
        )
        return df

    # ──────────────────────────────────────────────
    # 세부 처리 메서드
    # ──────────────────────────────────────────────

    def _drop_required_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """필수 컬럼 결측 행 제거"""
        existing_required = [c for c in self.REQUIRED_COLUMNS if c in df.columns]
        if not existing_required:
            return df
        before = len(df)
        df = df.dropna(subset=existing_required)
        dropped = before - len(df)
        if dropped > 0:
            self.logger.warning(
                "[MissingHandler] 필수 컬럼 결측으로 %d건 제거: %s",
                dropped, existing_required
            )
        return df

    def _impute_by_industry_mean(self, df: pd.DataFrame) -> pd.DataFrame:
        """업종 평균값으로 결측 대체"""
        target_cols = [c for c in self.NUMERIC_COLUMNS if c in df.columns]
        if not target_cols:
            return df

        group_key = "industry_code" if "industry_code" in df.columns else None
        if group_key is None:
            return self._impute_by_global_mean(df)

        for col in target_cols:
            missing_count = df[col].isna().sum()
            if missing_count == 0:
                continue

            # 업종별 평균 계산 후 fillna
            industry_means = df.groupby(group_key)[col].transform("mean")
            global_mean = df[col].mean()

            df[col] = df[col].fillna(industry_means)
            df[col] = df[col].fillna(global_mean)   # 업종 전체가 결측이면 전체 평균으로

            self.logger.debug(
                "[MissingHandler] %s: %d건 결측 → 업종평균 대체", col, missing_count
            )

        return df

    def _impute_by_global_mean(self, df: pd.DataFrame) -> pd.DataFrame:
        """전체 평균으로 결측 대체"""
        target_cols = [c for c in self.NUMERIC_COLUMNS if c in df.columns]
        for col in target_cols:
            missing_count = df[col].isna().sum()
            if missing_count == 0:
                continue
            global_mean = df[col].mean()
            df[col] = df[col].fillna(global_mean)
            self.logger.debug(
                "[MissingHandler] %s: %d건 → 전체평균(%.2f) 대체",
                col, missing_count, global_mean
            )
        return df

    def _drop_any_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """수치 컬럼에 결측이 하나라도 있으면 행 제거"""
        target_cols = [c for c in self.NUMERIC_COLUMNS if c in df.columns]
        if not target_cols:
            return df
        before = len(df)
        df = df.dropna(subset=target_cols, how="any")
        self.logger.info(
            "[MissingHandler] drop 전략: %d → %d건", before, len(df)
        )
        return df

    def _drop_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """동일 업종+규모+연도 중복 제거 (최신 데이터 우선)"""
        key_cols = ["industry_code", "company_size", "reference_year"]
        existing_keys = [c for c in key_cols if c in df.columns]
        if not existing_keys:
            return df

        before = len(df)
        df = df.drop_duplicates(subset=existing_keys, keep="last")
        dropped = before - len(df)
        if dropped > 0:
            self.logger.info(
                "[MissingHandler] 중복 %d건 제거 (keep=last)", dropped
            )
        return df

    def report(self, df: pd.DataFrame) -> dict:
        """
        DataFrame의 결측 현황을 딕셔너리로 반환.
        파이프라인 로그 기록용.
        """
        target_cols = [c for c in self.NUMERIC_COLUMNS if c in df.columns]
        return {
            col: {
                "missing": int(df[col].isna().sum()),
                "missing_pct": float(df[col].isna().mean() * 100),
                "mean": float(df[col].mean()) if df[col].notna().any() else None,
            }
            for col in target_cols
        }
