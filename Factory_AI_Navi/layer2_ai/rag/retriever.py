"""
layer2_ai/rag/retriever.py
==========================
Factory AI Navi — 온라인 RAG 리트리버

파이프라인:
  1. Multi-Query   : Claude가 쿼리 3개 생성 (도입사례 / 비용ROI / 기술효과 각도)
  2. 병렬 검색     : Naver + Tavily 동시 검색
  3. RRF 합산      : Reciprocal Rank Fusion으로 Top10 후보 선별
  4. 본문 크롤링   : 상위 3건 BeautifulSoup으로 본문 추출
  5. LLM Reranker  : Claude가 관련성 점수 부여 → Top5 최종 선별
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from layer1_etl.constants import AI_APPLICATION_TYPES, INDUSTRY_MAP_REVERSE
from layer2_ai.config import (
    CRAWL_MAX_CHARS,
    CRAWL_TIMEOUT,
    CRAWL_TOP_N,
    MULTI_QUERY_COUNT,
    MULTI_QUERY_MAX_TOKENS,
    RERANK_MAX_TOKENS,
    RERANK_TOP_N,
    RRF_K,
    RRF_TOP_K,
    logger,
)
from layer2_ai.llm_client import call_llm
from layer2_ai.rag.search_clients import NaverSearchClient, TavilySearchClient

# 크롤링 시 불필요한 HTML 태그
_CRAWL_STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "iframe"]

_CRAWL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class OnlineRAGRetriever:
    """
    온라인 RAG 리트리버.

    사용 예시
    ---------
    retriever = OnlineRAGRetriever()
    results = retriever.retrieve(
        industry_code="C25",
        ai_type="predictive_maintenance",
        company_profile={"company_size": "small"},
    )
    # results: [{"url": ..., "title": ..., "content": ..., "relevance_score": 8, ...}, ...]
    """

    def __init__(self):
        self.naver = NaverSearchClient()
        self.tavily = TavilySearchClient()

    # ──────────────────────────────────────────────
    # 메인 파이프라인
    # ──────────────────────────────────────────────

    def retrieve(
        self,
        industry_code: str,
        ai_type: str,
        company_profile: dict,
    ) -> list[dict]:
        """
        전체 RAG 파이프라인 실행.

        Parameters
        ----------
        industry_code : str
            KSIC 업종코드 (예: "C25")
        ai_type : str
            AI 유형 코드 (예: "predictive_maintenance")
        company_profile : dict
            기업 프로파일 (company_size 등)

        Returns
        -------
        list[dict]
            Top5 검색 결과. 각 항목:
            {url, title, snippet, content, source, rrf_score,
             relevance_score, relevance_reason}
        """
        industry_name = INDUSTRY_MAP_REVERSE.get(industry_code, industry_code)
        ai_name = AI_APPLICATION_TYPES.get(ai_type, ai_type)

        logger.info("[RAG] 파이프라인 시작: %s / %s", industry_name, ai_name)

        # Step 1: Multi-Query 생성
        queries = self._generate_queries(industry_name, ai_name)
        logger.info("[RAG] 생성된 쿼리 %d개: %s", len(queries), queries)

        # Step 2: Naver + Tavily 병렬 검색
        all_result_lists = self._parallel_search(queries)

        # Step 3: RRF 합산 → Top-K 후보
        candidates = self._rrf_merge(all_result_lists)[:RRF_TOP_K]
        logger.info("[RAG] RRF 후보: %d건", len(candidates))

        if not candidates:
            logger.warning("[RAG] 검색 결과 없음 (API 키 확인 필요)")
            return []

        # Step 4: 상위 N건 본문 크롤링
        candidates = self._enrich_with_content(candidates)

        # Step 5: LLM Reranker
        top_results = self._llm_rerank(industry_name, ai_name, company_profile, candidates)
        logger.info("[RAG] 최종 선별: %d건", len(top_results))

        return top_results

    # ──────────────────────────────────────────────
    # Step 1: Multi-Query 생성
    # ──────────────────────────────────────────────

    def _generate_queries(self, industry: str, ai_type: str) -> list[str]:
        """
        Claude로 다각도 검색 쿼리 3개 생성.

        3개 각도:
        1. 도입 사례/성공사례 중심
        2. 비용/ROI/투자회수 중심
        3. 기술/공정 개선 효과 중심
        """
        prompt = f"""다음 조건으로 한국어 웹 검색 쿼리 {MULTI_QUERY_COUNT}개를 생성하세요.
