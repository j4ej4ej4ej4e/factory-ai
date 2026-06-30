"""
scripts/seed_db.py
==================
Factory AI Navi — 벤치마크 DB 시드 스크립트

진행현황_TODO.txt v2.0 확정값 기준 24행을 SQLite 파일 DB에 적재합니다.
Layer 2 에이전트 실행 전에 반드시 한 번 실행해야 합니다.

실행 방법
---------
  # 프로젝트 루트에서 실행
  python scripts/seed_db.py

  # 이미 시드된 경우 덮어쓰기
  python scripts/seed_db.py --force
"""

import argparse
import os
import sys
from pathlib import Path

# ── 프로젝트 루트를 sys.path에 추가 ──────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# SQLite 파일 DB 강제 사용 (메모리 DB 대신 영구 저장)
os.environ.setdefault("USE_MOCK_DATA", "false")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / 'dev_local.db'}")

from datetime import date

from layer1_etl.models.base import Base, engine, SessionLocal, init_db
from layer1_etl.models.industry_stats import KiatIndustryStat
from layer1_etl.models.subsidies import KeitSubsidy
from layer1_etl.models.benchmark import BenchmarkSummary

# ──────────────────────────────────────────────
# 벤치마크 24행 (진행현황_TODO.txt v2.0 확정값)
# KSIC │ 규모   │불량%│가동%│AI%│인건비│에너지%│로봇%│ROI월│생산액│재료비%
# ──────────────────────────────────────────────
BENCHMARK_ROWS = [
    # ── 뿌리업종 6개 ──────────────────────────────
    ("C243", "주조",          "small",  5.2, 62,  1.5, 3600, 18, 3,  36, 2800, 55),
    ("C243", "주조",          "medium", 3.8, 72,  3.0, 4200, 15, 8,  30, 4000, 58),
    ("C251", "금형",          "small",  3.0, 68,  2.0, 4100,  8, 2,  30, 3200, 30),
    ("C251", "금형",          "medium", 1.8, 78,  5.0, 4800,  7, 6,  24, 4800, 32),
    ("C259", "소성가공",      "small",  3.5, 65,  1.5, 3700, 14, 2,  36, 2600, 50),
    ("C259", "소성가공",      "medium", 2.2, 74,  3.5, 4300, 12, 6,  30, 3800, 52),
    ("C289", "용접",          "small",  4.2, 70,  2.0, 3500,  7, 5,  28, 2400, 45),
    ("C289", "용접",          "medium", 2.8, 78,  4.5, 4100,  6, 15, 24, 3500, 48),
    ("C301", "표면처리",      "small",  3.3, 67,  1.0, 3400, 20, 1,  40, 2200, 35),
    ("C301", "표면처리",      "medium", 2.0, 75,  2.5, 3900, 17, 3,  32, 3200, 38),
    ("C302", "열처리",        "small",  2.5, 72,  1.5, 3600, 28, 1,  36, 2800, 25),
    ("C302", "열처리",        "medium", 1.5, 80,  3.5, 4200, 24, 2,  28, 4100, 28),
    # ── 일반 제조업 6개 ──────────────────────────
    ("C10",  "식품제조",      "small",  1.8, 75,  2.5, 3100, 10, 2,  28, 2800, 65),
    ("C10",  "식품제조",      "medium", 0.9, 82,  6.0, 3800,  9, 5,  22, 4100, 68),
    ("C22",  "사출성형",      "small",  4.0, 66,  4.0, 3400, 11, 4,  26, 2600, 55),
    ("C22",  "사출성형",      "medium", 2.5, 76,  9.0, 4000,  9, 12, 20, 3800, 58),
    ("C25",  "금속가공",      "small",  3.2, 68,  3.5, 3800,  9, 5,  24, 3200, 45),
    ("C25",  "금속가공",      "medium", 1.8, 78, 11.0, 4400,  8, 16, 18, 4700, 48),
    ("C26",  "전자부품",      "small",  1.2, 80, 12.0, 4100,  6, 8,  18, 4800, 52),
    ("C26",  "전자부품",      "medium", 0.5, 87, 22.0, 5000,  5, 22, 14, 7200, 55),
    ("C29",  "산업기계",      "small",  2.0, 72,  4.5, 4100,  5, 4,  26, 3800, 40),
    ("C29",  "산업기계",      "medium", 1.2, 80,  9.0, 4800,  5, 12, 20, 5600, 42),
    ("C30",  "자동차부품",    "small",  0.8, 84, 10.0, 4200,  7, 15, 18, 4500, 50),
    ("C30",  "자동차부품",    "medium", 0.3, 90, 20.0, 5100,  6, 35, 12, 7000, 53),
]

