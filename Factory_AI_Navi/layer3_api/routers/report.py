"""
layer3_api/routers/report.py
==============================
GET /api/v1/report/{report_id}       — 진단 결과 JSON 조회
GET /api/v1/report/{report_id}/pdf   — PDF 레포트 다운로드
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from layer3_api.services.report_cache import report_cache
from layer3_api.services.report_generator import generate_pdf

router = APIRouter()


@router.get("/report/{report_id}")
def get_report(report_id: str):
    """캐시된 진단 결과 JSON 반환"""
    report = report_cache.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or expired")
    return report


@router.get("/report/{report_id}/pdf")
def download_pdf(report_id: str):
    """진단 결과 PDF 다운로드"""
    report = report_cache.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found or expired")

    pdf_bytes = generate_pdf(report)
    industry = report.get("industry_name", "report").replace(" ", "_")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="factory_ai_navi_{industry}.pdf"'},
    )
