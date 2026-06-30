#!/bin/bash
# Factory AI Navi — 개발 서버 시작 스크립트
# 사용법: bash start.sh

set -e

echo "=========================================="
echo "  Factory AI Navi — 개발 서버 시작"
echo "=========================================="

# .env 파일 확인
if [ ! -f .env ]; then
  echo "[!] .env 파일이 없습니다. .env.example을 복사해 API 키를 설정하세요."
  echo "    cp .env.example .env && vi .env"
  exit 1
fi

# DB 시드 확인
if [ ! -f dev_local.db ]; then
  echo "[1/3] DB 초기 데이터 생성 중..."
  python scripts/seed_db.py
else
  echo "[1/3] DB 이미 존재함 (dev_local.db)"
fi

# FastAPI 백엔드 (백그라운드)
echo "[2/3] FastAPI 백엔드 시작 (포트 8000)..."
uvicorn layer3_api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "      PID: $BACKEND_PID"

sleep 2

# Next.js 프론트엔드 (백그라운드)
echo "[3/3] Next.js 프론트엔드 시작 (포트 3000)..."
cd layer3_frontend
if [ ! -d node_modules ]; then
  echo "      npm 패키지 설치 중..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=========================================="
echo "  서비스 준비 완료!"
echo "  프론트엔드: http://localhost:3000"
echo "  API Swagger: http://localhost:8000/docs"
echo ""
echo "  종료: Ctrl+C"
echo "=========================================="

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
