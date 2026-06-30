"""
main.py
=======
Factory AI Navi — Layer 1 ETL 단독 실행 진입점

Airflow 없이 로컬에서 전체 ETL 파이프라인을 실행합니다.
mock 모드(.env: USE_MOCK_DATA=true)에서는 API 키 없이도 동작합니다.

실행 방법
---------
  # mock 모드 (API 키 없이 테스트)
  python -m layer1_etl.main

  # 특정 수집기만 실행
  python -m layer1_etl.main --source kiat
  python -m layer1_etl.main --source keit
  python -m layer1_etl.main --source all

  # 벤치마크 집계만 재실행
  python -m layer1_etl.main --rebuild-benchmark

작성일: 2026-04-28
버전: v1.0
"""

import argparse
import sys
import time
from datetime import datetime

from layer1_etl.config import USE_MOCK_DATA, logger, validate_config
from layer1_etl.collectors.kiat_collector import KiatCollector
from layer1_etl.collectors.keit_collector import KeitCollector
from layer1_etl.collectors.ntis_collector import NtisCollector
from layer1_etl.collectors.ksnpc_collector import KsnpcCollector
from layer1_etl.collectors.koita_collector import KoitaCollector
from layer1_etl.transformers.industry_standardizer import IndustryStandardizer
from layer1_etl.transformers.unit_converter import UnitConverter
from layer1_etl.transformers.missing_handler import MissingHandler
from layer1_etl.loaders.postgres_loader import PostgresLoader
from layer1_etl.loaders.vector_loader import VectorLoader


def run_industry_stats_pipeline(loader: PostgresLoader) -> dict:
    """
    업종 통계 수집 파이프라인 (KIAT + KSNPC + KOITA 통합).

    Returns
    -------
    dict : {'loaded': int, 'errors': int}
    """
    standardizer = IndustryStandardizer()
    converter    = UnitConverter()
    handler      = MissingHandler()

    collectors = [
        ("KIAT",  KiatCollector(),  "KIAT"),
        ("KSNPC", KsnpcCollector(), "KSNPC"),
        ("KOITA", KoitaCollector(), "KOITA"),
    ]

    total_loaded = 0
    total_errors = 0

    for name, collector, source in collectors:
        logger.info("=" * 50)
        logger.info("[Pipeline] %s 수집 시작", name)
        t0 = time.time()
        try:
            df = collector.run()
            if df.empty:
                logger.warning("[Pipeline] %s: 빈 데이터, 건너뜀", name)
                continue

            df = standardizer.transform(df)
            df = converter.transform(df, source=source)
            df = handler.transform(df)

            count = loader.load_industry_stats(df)
            total_loaded += count
            logger.info(
                "[Pipeline] %s 완료: %d건 적재 (%.1fs)",
                name, count, time.time() - t0
            )
        except Exception as e:
            logger.error("[Pipeline] %s 실패: %s", name, e, exc_info=True)
            total_errors += 1

    return {"loaded": total_loaded, "errors": total_errors}


def run_subsidies_pipeline(loader: PostgresLoader) -> dict:
    """
    지원사업 수집 파이프라인 (KEIT + NTIS 통합).

    Returns
    -------
    dict : {'loaded': int, 'errors': int}
    """
    collectors = [
        ("KEIT", KeitCollector()),
        ("NTIS", NtisCollector()),
    ]

    total_loaded = 0
    total_errors = 0

    for name, collector in collectors:
        logger.info("=" * 50)
        logger.info("[Pipeline] %s 공고 수집 시작", name)
        t0 = time.time()
        try:
            df = collector.run()
            if df.empty:
                logger.warning("[Pipeline] %s: 빈 데이터, 건너뜀", name)
                continue

            count = loader.load_subsidies(df)
            total_loaded += count
            logger.info(
                "[Pipeline] %s 완료: %d건 적재 (%.1fs)",
                name, count, time.time() - t0
            )
        except Exception as e:
            logger.error("[Pipeline] %s 실패: %s", name, e, exc_info=True)
            total_errors += 1

    return {"loaded": total_loaded, "errors": total_errors}


