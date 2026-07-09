"""
예측 데이터 조회 API 라우터

프론트엔드(React)가 실제로 호출하는 엔드포인트들이 여기 정의되어 있다.
DB에 쓰는 코드는 없음 - 쓰기는 항상 src/step3_predict_stock_price.py(+prediction_logger.py) 쪽에서만 하고,
이 백엔드는 조회(읽기) 전용으로만 동작한다 (역할을 명확히 분리).
"""

from fastapi import APIRouter, HTTPException

from app.database import get_connection
from app.schemas import PredictionOut

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/latest", response_model=list[PredictionOut])
def get_latest_predictions():
    """
    종목별로 가장 최근에 저장된 예측 1건씩만 뽑아 반환한다.
    대시보드 메인 화면(Top 5 카드 목록)에서 사용.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM predictions p
            WHERE p.id = (
                SELECT id FROM predictions p2
                WHERE p2.code = p.code
                ORDER BY run_datetime DESC, id DESC
                LIMIT 1
            )
            ORDER BY p.code
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


@router.get("/{code}", response_model=list[PredictionOut])
def get_prediction_history(code: str):
    """
    특정 종목코드의 전체 예측 히스토리를 최신순으로 반환한다.
    종목 상세 페이지에서 시간에 따른 예측 추이를 보여줄 때 사용.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM predictions WHERE code = ? ORDER BY run_datetime DESC, id DESC",
            (code,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail=f"종목 코드 {code}에 대한 예측 데이터가 없습니다.")
    return [dict(row) for row in rows]
