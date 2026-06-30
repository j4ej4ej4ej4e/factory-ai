"""
dags/data_cleanup_dag.py
========================
Factory AI Navi — Airflow DAG (월별 데이터 정리)

매월 1일 03:00에 실행:
  1. 만료된 지원사업 공고 아카이브 (is_active=False + deadline 경과 30일 이상)
  2. 30일 이상 된 raw CSV 파일 삭제 (data/raw/ 디렉토리)
  3. 오래된 processed 파일 정리 (data/processed/ 디렉토리)
  4. 정리 결과 리포트 XCom push
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
    "retry_delay":       timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# raw/processed 파일을 보관할 최대 일수
RAW_RETENTION_DAYS      = 30
PROCESSED_RETENTION_DAYS = 60
# 만료 공고를 DB에서 삭제하지 않고 보관할 최대 일수 (deadline 경과 후)
SUBSIDY_ARCHIVE_DAYS    = 30


# ══════════════════════════════════════════════
# Task 함수
# ══════════════════════════════════════════════

def task_archive_expired_subsidies(**context):
    """
    마감일이 SUBSIDY_ARCHIVE_DAYS일 이상 경과한 비활성 공고를 DB에서 물리 삭제.
    데이터 분석에 활용될 수 있으므로 기본값은 30일 보관 후 삭제.
    """
    from layer1_etl.models.base import SessionLocal
    from layer1_etl.models.subsidies import KeitSubsidy
    from layer1_etl.config import logger

    cutoff = datetime.utcnow() - timedelta(days=SUBSIDY_ARCHIVE_DAYS)

    session = SessionLocal()
    try:
        expired = (
            session.query(KeitSubsidy)
            .filter(
                KeitSubsidy.is_active == False,  # noqa: E712
                KeitSubsidy.deadline != None,     # noqa: E711
                KeitSubsidy.deadline < cutoff,
            )
            .all()
        )
        count = len(expired)
        for record in expired:
            session.delete(record)
        session.commit()
        logger.info("[Cleanup] 만료 공고 삭제: %d건 (기준일: %s)", count, cutoff.date())
    except Exception as e:
        session.rollback()
        logger.error("[Cleanup] 만료 공고 삭제 실패: %s", e)
        raise
    finally:
        session.close()

    context["ti"].xcom_push(key="archived_subsidies", value=count)
    return {"archived_subsidies": count, "cutoff_date": cutoff.isoformat()}


def task_cleanup_raw_files(**context):
    """
    data/raw/ 디렉토리에서 RAW_RETENTION_DAYS일 이상 된 CSV 파일 삭제.
    최신 수집 파일은 보존.
    """
    import os
    from pathlib import Path
    from layer1_etl.config import RAW_DIR, logger

    cutoff = datetime.utcnow() - timedelta(days=RAW_RETENTION_DAYS)
    deleted_files = []
    kept_files    = []

    for csv_file in Path(RAW_DIR).glob("*.csv"):
        mtime = datetime.utcfromtimestamp(csv_file.stat().st_mtime)
        if mtime < cutoff:
            csv_file.unlink()
            deleted_files.append(csv_file.name)
            logger.info("[Cleanup] raw 파일 삭제: %s (수정일: %s)", csv_file.name, mtime.date())
        else:
            kept_files.append(csv_file.name)

    logger.info("[Cleanup] raw 파일 — 삭제: %d개, 보존: %d개", len(deleted_files), len(kept_files))
    context["ti"].xcom_push(key="deleted_raw_count", value=len(deleted_files))
    return {"deleted": deleted_files, "kept_count": len(kept_files)}


def task_cleanup_processed_files(**context):
    """
    data/processed/ 디렉토리에서 PROCESSED_RETENTION_DAYS일 이상 된 파일 삭제.
    """
    from pathlib import Path
    from layer1_etl.config import PROC_DIR, logger

    cutoff = datetime.utcnow() - timedelta(days=PROCESSED_RETENTION_DAYS)
    deleted_files = []

    for f in Path(PROC_DIR).iterdir():
        if f.is_file():
            mtime = datetime.utcfromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                deleted_files.append(f.name)
                logger.info("[Cleanup] processed 파일 삭제: %s", f.name)

    logger.info("[Cleanup] processed 파일 삭제: %d개", len(deleted_files))
    context["ti"].xcom_push(key="deleted_processed_count", value=len(deleted_files))
    return {"deleted": deleted_files}


def task_cleanup_report(**context):
    """정리 결과 종합 리포트 생성 및 XCom push"""
    from layer1_etl.config import logger

    ti = context["ti"]
    archived  = ti.xcom_pull(task_ids="archive_expired_subsidies", key="archived_subsidies") or 0
    raw_del   = ti.xcom_pull(task_ids="cleanup_raw_files",         key="deleted_raw_count") or 0
    proc_del  = ti.xcom_pull(task_ids="cleanup_processed_files",   key="deleted_processed_count") or 0

    report = {
        "run_date":              context["ds"],
        "archived_subsidies":    archived,
        "deleted_raw_files":     raw_del,
        "deleted_processed_files": proc_del,
    }
    logger.info(
        "[Cleanup] 월간 정리 완료 — 만료공고: %d건, raw파일: %d개, processed파일: %d개",
        archived, raw_del, proc_del,
    )
    context["ti"].xcom_push(key="cleanup_report", value=report)
    return report


def on_failure_callback(context):
    from layer1_etl.config import logger
    task_id = context.get("task_instance").task_id
    logger.error("[Cleanup DAG] 태스크 실패: task=%s", task_id)


# ══════════════════════════════════════════════
# DAG 정의
# ══════════════════════════════════════════════

if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="factory_ai_navi_monthly_cleanup",
        default_args={**DEFAULT_ARGS, "on_failure_callback": on_failure_callback},
        description="Factory AI Navi — 월별 만료 공고 아카이브 및 파일 정리",
        schedule_interval="0 3 1 * *",   # 매월 1일 03:00
        start_date=days_ago(1),
        catchup=False,
        tags=["factory_ai_navi", "cleanup", "maintenance"],
    ) as dag:

        t_archive = PythonOperator(
            task_id="archive_expired_subsidies",
            python_callable=task_archive_expired_subsidies,
        )
        t_raw = PythonOperator(
            task_id="cleanup_raw_files",
            python_callable=task_cleanup_raw_files,
        )
        t_proc = PythonOperator(
            task_id="cleanup_processed_files",
            python_callable=task_cleanup_processed_files,
        )
        t_report = PythonOperator(
            task_id="cleanup_report",
            python_callable=task_cleanup_report,
        )

        # 아카이브·파일 정리 병렬 실행 → 리포트
        [t_archive, t_raw, t_proc] >> t_report