# ──────────────────────────────────────────────
# Mock 지원사업 8건 (CSV 파일과 동일)
# ──────────────────────────────────────────────
MOCK_SUBSIDIES = [
    {
        "subsidy_id": "KEIT-2026-0501", "source": "KEIT",
        "program_name": "제조AI특화 스마트공장 구축 지원", "program_category": "스마트공장",
        "target_industry_codes": "C25,C10,C22,C243", "target_company_sizes": "small,medium",
        "target_ai_types": "predictive_maintenance,vision_inspection",
        "max_support_amount": 20000, "min_support_amount": 3000, "co_funding_rate": 0.5,
        "application_start": date(2026, 3, 29), "application_end": date(2026, 7, 14),
        "announcement_date": date(2026, 3, 29),
        "apply_url": "https://www.smart-factory.kr",
        "description": "중소 제조기업 AI 기반 스마트공장 구축 지원. 예측유지보수·품질검사 AI 우선 지원.",
        "requirements": "종업원 300인 미만 제조업, 스마트공장 1~2수준 기업",
        "is_active": True,
    },
    {
        "subsidy_id": "KEIT-2026-0502", "source": "KEIT",
        "program_name": "배터리·전기전자 분야 기술개발 과제", "program_category": "R&D",
        "target_industry_codes": "C26,C27,C28", "target_company_sizes": "small,medium,mid_large",
        "target_ai_types": "quality_control,process_control",
        "max_support_amount": 50000, "min_support_amount": 10000, "co_funding_rate": 0.35,
        "application_start": date(2026, 4, 8), "application_end": date(2026, 7, 27),
        "announcement_date": date(2026, 4, 8),
        "apply_url": "https://www.keit.re.kr",
        "description": "배터리·전기전자 업종 AI 공정최적화 R&D 지원. 기업부설연구소 필수.",
        "requirements": "기업부설연구소 보유, 기술개발 의지 확인",
        "is_active": True,
    },
    {
        "subsidy_id": "SBC-2026-0301", "source": "KEIT",
        "program_name": "뿌리업종 AI 응용상용화 지원", "program_category": "뿌리업종",
        "target_industry_codes": "C243,C251,C259,C289,C301,C302",
        "target_company_sizes": "small,medium",
        "target_ai_types": "vision_inspection,predictive_maintenance",
        "max_support_amount": 30000, "min_support_amount": 5000, "co_funding_rate": 0.4,
        "application_start": date(2026, 4, 18), "application_end": date(2026, 7, 18),
        "announcement_date": date(2026, 4, 18),
        "apply_url": "https://www.sbiz.or.kr",
        "description": "주조·금형·소성가공 등 뿌리업종 AI 비전검사 및 공정개선 지원.",
        "requirements": "뿌리산업진흥법 제2조 해당 뿌리업종 영위 기업",
        "is_active": True,
    },
    {
        "subsidy_id": "MSS-2026-0401", "source": "KEIT",
        "program_name": "대중소 상생형 AI트랙 (삼성전자 협력)", "program_category": "상생협력",
        "target_industry_codes": "C25,C26,C30", "target_company_sizes": "small",
        "target_ai_types": "process_control,robot_automation",
        "max_support_amount": 30000, "min_support_amount": 5000, "co_funding_rate": 0.3,
        "application_start": date(2026, 4, 23), "application_end": date(2026, 7, 23),
        "announcement_date": date(2026, 4, 23),
        "apply_url": "https://www.mss.go.kr",
        "description": "삼성전자 협력사 대상 AI 자동화 솔루션 구축 지원.",
        "requirements": "삼성전자 1·2차 협력사, 종업원 50인 미만 소기업",
        "is_active": True,
    },
    {
        "subsidy_id": "MOTIE-2026-0601", "source": "KEIT",
        "program_name": "지역특화 스마트공장 보급·확산", "program_category": "스마트공장",
        "target_industry_codes": "C10,C22,C25,C24", "target_company_sizes": "small,medium",
        "target_ai_types": "predictive_maintenance,energy_optimization",
        "max_support_amount": 10000, "min_support_amount": 2000, "co_funding_rate": 0.5,
        "application_start": date(2026, 4, 13), "application_end": date(2026, 7, 13),
        "announcement_date": date(2026, 4, 13),
        "apply_url": "https://www.smart-factory.kr",
        "description": "지역 산업단지 입주 중소기업 스마트공장 구축. 에너지 절감 우선.",
        "requirements": "국가산업단지 또는 일반산업단지 입주 기업",
        "is_active": True,
    },
    {
        "subsidy_id": "NTIS-2026-M001", "source": "NTIS",
        "program_name": "제조공정 AI 비전검사 기술 개발", "program_category": "R&D",
        "target_industry_codes": "C25,C22", "target_company_sizes": "small,medium",
        "target_ai_types": "vision_inspection",
        "max_support_amount": 25000, "min_support_amount": 5000, "co_funding_rate": 0.4,
        "application_start": date(2026, 4, 21), "application_end": date(2026, 7, 27),
        "announcement_date": date(2026, 4, 21),
        "apply_url": "https://www.ntis.go.kr",
        "description": "금속·사출 공정 AI 비전검사 시스템 개발 R&D",
        "requirements": "중소기업 기술개발 역량 보유",
        "is_active": True,
    },
    {
        "subsidy_id": "NTIS-2026-M002", "source": "NTIS",
        "program_name": "식품제조 스마트 품질관리 AI 플랫폼", "program_category": "R&D",
        "target_industry_codes": "C10", "target_company_sizes": "small,medium",
        "target_ai_types": "quality_control",
        "max_support_amount": 15000, "min_support_amount": 3000, "co_funding_rate": 0.45,
        "application_start": date(2026, 4, 14), "application_end": date(2026, 7, 13),
        "announcement_date": date(2026, 4, 14),
        "apply_url": "https://www.ntis.go.kr",
        "description": "식품 제조 HACCP 연계 AI 실시간 품질 모니터링",
        "requirements": "식품제조 허가 보유 기업",
        "is_active": True,
    },
    {
        "subsidy_id": "NTIS-2026-M003", "source": "NTIS",
        "program_name": "산업용 IoT·AI 융합 예측유지보수 기술", "program_category": "R&D",
        "target_industry_codes": "C25,C24,C29,C243,C251,C259,C289,C301,C302",
        "target_company_sizes": "medium",
        "target_ai_types": "predictive_maintenance",
        "max_support_amount": 40000, "min_support_amount": 10000, "co_funding_rate": 0.35,
        "application_start": date(2026, 4, 25), "application_end": date(2026, 8, 26),
        "announcement_date": date(2026, 4, 25),
        "apply_url": "https://www.ntis.go.kr",
        "description": "IoT 센서 + AI 기반 설비 고장 예측 시스템 R&D",
        "requirements": "기업부설연구소 보유, 제조업 영위",
        "is_active": True,
    },
]


