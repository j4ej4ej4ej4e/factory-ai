"""
layer3_api/main.py
===================
Factory AI Navi — FastAPI 앱 엔트리포인트

실행 방법:
  uvicorn layer3_api.main:app --host 0.0.0.0 --port 8000 --reload

Swagger UI: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from layer3_api.routers import diagnose, subsidies, report

app = FastAPI(
    title="Factory AI Navi API",
    version="1.0.0",
    description="중소 제조기업 AI 공정 진단 & 정부지원 매칭 플랫폼",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnose.router, prefix="/api/v1", tags=["진단"])
app.include_router(subsidies.router, prefix="/api/v1", tags=["지원사업 / ROI"])
app.include_router(report.router, prefix="/api/v1", tags=["레포트"])


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "service": "factory-ai-navi"}
