#!/bin/bash
# Blogdex 전체 서비스 시작
# 사용법: ./start.sh 또는 blogdex

echo "================================"
echo "  Blogdex 서비스 시작"
echo "================================"

# 로컬 API 서버 (백그라운드)
echo ""
echo "[1] 로컬 API 서버 시작 (포트 5001)..."
cd /Users/twinssn/Projects/blogdex/cli
source venv/bin/activate
python local_api.py &
LOCAL_PID=$!
echo "  PID: $LOCAL_PID"

# 잠시 대기
sleep 2

# 대시보드 (포그라운드)
echo ""
echo "[2] 대시보드 시작 (포트 5173)..."
cd /Users/twinssn/Projects/blogdex/dashboard
npm run dev &
DASH_PID=$!
echo "  PID: $DASH_PID"

echo ""
echo "================================"
echo "  로컬 API:  http://localhost:5001"
echo "  대시보드:  http://localhost:5173"
echo "================================"
echo ""
echo "종료: Ctrl+C"

# Ctrl+C로 둘 다 종료
trap "echo ''; echo '서비스 종료 중...'; kill $LOCAL_PID $DASH_PID 2>/dev/null; exit" INT TERM

# 대기
wait
