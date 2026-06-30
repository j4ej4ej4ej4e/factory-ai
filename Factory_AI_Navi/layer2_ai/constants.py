"""
layer2_ai/constants.py
=======================
Factory AI Navi — Layer 2 전용 상수 정의

업종별 AI ROI 파라미터, 활성화 업종 코드 등
"""

# ──────────────────────────────────────────────
# 12개 핵심 업종 코드
# ──────────────────────────────────────────────
ACTIVE_INDUSTRY_CODES: list[str] = [
    # 그룹 A — 뿌리업종 6개
    "C243", "C251", "C259", "C289", "C301", "C302",
    # 그룹 B — 일반 제조업 6개
    "C10", "C22", "C25", "C26", "C29", "C30",
]

ROOTS_INDUSTRY_CODES: list[str] = ["C243", "C251", "C259", "C289", "C301", "C302"]

# ──────────────────────────────────────────────
# 업종별 AI ROI 파라미터
# implementation_cost_range : 구축비용 범위 (만원)
# labor_reduction_rate      : 인건비 절감률 (0.0~1.0)
# energy_reduction_rate     : 에너지 절감률 (0.0~1.0)
# defect_improvement_pp     : 불량률 개선 포인트 (%)
# ──────────────────────────────────────────────
INDUSTRY_ROI_PARAMS: dict[str, dict] = {
    "C243": {
        "name": "주조",
        "best_ai": ["process_control", "vision_inspection"],
        "labor_reduction_rate": 0.08,
        "energy_reduction_rate": 0.12,
        "defect_improvement_pp": 1.5,
        "implementation_cost_range": (5000, 10000),
    },
    "C251": {
        "name": "금형",
        "best_ai": ["predictive_maintenance", "vision_inspection"],
        "labor_reduction_rate": 0.10,
        "energy_reduction_rate": 0.05,
        "defect_improvement_pp": 1.0,
        "implementation_cost_range": (4000, 8000),
    },
    "C259": {
        "name": "소성가공",
        "best_ai": ["predictive_maintenance", "process_control"],
        "labor_reduction_rate": 0.07,
        "energy_reduction_rate": 0.10,
        "defect_improvement_pp": 1.2,
        "implementation_cost_range": (5000, 9000),
    },
    "C289": {
        "name": "용접",
        "best_ai": ["vision_inspection", "robot_automation"],
        "labor_reduction_rate": 0.12,
        "energy_reduction_rate": 0.05,
        "defect_improvement_pp": 1.3,
        "implementation_cost_range": (4000, 8000),
    },
    "C301": {
        "name": "표면처리",
        "best_ai": ["energy_optimization", "process_control"],
        "labor_reduction_rate": 0.06,
        "energy_reduction_rate": 0.15,
        "defect_improvement_pp": 1.0,
        "implementation_cost_range": (4000, 7000),
    },
    "C302": {
        "name": "열처리",
        "best_ai": ["energy_optimization", "process_control"],
        "labor_reduction_rate": 0.05,
        "energy_reduction_rate": 0.18,
        "defect_improvement_pp": 0.8,
        "implementation_cost_range": (6000, 10000),
    },
    "C10": {
        "name": "식품제조",
        "best_ai": ["vision_inspection", "quality_control"],
        "labor_reduction_rate": 0.10,
        "energy_reduction_rate": 0.06,
        "defect_improvement_pp": 0.7,
        "implementation_cost_range": (3000, 6000),
    },
    "C22": {
        "name": "사출성형",
        "best_ai": ["predictive_maintenance", "vision_inspection"],
        "labor_reduction_rate": 0.09,
        "energy_reduction_rate": 0.08,
        "defect_improvement_pp": 1.4,
        "implementation_cost_range": (4000, 8000),
    },
    "C25": {
        "name": "금속가공",
        "best_ai": ["predictive_maintenance", "vision_inspection"],
        "labor_reduction_rate": 0.10,
        "energy_reduction_rate": 0.07,
        "defect_improvement_pp": 1.2,
        "implementation_cost_range": (4000, 8000),
    },
    "C26": {
        "name": "전자부품",
        "best_ai": ["vision_inspection", "quality_control"],
        "labor_reduction_rate": 0.12,
        "energy_reduction_rate": 0.04,
        "defect_improvement_pp": 0.4,
        "implementation_cost_range": (5000, 10000),
    },
    "C29": {
        "name": "산업기계",
        "best_ai": ["predictive_maintenance", "robot_automation"],
        "labor_reduction_rate": 0.08,
        "energy_reduction_rate": 0.05,
        "defect_improvement_pp": 0.7,
        "implementation_cost_range": (5000, 9000),
    },
    "C30": {
        "name": "자동차부품",
        "best_ai": ["vision_inspection", "quality_control", "robot_automation"],
        "labor_reduction_rate": 0.15,
        "energy_reduction_rate": 0.05,
        "defect_improvement_pp": 0.3,
        "implementation_cost_range": (6000, 12000),
    },
}

# ──────────────────────────────────────────────
# Pain point → 우선 추천 AI 유형 매핑
# ──────────────────────────────────────────────
PAIN_POINT_TO_AI: dict[str, list[str]] = {
    "defect_high":            ["vision_inspection", "quality_control"],
    "equipment_breakdown":    ["predictive_maintenance"],
    "energy_cost":            ["energy_optimization", "process_control"],
    "quality_inconsistency":  ["quality_control", "process_control"],
    "delivery_delay":         ["demand_forecasting", "supply_chain"],
    "labor_shortage":         ["robot_automation"],
    "material_waste":         ["process_control", "quality_control"],
}

# ──────────────────────────────────────────────
# 업종별 한글명 (INDUSTRY_MAP_REVERSE 보완용)
# ──────────────────────────────────────────────
INDUSTRY_NAMES: dict[str, str] = {
    "C243": "주조",
    "C251": "금형",
    "C259": "소성가공",
    "C289": "용접",
    "C301": "표면처리",
    "C302": "열처리",
    "C10":  "식품제조",
    "C22":  "사출성형",
    "C25":  "금속가공",
    "C26":  "전자부품",
    "C29":  "산업기계",
    "C30":  "자동차부품",
}
