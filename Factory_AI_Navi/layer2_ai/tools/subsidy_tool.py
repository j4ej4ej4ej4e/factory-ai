"""
layer2_ai/tools/subsidy_tool.py
=================================
Factory AI Navi — 지원사업 조회 툴

keit_subsidies 테이블에서 기업 조건에 맞는 지원사업을 검색합니다.
뿌리업종 전용 우선 매칭 + 마감 임박 긴급 정렬 적용.
"""

from layer1_etl.models.base import SessionLocal
from layer1_etl.models.subsidies import KeitSubsidy
from layer2_ai.config import logger
from layer2_ai.constants import ROOTS_INDUSTRY_CODES


class SubsidyTool:
    """
    지원사업 매칭 조회 툴.

    사용 예시
    ---------
    tool = SubsidyTool()
    results = tool.search("C25", "small", ai_types=["predictive_maintenance"])
    """

    def search(
        self,
        industry_code: str,
        company_size: str,
        ai_types: list[str] | None = None,
        top_n: int = 5,
    ) -> list[dict]:
        """
        기업 조건에 맞는 지원사업 검색.

        매칭 기준
        ---------
        1. is_active=True 공고만
        2. target_industry_codes 에 industry_code 포함
        3. target_company_sizes 에 company_size 포함
        4. (선택) target_ai_types 중 하나 이상 일치 → 매칭 점수 상향
        5. 뿌리업종이면 뿌리 전용 카테고리 우선 점수 부여
        6. 마감 D-7 이내 긴급 공고 최우선 정렬

        Parameters
        ----------
        industry_code : str
            KSIC 업종코드
        company_size : str
            기업 규모 ("small" | "medium")
        ai_types : list[str] | None
            진단 결과 AI 유형 목록 (매칭 점수 상향에 사용)
        top_n : int
            반환할 최대 건수

        Returns
        -------
        list[dict]
            KeitSubsidy.to_dict() + match_score, is_urgent 포함
        """
        session = SessionLocal()
        try:
            all_subsidies = session.query(KeitSubsidy).filter_by(is_active=True).all()
            subsidies_data = [s.to_dict() for s in all_subsidies]
            urgency_map = {s.to_dict()["subsidy_id"]: s.is_urgent for s in all_subsidies}
        finally:
            session.close()

        is_roots = industry_code in ROOTS_INDUSTRY_CODES
        matched: list[dict] = []

        for s in subsidies_data:
            score = self._calc_match_score(s, industry_code, company_size, ai_types, is_roots)
            if score is None:
                continue
            s["match_score"] = score
            s["is_urgent"] = urgency_map.get(s["subsidy_id"], False)
            matched.append(s)

        # 정렬: 긴급 우선 → 매칭 점수 내림차순 → 마감일 오름차순
        matched.sort(key=lambda x: (
            -int(x["is_urgent"]),
            -x["match_score"],
            x.get("application_end") or "9999-12-31",
        ))

        logger.info(
            "[Subsidy] 매칭: 전체 %d건 중 %d건 해당, 상위 %d건 반환",
            len(subsidies_data), len(matched), min(top_n, len(matched)),
        )
        return matched[:top_n]

    # ──────────────────────────────────────────────
    # 내부 메서드
    # ──────────────────────────────────────────────

    @staticmethod
    def _calc_match_score(
        subsidy: dict,
        industry_code: str,
        company_size: str,
        ai_types: list[str] | None,
        is_roots: bool,
    ) -> float | None:
        """
        지원사업 하나의 매칭 점수 계산.
        조건 미충족 시 None 반환 (필터 역할).
        """
        # ① 업종 매칭 (필수)
        target_codes_raw = subsidy.get("target_industry_codes") or ""
        if target_codes_raw:
            target_codes = [c.strip() for c in target_codes_raw.split(",")]
            if industry_code not in target_codes:
                return None

        # ② 규모 매칭 (필수)
        target_sizes_raw = subsidy.get("target_company_sizes") or ""
        if target_sizes_raw:
            target_sizes = [s.strip() for s in target_sizes_raw.split(",")]
            if company_size not in target_sizes:
                return None

        score = 1.0

        # ③ AI 유형 매칭 (선택 — 점수 상향)
        if ai_types:
            target_ai_raw = subsidy.get("target_ai_types") or ""
            if target_ai_raw:
                target_ai = [a.strip() for a in target_ai_raw.split(",")]
                matched_count = sum(1 for at in ai_types if at in target_ai)
                score += matched_count * 0.3

        # ④ 뿌리업종 전용 보너스
        if is_roots and subsidy.get("program_category") in ("뿌리업종", "뿌리산업"):
            score += 0.5

        return round(score, 2)
