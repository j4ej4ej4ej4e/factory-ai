"""
transformers/industry_standardizer.py
======================================
Factory AI Navi — KSIC 업종코드 표준화 모듈

여러 기관의 공공데이터는 업종명·코드 표기가 제각각입니다.
이 모듈이 모든 데이터를 KSIC 10차 기준 코드로 통일합니다.

예시:
  "금속" → C25 (금속가공)
  "식품·음료" → C10 (식품제조)
  "사출" → C22 (사출성형)

작성일: 2026-04-28
버전: v1.0
"""

import re

import pandas as pd

from layer1_etl.config import logger
from layer1_etl.constants import INDUSTRY_MAP, INDUSTRY_MAP_REVERSE


class IndustryStandardizer:
    """
    KSIC 10차 기준 업종코드 표준화 클래스.

    사용법
    ------
    std = IndustryStandardizer()
    df  = std.transform(df)
    """

    # 다양한 표기 → KSIC 코드 추가 매핑 (퍼지 매칭용)
    ALIAS_MAP: dict[str, str] = {
        # 금속·기계 계열
        "금속":         "C25",
        "금속가공":     "C25",
        "금속부품":     "C25",
        "철강":         "C241",
        "비철":         "C242",
        "주조":         "C243",
        "금형":         "C251",
        "표면처리":     "C301",
        "열처리":       "C302",
        "용접":         "C289",
        # 식품 계열
        "식품":         "C10",
        "식품제조":     "C10",
        "식품·음료":    "C10",
        "식품가공":     "C10",
        "음료":         "C11",
        # 화학·플라스틱
        "사출":         "C22",
        "사출성형":     "C22",
        "플라스틱":     "C222",
        "고무":         "C221",
        "화학":         "C20",
        # 전자·반도체
        "전자":         "C26",
        "전자부품":     "C26",
        "반도체":       "C261",
        "디스플레이":   "C262",
        "이차전지":     "C263",
        # 자동차
        "자동차":       "C30",
        "자동차부품":   "C30",
        # 기계
        "기계":         "C29",
        "산업기계":     "C291",
        "의료기기":     "C272",
        # 섬유·의류
        "섬유":         "C13",
        "의류":         "C14",
        # 종이·인쇄
        "종이":         "C17",
        "인쇄":         "C18",
        # 조선·항공
        "조선":         "C311",
        "항공":         "C312",
    }

    def __init__(self):
        # ALIAS_MAP + INDUSTRY_MAP 통합 (ALIAS 우선)
        self._full_map = {**INDUSTRY_MAP, **self.ALIAS_MAP}
        self.logger = logger.getChild("IndustryStandardizer")

    # ──────────────────────────────────────────────
    # 메인 변환 메서드
    # ──────────────────────────────────────────────

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame의 industry_code / industry_name 컬럼을 KSIC 기준으로 표준화.

        Parameters
        ----------
        df : pd.DataFrame
            industry_code 또는 industry_name 컬럼을 포함해야 합니다.

        Returns
        -------
        pd.DataFrame
            industry_code, industry_name 컬럼이 KSIC 기준으로 표준화된 DataFrame.
        """
        df = df.copy()

        if "industry_code" in df.columns:
            df["industry_code"] = df["industry_code"].apply(self._normalize_code)

        if "industry_name" in df.columns:
            df["industry_name"] = df["industry_name"].apply(self._normalize_name)

        # 코드가 없고 이름만 있는 경우 → 이름으로 코드 유추
        if "industry_code" in df.columns and "industry_name" in df.columns:
            mask_missing_code = df["industry_code"].isna() | (df["industry_code"] == "")
            df.loc[mask_missing_code, "industry_code"] = df.loc[
                mask_missing_code, "industry_name"
            ].apply(self._name_to_code)

        # 이름이 없고 코드만 있는 경우 → 코드로 이름 채우기
        if "industry_name" in df.columns and "industry_code" in df.columns:
            mask_missing_name = df["industry_name"].isna() | (df["industry_name"] == "")
            df.loc[mask_missing_name, "industry_name"] = df.loc[
                mask_missing_name, "industry_code"
            ].apply(lambda c: INDUSTRY_MAP_REVERSE.get(c, c))

        converted = (~mask_missing_code).sum() if "industry_code" in df.columns else 0
        self.logger.info(
            "[Standardizer] 업종코드 표준화 완료: 총 %d건", len(df)
        )
        return df

    # ──────────────────────────────────────────────
    # 개별 변환 메서드
    # ──────────────────────────────────────────────

    def _normalize_code(self, code: str | None) -> str | None:
        """
        업종코드 정규화.
        - 앞뒤 공백 제거
        - 소문자 → 대문자
        - 'C' 접두사 없으면 추가 (예: '25' → 'C25')
        """
        if code is None or (isinstance(code, float)):
            return None
        code = str(code).strip().upper()
        if code == "" or code == "NAN":
            return None
        # 숫자만 있으면 'C' 접두사 추가
        if re.fullmatch(r"\d+", code):
            code = "C" + code
        return code if code in INDUSTRY_MAP_REVERSE else code

    def _normalize_name(self, name: str | None) -> str | None:
        """업종명 앞뒤 공백 제거 및 중복 공백 정리"""
        if name is None or (isinstance(name, float)):
            return None
        return re.sub(r"\s+", " ", str(name).strip())

    def _name_to_code(self, name: str | None) -> str | None:
        """
        업종명 → KSIC 코드 변환 (완전일치 → 부분일치 순서로 시도).

        Parameters
        ----------
        name : str
            업종명 (예: '금속가공', '금속')

        Returns
        -------
        str | None
            KSIC 코드 또는 None
        """
        if name is None or (isinstance(name, float)):
            return None
        name = str(name).strip()

        # 1) 완전 일치
        if name in self._full_map:
            return self._full_map[name]

        # 2) 부분 포함 (alias 키가 name 안에 포함되는 경우)
        for alias, code in self._full_map.items():
            if alias in name:
                self.logger.debug(
                    "[Standardizer] 부분매칭 '%s' → '%s' (%s)", name, alias, code
                )
                return code

        self.logger.warning(
            "[Standardizer] 업종코드 매핑 실패: '%s' — constants.INDUSTRY_MAP 에 추가하세요.", name
        )
        return None

    def code_to_name(self, code: str) -> str | None:
        """KSIC 코드 → 한글 업종명 변환"""
        return INDUSTRY_MAP_REVERSE.get(code)

    def name_to_code(self, name: str) -> str | None:
        """한글 업종명 → KSIC 코드 변환 (public API)"""
        return self._name_to_code(name)