def seed_industry_stats(session, force: bool = False) -> int:
    """kiat_industry_stats 테이블에 24행 시드"""
    if not force:
        count = session.query(KiatIndustryStat).count()
        if count >= 24:
            print(f"  [Skip] kiat_industry_stats 이미 {count}행 존재 (--force로 덮어쓰기)")
            return 0

    loaded = 0
    for row in BENCHMARK_ROWS:
        (code, name, size, defect, operating, ai_rate,
         labor, energy, robot, roi_months, production, material) = row

        existing = session.query(KiatIndustryStat).filter_by(
            industry_code=code, company_size=size, reference_year=2024
        ).first()

        data = dict(
            industry_code=code,
            industry_name=name,
            company_size=size,
            reference_year=2024,
            avg_defect_rate=defect,
            avg_operating_rate=operating,
            ai_adoption_rate=ai_rate,
            avg_labor_cost_per_person=float(labor),
            avg_energy_cost_ratio=float(energy),
            robot_adoption_rate=float(robot),
            avg_robot_roi_months=float(roi_months),
            avg_production_per_person=float(production),
            avg_material_cost_ratio=float(material),
            data_source="KIAT_MANUAL_2024",
        )

        if existing:
            for k, v in data.items():
                if k not in ("industry_code", "company_size", "reference_year"):
                    setattr(existing, k, v)
        else:
            session.add(KiatIndustryStat(**data))

        loaded += 1

    session.commit()
    print(f"  [OK] kiat_industry_stats: {loaded}행 적재")
    return loaded


def seed_subsidies(session, force: bool = False) -> int:
    """keit_subsidies 테이블에 mock 지원사업 8건 시드"""
    if not force:
        count = session.query(KeitSubsidy).count()
        if count >= 8:
            print(f"  [Skip] keit_subsidies 이미 {count}건 존재 (--force로 덮어쓰기)")
            return 0

    loaded = 0
    for s in MOCK_SUBSIDIES:
        existing = session.query(KeitSubsidy).filter_by(
            subsidy_id=s["subsidy_id"], source=s["source"]
        ).first()

        if existing:
            for k, v in s.items():
                if k not in ("subsidy_id", "source"):
                    setattr(existing, k, v)
        else:
            session.add(KeitSubsidy(**s))

        loaded += 1

    session.commit()
    print(f"  [OK] keit_subsidies: {loaded}건 적재")
    return loaded


def seed_benchmark_summary(session) -> int:
    """benchmark_summary 집계 테이블 갱신"""
    from layer1_etl.loaders.postgres_loader import PostgresLoader
    loader = PostgresLoader()
    count = loader.rebuild_benchmark_summary()
    print(f"  [OK] benchmark_summary: {count}건 집계")
    return count


def main():
    parser = argparse.ArgumentParser(description="Factory AI Navi — DB 시드")
    parser.add_argument("--force", action="store_true", help="기존 데이터 덮어쓰기")
    args = parser.parse_args()

    print("=" * 50)
    print("Factory AI Navi — DB 시드 시작")
    print(f"DB: {os.environ.get('DATABASE_URL')}")
    print("=" * 50)

    # 테이블 생성
    init_db()

    session = SessionLocal()
    try:
        n1 = seed_industry_stats(session, force=args.force)
        n2 = seed_subsidies(session, force=args.force)
    finally:
        session.close()

    n3 = seed_benchmark_summary(SessionLocal())

    print("=" * 50)
    print(f"완료: 업종통계 {n1}행 / 지원사업 {n2}건 / 벤치마크 {n3}건")
    print("이제 Layer 2 에이전트를 실행할 수 있습니다.")
    print("=" * 50)


if __name__ == "__main__":
    main()
