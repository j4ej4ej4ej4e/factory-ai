"""
layer2_ai/config.py
===================
Factory AI Navi — Layer 2 AI 엔진 전용 설정

Layer 1 config를 재사용하고 Layer 2 추가 설정을 정의합니다.
"""

import os
from pathlib import Path

from layer1_etl.config import (
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    CLAUDE_MODEL,
    EMBEDDING_MODEL,
    logger,
    BASE_DIR,
)

# ══════════════════════════════════════════════
# [1] 네이버 검색 API
# ══════════════════════════════════════════════
# 발급: https://developers.naver.com → 애플리케이션 등록 → 검색 API
# .env: NAVER_CLIENT_ID=your_id
#       NAVER_CLIENT_SECRET=your_secret
NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "PLACEHOLDER_NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "PLACEHOLDER_NAVER_CLIENT_SECRET")
NAVER_SEARCH_URL: str = "https://openapi.naver.com/v1/search/webkr.json"
NAVER_SEARCH_DISPLAY: int = 10  # 쿼리당 결과 수 (최대 100)

# ══════════════════════════════════════════════
# [2] Tavily 검색 API (선택 — 없으면 Naver만 사용)
# ══════════════════════════════════════════════
# 발급: https://tavily.com → 무료 플랜 1,000건/월
# .env: TAVILY_API_KEY=your_key
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# ══════════════════════════════════════════════
# [3] Multi-Query 설정
# ══════════════════════════════════════════════
MULTI_QUERY_COUNT: int = 3      # Claude가 생성할 쿼리 수
MULTI_QUERY_MAX_TOKENS: int = 200

# ══════════════════════════════════════════════
# [4] RRF (Reciprocal Rank Fusion) 설정
# ══════════════════════════════════════════════
RRF_K: int = 60       # RRF 상수 (클수록 상위-하위 점수 차이 완화)
RRF_TOP_K: int = 10   # RRF 합산 후 Reranker에 넘길 후보 수

# ══════════════════════════════════════════════
# [5] 웹 크롤링 설정
# ══════════════════════════════════════════════
CRAWL_TOP_N: int = 3          # 본문 전체 크롤링할 상위 N건 (나머지는 스니펫만)
CRAWL_TIMEOUT: int = 10       # 요청 타임아웃 (초)
CRAWL_MAX_CHARS: int = 2000   # 본문 최대 문자 수 (Claude 토큰 절약)

# ══════════════════════════════════════════════
# [6] LLM Reranker 설정
# ══════════════════════════════════════════════
RERANK_TOP_N: int = 5           # 최종 선별 수
RERANK_MAX_TOKENS: int = 600

# ══════════════════════════════════════════════
# [7] Layer 2 디렉토리
# ══════════════════════════════════════════════
LAYER2_DIR: Path = BASE_DIR / "layer2_ai"
