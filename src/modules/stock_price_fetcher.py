"""
[3단계용 모듈] 개별 종목의 주가(OHLCV) 데이터 조회

FinanceDataReader(FDR)를 이용해 특정 종목코드의 최근 1년치
시가/고가/저가/종가/거래량(OHLCV)을 가져오는 역할만 담당한다.
"""

from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pytz

# 한국 시간대 (뉴욕/UTC 서버에서 돌려도 "오늘" 기준이 한국 기준이 되도록 고정)
KST = pytz.timezone('Asia/Seoul')


def get_trailing_year_range(days=365):
    """
    오늘(KST 기준)로부터 최근 `days`일간의 날짜 범위를 계산한다.
    기존 지표기반 프로젝트는 2014년~현재 전체 히스토리를 썼지만,
    이 파이프라인은 "최근 1년"만 학습에 사용하도록 의도적으로 범위를 좁혔다.

    Args:
        days: 오늘 기준 며칠 전까지 볼지 (기본 365일 = 1년)

    Returns:
        (start_date, end_date) 문자열 튜플, 'YYYY-MM-DD' 형식
    """
    end = datetime.now(KST)
    start = end - timedelta(days=days)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


def fetch_ohlcv(code, start_date, end_date):
    """
    종목코드로 지정한 기간의 OHLCV(시가/고가/저가/종가/거래량) 데이터를 가져온다.

    Args:
        code: 6자리 종목코드 (예: '005930'). 앞자리 0이 날아간 채로 들어와도
              zfill(6)으로 다시 채워주므로 int/str 어느 쪽이 와도 안전하다.
        start_date, end_date: 'YYYY-MM-DD' 형식의 조회 시작/종료일

    Returns:
        컬럼명이 소문자(open/high/low/close/volume)로 정리된 DataFrame.
        (기술적 지표 계산 모듈이 소문자 컬럼명을 기대하기 때문에 여기서 미리 맞춰둔다)

    Raises:
        ValueError: 조회 결과가 비어있을 때 (상장폐지, 잘못된 코드, 네트워크 오류 등)
    """
    # pandas가 "005930"을 숫자로 잘못 해석해 5930으로 바꿔버리는 경우가 있어 방어적으로 재보정
    code = str(code).zfill(6)

    df = fdr.DataReader(code, start_date, end_date)
    if df.empty:
        raise ValueError(f"{code}: FDR에서 OHLCV 데이터를 가져오지 못했습니다.")

    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Volume': 'volume'
    })
    df = df.dropna(subset=['close'])
    df = df.sort_index()
    return df
