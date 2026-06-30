"""
dags/etl_daily_dag.py
=====================
Factory AI Navi — Airflow DAG (매일 지원사업 공고 갱신)

매일 23:00에 지원사업 공고만 수집·갱신:
  1. KEIT 사업공고 수집·적재
  2. NTIS R&D 과제 수집·적재
  3. 마감 D-7 이내 긴급 공고 탐지 및 XCom 기록
  4. 데이터 품질 검사

주간 전체 ETL(etl_weekly_dag)과 역할 분리:
  - etl_weekly_dag  : 업종통계·벤치마크 등 무거운 배치 (매주 월요일)
  - etl_daily_dag   : 공고·마감임박 감지 등 가벼운 실시간성 작업 (매일)
"""

try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
    from airflow.utils.dates import days_ago
    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

from datetime import datetime, timedelta

DEFAULT_ARGS = {
    "owner":             "factory_ai_navi",
    "depends_on_past":   False,
    "email_on_failure":  False,
    "email_on_retry":    False,
    "retries":           1,
    "retry_delay":       timedelta(minutes=3),
    "execution_timeout": timedelta(hours=1),
}


# ══════════════════════════════════════════════
# Task 함수
# ══════════════════════════════════════════════

def task_collect_keit_daily(**context):
    """KEIT 사업공고 수집 → 적재, 수집 건수 XCom push"""
    from layer1_etl.collectors.keit_collector import KeitCollector
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = KeitCollector().run()
    count = PostgresLoader().load_subsidies(df)
    context["ti"].xcom_push(key="keit_loaded", value=count)
    return {"source": "KEIT", "loaded": count}


def task_collect_ntis_daily(**context):
    """NTIS R&D 과제 수집 → 적재, 수집 건수 XCom push"""
    from layer1_etl.collectors.ntis_collector import NtisCollector
    from layer1_etl.loaders.postgres_loader import PostgresLoader

    df = NtisCollector().run()
    count = PostgresLoader().load_subsidies(df)
    context["ti"].xcom_push(key="ntis_loaded", value=count)
    return {"source": "NTIS", "loaded": count}


def task_detect_urgent_subsidies(**context):
    """
    마감 D-7 이내 긴급 공고 탐지.
    탐지 결과를 XCom에 push하여 후속 알림 태스크(Layer 3 구현 시)가 사용할 수 있도록 함.
    """
    from layer1_etl.models.base import SessionLocal
    from layer1_etl.models.subsidies import KeitSubsidy
    from layer1_etl.config import logger

    session = SessionLocal()
    try:
        active_subsidies = session.query(KeitSubsidy).filter_by(is_active=True).all()
        urgent = [
            {
                "subsidy_id": s.subsidy_id,
                "title":      s.title,
                "source":     s.source,
                "deadline":   s.deadline.isoformat() if s.deadline else None,
                "days_left":  s.days_until_deadline,
            }
            for s in active_subsidies
            if s.is_urgent  # days_until_deadline <= 7
        ]
    finally:
        session.close()

    logger.info("[DailyDAG] 마감 D-7 긴급 공고: %d건", len(urgent))
    context["ti"].xcom_push(key="urgent_subsidies", value=urgent)
    context["ti"].xcom_push(key="urgent_count", value=len(urgent))
    return {"urgent_count": len(urgent), "urgent": urgent}


def task_daily_quality_check(**context):
    """
    일일 데이터 품질 검사.
    수집 결과가 0건이면 경고 로그 출력 (파이프라인 실패로 간주하지 않음).
    """
    from layer1_etl.config import logger

    ti = context["ti"]
    keit_loaded = ti.xcom_pull(task_ids="collect_keit_daily", key="keit_loaded") or 0
    ntis_loaded = ti.xcom_pull(task_ids="collect_ntis_daily", key="ntis_loaded") or 0
    urgent_count = ti.xcom_pull(task_ids="detect_urgent_subsidies", key="urgent_count") or 0

    total = keit_loaded + ntis_loaded
    result = {
        "run_date":     context["ds"],
        "keit_loaded":  keit_loaded,
        "ntis_loaded":  ntis_loaded,
        "total_loaded": total,
        "urgent_count": urgent_count,
        "quality_ok":   total > 0,
    }

    if total == 0:
        logger.warning(
            "[DailyDAG] 품질 경고: 오늘 수집된 공고가 0건입니다. "
            "API 키 및 네트워크 상태를 확인하세요. run_date=%s",
            context["ds"],
        )
    else:
        logger.info(
            "[DailyDAG] 품질 검사 통과: 총 %d건 수집, 긴급 공고 %d건. run_date=%s",
            total, urgent_count, context["ds"],
        )

    context["ti"].xcom_push(key="daily_quality_report", value=result)
    return result


def on_failure_callback(context):
    """태스크 실패 시 로그 출력 (실제 운영 시 Slack/이메일 연동 포인트)"""
    from layer1_etl.config import logger
    task_id = context.get("task_instance").task_id
    dag_id  = context.get("dag").dag_id
    run_id  = context.get("run_id")
    logger.error(
        "[DailyDAG] 태스크 실패: dag=%s task=%s run_id=%s",
        dag_id, task_id, run_id,
    )
    # TODO (Layer 3): Slack webhook 또는 카카오 알림톡으로 실패 알림 발송


# ══════════════════════════════════════════════
# DAG 정의
# ══════════════════════════════════════════════

if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="factory_ai_navi_daily_subsidy",
        default_args={**DEFAULT_ARGS, "on_failure_callback": on_failure_callback},
        description="Factory AI Navi — 매일 지원사업 공고 갱신 및 긴급 마감 감지",
        schedule_interval="0 23 * * *",   # 매일 23:00
        start_date=days_ago(1),
        catchup=False,
        tags=["factory_ai_navi", "etl", "daily", "subsidies"],
    ) as dag:

        t_keit = PythonOperator(
            task_id="collect_keit_daily",
            python_callable=task_collect_keit_daily,
        )
        t_ntis = PythonOperator(
            task_id="collect_ntis_daily",
            python_callable=task_collect_ntis_daily,
        )
        t_urgent = PythonOperator(
            task_id="detect_urgent_subsidies",
            python_callable=task_detect_urgent_subsidies,
        )
        t_quality = PythonOperator(
            task_id="daily_quality_check",
            python_callable=task_daily_quality_check,
        )

        # 병렬 수집 → 긴급 감지 → 품질 검사
        [t_keit, t_ntis] >> t_urgent >> t_quality
