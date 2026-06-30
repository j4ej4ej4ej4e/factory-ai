"""
collectors/base_collector.py
============================
Factory AI Navi — 공통 수집기 베이스 클래스

모든 개별 수집기(KIAT, KEIT, NTIS 등)가 이 클래스를 상속합니다.
공통 기능: HTTP 요청, 재시도 로직, mock 데이터 반환, 파일 저장, 로깅

작성일: 2026-04-28
버전: v1.0
"""

import json
import time
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from layer1_etl.config import (
    HTTP_HEADERS,
    HTTP_RETRY_COUNT,
    HTTP_RETRY_DELAY,
    HTTP_TIMEOUT,
    PROC_DIR,
    RAW_DIR,
    USE_MOCK_DATA,
    logger,
)


class BaseCollector(ABC):
    """
    모든 공공데이터 수집기의 추상 베이스 클래스.

    서브클래스 구현 필수 메서드
    --------------------------
    collect()      : 실제 데이터 수집 로직 (API 호출 또는 파일 파싱)
    get_mock_data(): mock 데이터 반환 (USE_MOCK_DATA=True 시 호출)
    source_name    : 데이터 출처 식별자 (예: 'KIAT', 'KEIT')

    사용 예시
    --------
    collector = KiatCollector()
    df = collector.run()   # mock/실제 모드 자동 분기
    """

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logger.getChild(source_name)
        self._session = self._build_session()

    # ──────────────────────────────────────────────
    # 추상 메서드 (서브클래스 필수 구현)
    # ──────────────────────────────────────────────

    @abstractmethod
    def collect(self) -> pd.DataFrame:
        """
        실제 데이터 수집 로직.
        API 호출 또는 파일 다운로드 후 pandas DataFrame 반환.
        """
        ...

    @abstractmethod
    def get_mock_data(self) -> pd.DataFrame:
        """
        Mock 데이터 반환 (API 키 없는 개발/테스트 환경용).
        실제 데이터와 동일한 컬럼 구조를 가진 DataFrame 반환.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """데이터 출처 식별자 (예: 'KIAT')"""
        ...

    @source_name.setter
    def source_name(self, value: str):
        self._source_name = value

    @source_name.getter
    def source_name(self) -> str:
        return self._source_name

    # ──────────────────────────────────────────────
    # 공통 실행 진입점
    # ──────────────────────────────────────────────

    def run(self) -> pd.DataFrame:
        """
        mock/실제 모드를 자동으로 분기하여 DataFrame 반환.
        수집 결과는 자동으로 raw 디렉토리에 CSV로 저장됩니다.
        """
        if USE_MOCK_DATA:
            self.logger.info("[%s] Mock 모드 — 가상 데이터 반환", self.source_name)
            df = self.get_mock_data()
        else:
            self.logger.info("[%s] 실제 수집 시작", self.source_name)
            df = self.collect()

        if df is not None and not df.empty:
            self._save_raw(df)
            self.logger.info(
                "[%s] 수집 완료: %d건", self.source_name, len(df)
            )
        else:
            self.logger.warning("[%s] 수집된 데이터가 없습니다.", self.source_name)
            df = pd.DataFrame()

        return df

    # ──────────────────────────────────────────────
    # HTTP 유틸리티
    # ──────────────────────────────────────────────

    def _build_session(self) -> requests.Session:
        """
        재시도 로직이 적용된 requests.Session 생성.
        429(Rate Limit), 500, 502, 503, 504 상태코드에서 자동 재시도.
        """
        session = requests.Session()
        session.headers.update(HTTP_HEADERS)

        retry = Retry(
            total=HTTP_RETRY_COUNT,
            backoff_factor=HTTP_RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        """
        GET 요청 래퍼. 예외 발생 시 로깅 후 re-raise.

        Parameters
        ----------
        url : str
        params : dict, optional

        Returns
        -------
        requests.Response
        """
        self.logger.debug("[%s] GET %s params=%s", self.source_name, url, params)
        try:
            response = self._session.get(url, params=params, timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            self.logger.error("[%s] 요청 타임아웃: %s", self.source_name, url)
            raise
        except requests.exceptions.HTTPError as e:
            self.logger.error(
                "[%s] HTTP 오류 %s: %s", self.source_name, e.response.status_code, url
            )
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error("[%s] 요청 실패: %s", self.source_name, e)
            raise

    def _get_json(self, url: str, params: dict | None = None) -> dict:
        """GET 요청 후 JSON 파싱"""
        response = self._get(url, params)
        return response.json()

    def _get_xml(self, url: str, params: dict | None = None) -> ET.Element:
        """GET 요청 후 XML 파싱"""
        response = self._get(url, params)
        return ET.fromstring(response.content)

    def _paginated_get(
        self,
        url: str,
        params: dict,
        page_param: str = "pageNo",
        size_param: str = "numOfRows",
        page_size: int = 100,
        max_pages: int = 50,
    ) -> list[dict]:
        """
        페이지네이션 지원 GET 요청. 전체 결과를 리스트로 반환.

        Parameters
        ----------
        url       : API 엔드포인트
        params    : 기본 파라미터 딕셔너리
        page_param: 페이지 번호 파라미터 이름
        size_param: 페이지 크기 파라미터 이름
        page_size : 한 번에 가져올 건수
        max_pages : 최대 페이지 수 (무한루프 방지)
        """
        all_items = []
        params[size_param] = page_size

        for page in range(1, max_pages + 1):
            params[page_param] = page
            try:
                data = self._get_json(url, params)
                items = self._extract_items(data)
                if not items:
                    self.logger.info(
                        "[%s] 페이지 %d: 데이터 없음, 종료", self.source_name, page
                    )
                    break
                all_items.extend(items)
                self.logger.info(
                    "[%s] 페이지 %d/%d: %d건 수집 (누적 %d건)",
                    self.source_name, page, max_pages, len(items), len(all_items)
                )
                time.sleep(0.3)   # API 과부하 방지
            except Exception as e:
                self.logger.error(
                    "[%s] 페이지 %d 수집 실패: %s", self.source_name, page, e
                )
                break

        return all_items

    def _extract_items(self, data: dict) -> list[dict]:
        """
        공공데이터 표준 응답 구조에서 item 리스트 추출.
        서브클래스에서 응답 구조가 다른 경우 오버라이드 가능.

        표준 구조:
            { "response": { "body": { "items": { "item": [...] } } } }
        """
        try:
            body = data.get("response", data).get("body", {})
            items_wrapper = body.get("items", {})
            if isinstance(items_wrapper, list):
                return items_wrapper
            item = items_wrapper.get("item", [])
            if isinstance(item, dict):   # 단건인 경우 리스트로 감싸기
                return [item]
            return item or []
        except (AttributeError, KeyError):
            return []

    # ──────────────────────────────────────────────
    # 파일 유틸리티
    # ──────────────────────────────────────────────

    def _save_raw(self, df: pd.DataFrame) -> Path:
        """수집된 DataFrame을 raw 디렉토리에 CSV로 저장"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = RAW_DIR / f"{self.source_name.lower()}_{timestamp}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        self.logger.info("[%s] Raw 저장: %s", self.source_name, file_path)
        return file_path

    def _save_processed(self, df: pd.DataFrame) -> Path:
        """전처리 완료 DataFrame을 processed 디렉토리에 저장"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = PROC_DIR / f"{self.source_name.lower()}_processed_{timestamp}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        self.logger.info("[%s] Processed 저장: %s", self.source_name, file_path)
        return file_path

    def _load_excel(self, file_path: str | Path, **kwargs) -> pd.DataFrame:
        """Excel 파일 로드 래퍼 (인코딩 오류 처리 포함)"""
        self.logger.info("[%s] Excel 로드: %s", self.source_name, file_path)
        return pd.read_excel(file_path, **kwargs)

    def _load_csv(
        self,
        file_path: str | Path,
        encoding: str = "utf-8",
        **kwargs
    ) -> pd.DataFrame:
        """CSV 파일 로드 래퍼 (인코딩 자동 감지)"""
        self.logger.info("[%s] CSV 로드: %s", self.source_name, file_path)
        try:
            return pd.read_csv(file_path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            self.logger.warning(
                "[%s] UTF-8 실패, CP949로 재시도: %s", self.source_name, file_path
            )
            return pd.read_csv(file_path, encoding="cp949", **kwargs)

    # ──────────────────────────────────────────────
    # 공통 유틸리티
    # ──────────────────────────────────────────────

    @staticmethod
    def safe_float(value: Any, default: float | None = None) -> float | None:
        """문자열·None을 안전하게 float으로 변환"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return default
        try:
            return float(str(value).replace(",", "").replace("%", "").strip())
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_int(value: Any, default: int | None = None) -> int | None:
        """문자열·None을 안전하게 int로 변환"""
        f = BaseCollector.safe_float(value)
        if f is None:
            return default
        return int(f)