- 업종: {industry}
- AI 유형: {ai_type}

각도를 다르게 해서 {MULTI_QUERY_COUNT}개:
1. 도입 사례/성공사례 중심 (예: "XX업체 AI 도입 성공사례")
2. 비용/ROI/투자회수 중심 (예: "AI 도입 비용 ROI 회수기간")
3. 기술/공정 개선 효과 중심 (예: "공정 AI 적용 불량률 절감 효과")

JSON 배열로만 출력 (설명 없이, 따옴표 포함): ["쿼리1", "쿼리2", "쿼리3"]"""

        try:
            raw = call_llm(user=prompt, max_tokens=MULTI_QUERY_MAX_TOKENS)
            # JSON 배열만 추출 (앞뒤 텍스트 무시)
            start = raw.find("[")
            end = raw.rfind("]") + 1
            queries = json.loads(raw[start:end])
            return [str(q) for q in queries[:MULTI_QUERY_COUNT]]

        except Exception as e:
            logger.error("[RAG] Multi-Query 생성 실패: %s → 기본 쿼리 사용", e)
            return [
                f"{industry} {ai_type} 도입 사례 중소기업",
                f"{industry} AI 도입 비용 ROI 투자회수",
                f"{industry} 스마트공장 공정 개선 효과",
            ]

    # ──────────────────────────────────────────────
    # Step 2: 병렬 검색
    # ──────────────────────────────────────────────

    def _parallel_search(self, queries: list[str]) -> list[list[dict]]:
        """
        쿼리별로 Naver + Tavily 동시 검색.

        ThreadPoolExecutor로 쿼리 3개를 병렬 실행합니다.
        각 쿼리에서 Naver 결과 + Tavily 결과를 합산합니다.
        """
        def _search_one(query: str) -> list[dict]:
            results = []
            results.extend(self.naver.search(query))
            results.extend(self.tavily.search(query))
            return results

        result_lists: list[list[dict]] = []

        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = {executor.submit(_search_one, q): q for q in queries}
            for future in as_completed(futures):
                query = futures[future]
                try:
                    result_lists.append(future.result())
                except Exception as e:
                    logger.error("[RAG] 검색 실패 (%s): %s", query[:40], e)
                    result_lists.append([])

        return result_lists

    # ──────────────────────────────────────────────
    # Step 3: RRF 합산
    # ──────────────────────────────────────────────

    def _rrf_merge(
        self,
        result_lists: list[list[dict]],
        k: int = RRF_K,
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion (RRF) 으로 여러 쿼리 결과를 합산.

        score(doc) = Σ 1 / (k + rank_i)
        같은 URL이 여러 쿼리에서 나올수록 점수가 높아집니다.
        """
        scores: dict[str, float] = {}
        url_to_doc: dict[str, dict] = {}

        for results in result_lists:
            for rank, doc in enumerate(results):
                url = doc["url"]
                scores[url] = scores.get(url, 0.0) + 1.0 / (k + rank + 1)
                url_to_doc[url] = doc

        sorted_urls = sorted(scores, key=lambda u: -scores[u])
        return [
            {**url_to_doc[url], "rrf_score": round(scores[url], 6)}
            for url in sorted_urls
        ]

    # ──────────────────────────────────────────────
    # Step 4: 본문 크롤링
    # ──────────────────────────────────────────────

    def _enrich_with_content(self, candidates: list[dict]) -> list[dict]:
        """
        상위 CRAWL_TOP_N건은 본문을 직접 크롤링해서 스니펫을 보강.
        나머지는 스니펫(snippet)만 content로 복사.
        """
        top_n = min(CRAWL_TOP_N, len(candidates))

        def _crawl_one(doc: dict) -> dict:
            try:
                resp = requests.get(
                    doc["url"],
                    headers=_CRAWL_HEADERS,
                    timeout=CRAWL_TIMEOUT,
                    allow_redirects=True,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                for tag in soup(_CRAWL_STRIP_TAGS):
                    tag.decompose()

                text = " ".join(soup.get_text(separator=" ").split())
                doc["content"] = text[:CRAWL_MAX_CHARS]

            except Exception as e:
                logger.debug("[RAG] 크롤링 실패 (%s): %s", doc["url"][:50], e)
                doc["content"] = doc.get("snippet", "")

            return doc

        enriched: list[dict] = []

        with ThreadPoolExecutor(max_workers=top_n or 1) as executor:
            futures = [
                executor.submit(_crawl_one, candidates[i])
                for i in range(top_n)
            ]
            enriched = [f.result() for f in futures]

        # 나머지는 스니펫으로 대체
        for i in range(top_n, len(candidates)):
            candidates[i]["content"] = candidates[i].get("snippet", "")
            enriched.append(candidates[i])

        return enriched

    # ──────────────────────────────────────────────
    # Step 5: LLM Reranker
    # ──────────────────────────────────────────────

    def _llm_rerank(
        self,
        industry: str,
        ai_type: str,
        company_profile: dict,
        candidates: list[dict],
    ) -> list[dict]:
        """
        Claude가 각 후보에 관련성 점수(0~10)를 부여하고 Top-N 선별.

        평가 기준:
        - 실제 도입 사례가 있는가
        - 구체적 수치(비용, ROI, 절감률)가 있는가
        - 한국 중소 제조기업 관련인가
        - 해당 업종/AI유형과 일치하는가
        """
        company_size = company_profile.get("company_size", "소기업")

        formatted = "\n\n".join([
            (
                f"[{i + 1}] URL: {d['url']}\n"
                f"제목: {d['title']}\n"
                f"내용: {d.get('content', d.get('snippet', ''))[:600]}"
            )
            for i, d in enumerate(candidates)
        ])

        prompt = f"""다음 검색 결과들에 관련성 점수(0~10)를 부여하고 상위 {RERANK_TOP_N}개를 선택하세요.

[검색 목적]
- 업종: {industry} ({company_size})
- AI 유형: {ai_type}
- 목적: 실제 AI 도입 사례, 비용/ROI 수치, 공정 개선 효과 파악

[평가 기준]
- 실제 도입 사례 포함 여부 (가중치 높음)
- 구체적 수치(도입비용, ROI, 불량률 감소, 절감액) 포함 여부
- 한국 중소 제조기업 관련 여부
- 해당 업종·AI유형 일치 여부

[검색 결과 {len(candidates)}건]
{formatted}

JSON으로만 출력 (설명·마크다운 없이):
[{{"index": 1, "score": 8, "reason": "금속가공 예측유지보수 실제 수치 포함"}}, ...]

규칙:
- 상위 {RERANK_TOP_N}개만 출력
- 점수 내림차순 정렬
- index는 위 목록의 번호"""

        try:
            raw = call_llm(user=prompt, max_tokens=RERANK_MAX_TOKENS)
            start = raw.find("[")
            end = raw.rfind("]") + 1
            scored: list[dict] = json.loads(raw[start:end])
            scored.sort(key=lambda x: -x.get("score", 0))

            result = []
            for item in scored[:RERANK_TOP_N]:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(candidates):
                    doc = candidates[idx].copy()
                    doc["relevance_score"] = item.get("score", 0)
                    doc["relevance_reason"] = item.get("reason", "")
                    result.append(doc)

            return result

        except Exception as e:
            logger.error("[RAG] Reranker 실패: %s → RRF 순서 그대로 반환", e)
            for doc in candidates[:RERANK_TOP_N]:
                # None으로 두면 프론트에서 "관련도 0.0"(실제 낮은 점수처럼 보임) 대신
                # "#1" 순번으로 표시됨 — 리랭커 실패와 "진짜 0점"을 구분하기 위함
                doc.setdefault("relevance_score", None)
                doc.setdefault("relevance_reason", "리랭커 일시 오류 — RRF 검색 순서로 표시")
            return candidates[:RERANK_TOP_N]
