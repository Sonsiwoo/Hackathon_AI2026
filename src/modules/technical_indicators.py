"""
[3단계용 모듈] 기술적 지표(Technical Indicator) 계산

pandas_ta_classic 라이브러리를 이용해 이동평균, RSI, MACD, 볼린저밴드 등
약 130개의 기술적 지표를 OHLCV 데이터프레임에 덧붙여준다.
(지표기반 프로젝트의 feature_engineering.py와 동일한 로직을 독립적으로 복제한 것으로,
 두 프로젝트가 서로 다른 저장소이기 때문에 import가 아니라 코드를 그대로 옮겨왔다.)
"""

import warnings

import pandas_ta_classic as ta

warnings.filterwarnings('ignore')


def apply_all_technical_indicators(df):
    """
    개별 종목 OHLCV 데이터프레임(df)을 입력받아, 약 130개의 기술적 지표(Feature)를
    안전하게 추가한 뒤 반환하는 모듈 함수입니다.

    Args:
        df: 'open','high','low','close','volume' 소문자 컬럼을 가진 DataFrame
            (stock_price_fetcher.fetch_ohlcv()의 반환값을 그대로 넣으면 됨)

    Returns:
        원본 컬럼 + 계산된 지표 컬럼들이 추가된 같은 DataFrame (in-place로 컬럼이 추가됨)
    """

    # pandas_ta_classic 호출 함수명 목록 (카테고리별로 정리)
    # 지표 하나당 df.ta.<이름>(append=True) 형태로 호출하면 결과 컬럼이 df에 자동으로 붙는다.
    indicator_list = [
        # 1. 추세 지표 (Trend & Overlap) - 가격의 방향성/추세를 보여줌
        'sma', 'ema', 'wma', 'dema', 'tema', 'hma', 'rma', 'zlma', 'alma',
        'fwma', 'pwma', 'linreg', 'midpoint', 'midprice', 'hl2', 'hlc3', 'ohlc4',
        'macd', 'adx', 'aroon', 'psar', 'qstick', 'vortex',

        # 2. 모멘텀 지표 (Momentum) - 가격 변화의 속도/힘을 보여줌
        'rsi', 'stoch', 'stochrsi', 'cci', 'willr', 'mom', 'roc', 'cmo',
        'mfi', 'tsi', 'ppo', 'apo', 'bop', 'cgo', 'kdj', 'rvgi', 'stc', 'uo',

        # 3. 변동성 지표 (Volatility) - 가격이 얼마나 출렁이는지를 보여줌
        'bbands', 'atr', 'kc', 'natr', 'true_range', 'massi', 'pdist', 'ui', 'rvi',

        # 4. 거래량 지표 (Volume) - 거래량 기반 매수/매도 압력을 보여줌
        'ad', 'obv', 'cmf', 'efi', 'pvt', 'nvi', 'pvi', 'vwap', 'adosc',

        # 5. 통계 및 기타 지표 (Statistics) - 가격 분포의 통계적 특성을 보여줌
        'zscore', 'variance', 'skew', 'kurtosis', 'mad', 'median', 'quantile', 'entropy', 'cg'
    ]

    success_count = 0
    fail_list = []

    print("\n[모듈 작동] 130여 개 기술적 지표 생성을 시작합니다...")

    # 지표를 하나씩 순회하며 동적으로 호출.
    # 일부 지표는 데이터가 너무 적거나(예: 1년치만 있는데 200일 이동평균 등) 특정 조건에서
    # 계산이 실패할 수 있으므로, 하나 실패해도 전체가 멈추지 않도록 개별적으로 try/except 처리.
    for ind_name in indicator_list:
        try:
            getattr(df.ta, ind_name)(append=True)
            success_count += 1
        except Exception:
            fail_list.append(ind_name)

    print(f"[모듈 완료] {success_count}종류의 지표 생성 성공!")
    print(f"           -> 생성된 최종 입력 변수(Feature) 갯수: 총 {len(df.columns)}개")

    if fail_list:
        print(f"⚠️ 데이터 부족 등으로 생략된 지표: {fail_list}")

    return df
