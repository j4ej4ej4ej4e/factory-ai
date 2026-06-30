"""
layer2_ai/rag/search_clients.py
================================
Factory AI Navi — 웹 검색 클라이언트

네이버 검색 API (무료, 한국어 최적화) +
Tavily Search API (선택, 없으면 자동 비활성화)
"""

import requests

from layer2_ai.config import (
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    NAVER_SEARCH_URL,
    NAVER_SEARCH_DISPLAY,
    TAVILY_API_KEY,
    logger,
)


class NaverSearchClient:
    """
    네이버 웹 검색 API 클라이언트.

    한국 제조업 사례는 네이버에 더 많이 인덱싱되어 있어
    Tavily보다 한국어 쿼리 품질이 높습니다.

    발급: https://developers.naver.com → 검색 API
    무료: 25,000건/일
    """

    def __init__(self):
        self._available = "PLACEHOLDER" not in NAVER_CLIENT_ID
        if not self._available:
            logger.warning("[Naver] API 키 미설정 — .env에 NAVER_CLIENT_ID/SECRET 추가 필요")

    def search(self, query: str, display: int = NAVER_SEARCH_DISPLAY) -> list[dict]:
        """
        네이버 웹 검색 실행.

        Parameters
        ----------
        query : str
            검색 쿼리
        display : int
            결과 수 (최대 100, 기본 10)

        Returns
        -------
        list[dict]
            각 항목: {url, title, snippet, source}
        """
        if not self._available:
            return []

        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        params = {"query": query, "display": display, "sort": "sim"}

        try:
            resp = requests.get(
                NAVER_SEARCH_URL,
                headers=headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

            return [
                {
                    "url": item["link"],
                    "title": _strip_bold(item.get("title", "")),
                    "snippet": _strip_bold(item.get("description", "")),
                    "source": "naver",
                }
                for item in items
                if item.get("link")
            ]

        except requests.exceptions.Timeout:
            logger.warning("[Naver] 타임아웃: %s", query[:40])
            return []
        except Exception as e:
            logger.error("[Naver] 검색 실패 (%s): %s", query[:40], e)
            return []


class TavilySearchClient:
    """
    Tavily Search API 클라이언트 (선택).

    TAVILY_API_KEY가 없으면 자동으로 비활성화됩니다.
    Naver와 병합 시 영문 자료 커버리지를 보완합니다.

    발급: https://tavily.com (무료 1,000건/월)
    """

    def __init__(self):
        self._client = None
        if not TAVILY_API_KEY:
            logger.info("[Tavily] API 키 없음 — Naver만 사용합니다.")
            return

        try:
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=TAVILY_API_KEY)
            logger.info("[Tavily] 클라이언트 초기화 완료")
        except ImportError:
            logger.warning("[Tavily] tavily-python 미설치 — `pip install tavily-python`")

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Tavily 검색 실행.

        Returns
        -------
        list[dict]
            각 항목: {url, title, snippet, source}
        """
        if not self._client:
            return []

        try:
            resp = self._client.search(
                query,
                max_results=max_results,
                search_depth="basic",
            )
            return [
                {
                    "url": r["url"],
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:500],
                    "source": "tavily",
                }
                for r in resp.get("results", [])
                if r.get("url")
            ]
        except Exception as e:
            logger.error("[Tavily] 검색 실패 (%s): %s", query[:40], e)
            return []


def _strip_bold(text: str) -> str:
    """네이버 API가 반환하는 <b>...</b> 태그 제거"""
    return text.replace("<b>", "").replace("</b>", "").strip()