def run_full_pipeline() -> dict:
    """
    전체 ETL 파이프라인 실행.

    Returns
    -------
    dict : 전체 실행 결과 요약
    """
    start_time = datetime.utcnow()
    logger.info("=" * 60)
    logger.info("Factory AI Navi — Layer 1 ETL 파이프라인 시작")
    logger.info("시작 시각: %s", start_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
    logger.info("모드: %s", "MOCK" if USE_MOCK_DATA else "REAL")
    logger.info("=" * 60)

    # 설정 검증
    if not validate_config():
        logger.error("[Main] 설정 오류로 파이프라인 중단")
        sys.exit(1)

    loader = PostgresLoader()

    # Step 0: DB 연결 확인 및 테이블 초기화
    logger.info("[Step 0] DB 초기화")
    if not loader.health_check():
        logger.error("[Main] DB 연결 실패 — .env 설정을 확인하세요.")
        if not USE_MOCK_DATA:
            sys.exit(1)
    loader.init_tables()

    # Step 1: 업종 통계 파이프라인
    logger.info("[Step 1] 업종 통계 수집 파이프라인")
    stats_result = run_industry_stats_pipeline(loader)

    # Step 2: 지원사업 파이프라인
    logger.info("[Step 2] 정부지원사업 수집 파이프라인")
    subsidy_result = run_subsidies_pipeline(loader)

    # Step 3: 벤치마크 집계 요약 갱신
    logger.info("[Step 3] 벤치마크 집계 요약 갱신")
    bench_count = loader.rebuild_benchmark_summary()

    # Step 4: Vector 임베딩 (Layer 2 대비, 현재는 skip)
    logger.info("[Step 4] Vector 임베딩 — Layer 2 구현 시 활성화 (현재 skip)")
    # VectorLoader().embed_and_load_subsidies(df)

    # 최종 요약
    end_time = datetime.utcnow()
    elapsed  = (end_time - start_time).total_seconds()
    db_stats = loader.get_stats()

    result = {
        "status":           "SUCCESS" if stats_result["errors"] + subsidy_result["errors"] == 0 else "PARTIAL",
        "elapsed_seconds":  elapsed,
        "stats_loaded":     stats_result["loaded"],
        "subsidies_loaded": subsidy_result["loaded"],
        "benchmark_updated": bench_count,
        "errors":           stats_result["errors"] + subsidy_result["errors"],
        "db_table_counts":  db_stats,
    }

    logger.info("=" * 60)
    logger.info("ETL 파이프라인 완료")
    logger.info("  소요 시간   : %.1f초", elapsed)
    logger.info("  업종통계    : %d건 적재", result["stats_loaded"])
    logger.info("  지원사업    : %d건 적재", result["subsidies_loaded"])
    logger.info("  벤치마크    : %d건 갱신", result["benchmark_updated"])
    logger.info("  오류        : %d건", result["errors"])
    logger.info("  DB 현황     : %s", db_stats)
    logger.info("  상태        : %s", result["status"])
    logger.info("=" * 60)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Factory AI Navi Layer 1 ETL 파이프라인"
    )
    parser.add_argument(
        "--source",
        choices=["all", "kiat", "keit", "ntis", "ksnpc", "koita"],
        default="all",
        help="실행할 수집기 (기본: all)",
    )
    parser.add_argument(
        "--rebuild-benchmark",
        action="store_true",
        help="벤치마크 집계 요약만 재실행",
    )
    args = parser.parse_args()

    if args.rebuild_benchmark:
        loader = PostgresLoader()
        loader.init_tables()
        count = loader.rebuild_benchmark_summary()
        logger.info("[Main] 벤치마크 재집계 완료: %d건", count)
        return

    if args.source == "all":
        result = run_full_pipeline()
        sys.exit(0 if result["status"] != "FAIL" else 1)
    else:
        # 단일 수집기 실행
        loader = PostgresLoader()
        loader.init_tables()

        collector_map = {
            "kiat":  (KiatCollector,  "KIAT",  loader.load_industry_stats),
            "keit":  (KeitCollector,  "KEIT",  loader.load_subsidies),
            "ntis":  (NtisCollector,  "NTIS",  loader.load_subsidies),
            "ksnpc": (KsnpcCollector, "KSNPC", loader.load_industry_stats),
            "koita": (KoitaCollector, "KOITA", loader.load_industry_stats),
        }

        CollectorClass, source, load_fn = collector_map[args.source]
        df = CollectorClass().run()

        if not df.empty:
            if source in ("KIAT", "KSNPC", "KOITA"):
                df = IndustryStandardizer().transform(df)
                df = UnitConverter().transform(df, source=source)
                df = MissingHandler().transform(df)
            count = load_fn(df)
            logger.info("[Main] %s 완료: %d건 적재", args.source.upper(), count)
        else:
            logger.warning("[Main] %s: 수집 데이터 없음", args.source.upper())


if __name__ == "__main__":
    main()
