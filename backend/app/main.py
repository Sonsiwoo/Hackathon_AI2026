"""
FastAPI 앱 진입점

실행: uvicorn app.main:app --reload --port 8000  (backend/ 폴더 안에서)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import predictions

app = FastAPI(title="주가 예측 API", description="HACKATHON 프로젝트의 Top5 종목 예측 결과 조회 API")

# 개발 단계에서는 프론트엔드(다른 포트)에서 자유롭게 호출 가능하도록 전체 허용.
# 실제 서버 배포 시에는 allow_origins를 프론트엔드 실제 도메인으로 좁히는 것을 권장.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(predictions.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "주가 예측 API 서버가 정상 동작 중입니다."}
