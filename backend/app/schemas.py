"""
API 응답 형식을 정의하는 Pydantic 모델

FastAPI가 이 스키마에 맞춰 DB 조회 결과를 자동으로 JSON으로 변환하고,
동시에 /docs(Swagger) 문서에 응답 형식을 자동으로 보여준다.
"""

from pydantic import BaseModel


class PredictionOut(BaseModel):
    id: int
    run_datetime: str      # 예측을 실행한 시각 ('YYYY-MM-DD HH:MM')
    keyword: str            # 트렌드 키워드 (예: '반도체')
    code: str                # 종목코드
    name: str                # 종목명
    market: str              # 시장구분 (KOSPI/KOSDAQ)
    target_date: str         # 예측 대상 날짜 (다음 영업일)
    current_close: float     # 예측 시점 기준 실제 종가
    predicted_close: float   # 모델이 예측한 종가
    direction: str           # '상승' / '하락' / '보합'
    change: float            # predicted_close - current_close
    model: str                # 예측에 사용된 모델 태그
