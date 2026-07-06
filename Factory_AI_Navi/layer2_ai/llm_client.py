"""
layer2_ai/llm_client.py
========================
Claude / Gemini 공통 LLM 래퍼.

.env의 LLM_PROVIDER 값으로 전환:
  LLM_PROVIDER=claude   → Anthropic Claude (기본)
  LLM_PROVIDER=gemini   → Google Gemini

사용 예시:
  from layer2_ai.llm_client import call_llm
  text = call_llm(user="질문", system="시스템 프롬프트", max_tokens=500)
"""

import os
import time
from layer2_ai.config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    logger,
)

LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "claude").lower()
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_MAX_RETRIES = 2  # 503(일시 과부하) 전용 재시도 횟수


def call_llm(user: str, system: str = "", max_tokens: int = 1000) -> str:
    """
    LLM_PROVIDER에 따라 Claude 또는 Gemini 호출.

    503(모델 일시 과부하)은 몇 초 내로 풀리는 경우가 많아 짧게 재시도한다.
    429(할당량 초과)는 재시도해도 수십 초~하루 단위로 안 풀리므로 바로
    포기하고 예외를 던져 호출부의 규칙 기반 폴백으로 넘어가게 한다.

    Parameters
    ----------
    user      : 사용자 메시지
    system    : 시스템 프롬프트 (Gemini는 user 앞에 붙임)
    max_tokens: 최대 출력 토큰 수

    Returns
    -------
    str : LLM 응답 텍스트
    """
    last_err: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            if LLM_PROVIDER == "gemini":
                return _call_gemini(user, system, max_tokens)
            return _call_claude(user, system, max_tokens)
        except Exception as e:
            last_err = e
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise  # 할당량 초과 — 재시도 무의미, 즉시 폴백으로
            if attempt < _MAX_RETRIES:
                wait = 1.5 * (attempt + 1)
                logger.warning(
                    "[LLM] 일시 오류 → %.1f초 후 재시도 (%d/%d): %s",
                    wait, attempt + 1, _MAX_RETRIES, msg[:80],
                )
                time.sleep(wait)
                continue
    raise last_err  # 재시도 다 소진


def _call_claude(user: str, system: str, max_tokens: int) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    kwargs: dict = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return resp.content[0].text.strip()


def _call_gemini(user: str, system: str, max_tokens: int) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "google-genai 미설치. `pip install google-genai` 실행 후 재시도."
        )

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY가 .env에 설정되지 않았습니다.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        system_instruction=system or None,
        thinking_config=types.ThinkingConfig(thinking_budget=0),  # JSON 출력을 위해 thinking 비활성화
    )
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=config,
    )
    # thinking 파트를 제외한 실제 텍스트만 추출
    text = resp.text or ""
    if not text and resp.candidates:
        parts = resp.candidates[0].content.parts or []
        text = "\n".join(
            p.text for p in parts
            if p.text and not getattr(p, "thought", False)
        )
    return text.strip()
