"""
dags/etl_weekly_dag.py
======================
Factory AI Navi — Airflow DAG (주 1회 전체 ETL)

매주 월요일 02:00에 전체 ETL 파이프라인 실행:
  1. DB 테이블 초기화
  2. KIAT 산업기술통계 수집·적재
  3. KEIT 사업공고 수집·적재
  4. NTIS R&D 과제 수집·적재
  5. KSNPC 산단 통계 수집·적재
  6. KOITA 로봇 실태조사 수집·적재
  7. 데이터 품질 검사 (수집 결과 XCom 집계)
  8. 벤치마크 집계 요약 갱신

변경 이력:
  v1.0 (2026-04-28) 최초 작성
  v1.1 (2026-05-28) XCom 결과 전달, 데이터 품질 검사 태스크, 실패 콜백 추가
"""

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.sensors.filesystem import FileSensor
    from airflow.utils.dates import days_ago
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

from datetime import datetime, timedelta
import os

DEFAULT_ARGS = {
    "owner":            "factory_ai_navi",
    "depends_on_past":  False,
    "email_on_failure": False,
    "email_on_retry":   False,
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# FileSensor가 확인할 Excel 파일 경로 (Airflow 컨테이너 내부 경로)
KIAT_EXCEL_PATH  = "/opt/airflow/data/raw/kiat_industry_2024.xlsx"
KOITA_EXCEL_PATH = "/opt/airflow/data/raw/koita_robot_survey_2024.xlsx"


# ══════════════════════════════════════════════
# 실패 콜백
# ══════════════════════════════════════════════

def on_failure_callback(context):
    """태스크 실패 시 로그 출력. Layer 3 구현 시 Slack/카카오 알림 연동 포인트."""
    from layer1_etl.config import logger
    ti     = context.get("task_instance")
    dag_id = context.get("dag").dag_id
    logger.error(
        "[WeeklyETL] 태스크 실패: dag=%s task=%s run_id=%s exception=%s",
        dag_id, ti.task_id, context.get("run_id"), context.get("exception"),
    )
    # TODO (Layer 3): 카카오 알림톡 또는 Slack webhook으로 실패 알림 발송


# ══════════════════════════════════════════════
# ETL Task 함수들
# ══════════════════════════════════════════════

def task_init_db(**context):
    """DB 테이블 초기화 (최초 1회 또는 스키마 변경 후)"""
    from layer1_etl.loaders.postgres_loader import PostgresLoader
    loader = PostgresLoader()
    loader.init_tables()
    healthy = loader.health_check()
    context["ti"].xcom_push(key="db_healthy", value=healthy)
    return {"status": "ok", "db_healthy": healthy}


def task_collect_kiat(**context):
    """KIAT 산업기술통계 수집 → 전처리 → 적재, 건수 XCom push"""
    from layer1_etl.collectors.kiat_collector import KiatCollector
    from layer1_etl.transformers.industry_standardizer import IndustryStandardizer
    from layer1_etl.transformers.unit_converter import UnitConverter
    from layer1_etl.transformers.missing_handler import MissingHandler
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = KiatCollector().run()
    df = IndustryStandardizer().transform(df)
    df = UnitConverter().transform(df, source="KIAT")
    df = MissingHandler().transform(df)
    count = PostgresLoader().load_industry_stats(df)
    context["ti"].xcom_push(key="kiat_loaded", value=count)
    return {"source": "KIAT", "loaded": count}


def task_collect_keit(**context):
    """KEIT 사업공고 수집 → 적재, 건수 XCom push"""
    from layer1_etl.collectors.keit_collector import KeitCollector
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = KeitCollector().run()
    count = PostgresLoader().load_subsidies(df)
    context["ti"].xcom_push(key="keit_loaded", value=count)
    return {"source": "KEIT", "loaded": count}


def task_collect_ntis(**context):
    """NTIS R&D 과제 수집 → 적재, 건수 XCom push"""
    from layer1_etl.collectors.ntis_collector import NtisCollector
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = NtisCollector().run()
    count = PostgresLoader().load_subsidies(df)
    context["ti"].xcom_push(key="ntis_loaded", value=count)
    return {"source": "NTIS", "loaded": count}


def task_collect_ksnpc(**context):
    """KSNPC 산단 통계 수집 → 전처리 → 적재, 건수 XCom push"""
    from layer1_etl.collectors.ksnpc_collector import KsnpcCollector
    from layer1_etl.transformers.industry_standardizer import IndustryStandardizer
    from layer1_etl.transformers.unit_converter import UnitConverter
    from layer1_etl.transformers.missing_handler import MissingHandler
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = KsnpcCollector().run()
    df = IndustryStandardizer().transform(df)
    df = UnitConverter().transform(df, source="KSNPC")
    df = MissingHandler().transform(df)
    count = PostgresLoader().load_industry_stats(df)
    context["ti"].xcom_push(key="ksnpc_loaded", value=count)
    return {"source": "KSNPC", "loaded": count}


def task_collect_koita(**context):
    """KOITA 로봇 실태조사 수집 → 전처리 → 적재, 건수 XCom push"""
    from layer1_etl.collectors.koita_collector import KoitaCollector
    from layer1_etl.transformers.industry_standardizer import IndustryStandardizer
    from layer1_etl.transformers.missing_handler import MissingHandler
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = KoitaCollector().run()
    df = IndustryStandardizer().transform(df)
    df = MissingHandler().transform(df)
    count = PostgresLoader().load_industry_stats(df)
    context["ti"].xcom_push(key="koita_loaded", value=count)
    return {"source": "KOITA", "loaded": count}


def task_quality_check(**context):
    """
    수집 결과 데이터 품질 검사.

    각 수집 태스크의 XCom 값을 집계하여:
    - 전체 수집 건수가 0이면 WARNING
    - DB 헬스체크 실패 시 RuntimeError 발생 (DAG 실패 처리)
    - 통과 시 품질 리포트를 XCom push
    """
    from layer1_etl.loaders.postgres_loader import PostgresLoader
    from layer1_etl.config import logger

    ti = context["ti"]

    counts = {
        "kiat":  ti.xcom_pull(task_ids="collect_kiat",  key="kiat_loaded")  or 0,
        "keit":  ti.xcom_pull(task_ids="collect_keit",  key="keit_loaded")  or 0,
        "ntis":  ti.xcom_pull(task_ids="collect_ntis",  key="ntis_loaded")  or 0,
        "ksnpc": ti.xcom_pull(task_ids="collect_ksnpc", key="ksnpc_loaded") or 0,
        "koita": ti.xcom_pull(task_ids="collect_koita", key="koita_loaded") or 0,
    }
    total = sum(counts.values())

    loader = PostgresLoader()
    db_stats = loader.get_stats()
    db_healthy = loader.health_check()

    if not db_healthy:
        raise RuntimeError("[QualityCheck] DB 연결 불량 — ETL 결과 검증 불가")

    if total == 0:
        logger.warning(
            "[QualityCheck] 경고: 이번 주 수집 건수가 0입니다. "
            "API 키 및 파일 경로를 확인하세요. run_date=%s",
            context["ds"],
        )
    else:
        logger.info(
            "[QualityCheck] 통과: 총 %d건 수집 | DB 현황: %s | run_date=%s",
            total, db_stats, context["ds"],
        )

    report = {
        "run_date":    context["ds"],
        "counts":      counts,
        "total":       total,
        "db_stats":    db_stats,
        "db_healthy":  db_healthy,
        "quality_ok":  total > 0 and db_healthy,
    }
    ti.xcom_push(key="quality_report", value=report)
    return report


def task_rebuild_benchmark(**context):
    """벤치마크 집계 요약 테이블 갱신"""
    from layer1_etl.loaders.postgres_loader import PostgresLoader
    loader = PostgresLoader()
    count = loader.rebuild_benchmark_summary()
    context["ti"].xcom_push(key="benchmark_updated", value=count)
    return {"updated": count}


# ══════════════════════════════════════════════
# DAG 정의 (Airflow 설치 시에만 활성화)
# ══════════════════════════════════════════════

if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="factory_ai_navi_weekly_etl",
        default_args={**DEFAULT_ARGS, "on_failure_callback": on_failure_callback},
        description="Factory AI Navi — 주 1회 전체 ETL 파이프라인",
        schedule_interval="0 2 * * 1",   # 매주 월요일 02:00
        start_date=days_ago(1),
        catchup=False,
        tags=["factory_ai_navi", "etl", "layer1"],
    ) as dag:

        t_init = PythonOperator(
            task_id="init_db",
            python_callable=task_init_db,
        )

        # ── Excel 파일 존재 여부 확인 (FileSensor) ──────────────────────────
        # USE_MOCK_DATA=true 환경에서는 파일이 없어도 mock으로 동작하므로
        # poke_interval/timeout을 짧게 설정하고 soft_fail=True로 비차단 처리
        t_wait_kiat = FileSensor(
            task_id="wait_for_kiat_excel",
            filepath=KIAT_EXCEL_PATH,
            poke_interval=60,          # 60초마다 확인
            timeout=600,               # 10분 대기 후 포기
            soft_fail=True,            # 파일 없어도 downstream 계속 진행
            mode="poke",
        )
        t_wait_koita = FileSensor(
            task_id="wait_for_koita_excel",
            filepath=KOITA_EXCEL_PATH,
            poke_interval=60,
            timeout=600,
            soft_fail=True,
            mode="poke",
        )

        t_kiat = PythonOperator(
            task_id="collect_kiat",
            python_callable=task_collect_kiat,
        )
        t_keit = PythonOperator(
            task_id="collect_keit",
            python_callable=task_collect_keit,
        )
        t_ntis = PythonOperator(
            task_id="collect_ntis",
            python_callable=task_collect_ntis,
        )
        t_ksnpc = PythonOperator(
            task_id="collect_ksnpc",
            python_callable=task_collect_ksnpc,
        )
        t_koita = PythonOperator(
            task_id="collect_koita",
            python_callable=task_collect_koita,
        )
        t_quality = PythonOperator(
            task_id="quality_check",
            python_callable=task_quality_check,
        )
        t_bench = PythonOperator(
            task_id="rebuild_benchmark",
            python_callable=task_rebuild_benchmark,
        )

        # ── 실행 순서 ────────────────────────────────────────────────────────
        # init_db
        #   ├─ wait_for_kiat_excel → collect_kiat  ┐
        #   ├─ collect_keit                          ├─ quality_check → rebuild_benchmark
        #   ├─ collect_ntis                          │
        #   ├─ collect_ksnpc                         │
        #   └─ wait_for_koita_excel → collect_koita ┘
        t_init >> t_wait_kiat  >> t_kiat
        t_init >> t_keit
        t_init >> t_ntis
        t_init >> t_ksnpc
        t_init >> t_wait_koita >> t_koita

        [t_kiat, t_keit, t_ntis, t_ksnpc, t_koita] >> t_quality >> t_bench
