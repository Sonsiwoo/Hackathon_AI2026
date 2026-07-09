"""
[3단계용 모듈] NHITS 딥러닝 모델로 "다음 영업일 종가" 예측

NHITS(Neural Hierarchical Interpolation for Time Series)는 시계열 예측용
딥러닝 모델이다. neuralforecast 라이브러리를 사용하며, 지표기반 프로젝트의
step3_technical.py 일별(daily) 예측 로직과 동일한 하이퍼파라미터를 그대로 재사용한다.

종목마다 실제로 예측력이 높은 지표는 다르므로, 모든 종목에 항상 같은 지표 50개를
쓰지 않고 종목별로 LightGBM을 한 번 학습시켜 중요도를 매긴 뒤 상위 50개만 골라 쓴다
(select_feature_columns). 이 랭킹은 predict_next_close()가 호출될 때마다(=파이프라인을
실행할 때마다, 보통 하루 한 번) 그 시점의 최신 데이터로 새로 계산되므로, 트렌드/기업
구성이 바뀌거나 시장 상황이 바뀌면 핵심 지표도 자동으로 함께 바뀐다.

이 파일은 반드시 아래 순서로 동작해야 한다:
  1) pytorch_lightning 버전 호환성 패치(shim) 적용
  2) 그 다음에 neuralforecast를 import
(순서가 바뀌면 neuralforecast 내부에서 pytorch_lightning의 옛날 API를 찾다가 죽는다.)
"""

import logging
import warnings

import numpy as np
import pandas as pd
import pytorch_lightning as pl
from lightgbm import LGBMRegressor

# --- pytorch_lightning 호환성 패치 (shim) ---
# 일부 pytorch_lightning 최신 버전은 pl.utilities.distributed 모듈을 없애버렸는데,
# neuralforecast 내부 코드(experiments/utils.py)가 여전히
# pl.utilities.distributed.log.setLevel(...) 형태로 접근을 시도한다.
# 그래서 neuralforecast를 import하기 '전에' 가짜(mock) distributed.log를 미리 만들어둔다.
if not hasattr(pl.utilities, 'distributed'):
    class MockDistributed:
        log = logging.getLogger(__name__)
    pl.utilities.distributed = MockDistributed
elif not hasattr(pl.utilities.distributed, 'log'):
    pl.utilities.distributed.log = logging.getLogger(__name__)

warnings.filterwarnings('ignore')

# 반드시 위 shim 적용 이후에 import해야 함
from neuralforecast import NeuralForecast
from neuralforecast.models import NHITS


def select_feature_columns(df, max_features=50):
    """
    기술적 지표가 잔뜩 붙은 데이터프레임에서, 이 종목에 실제로 예측력이 높은
    피처 컬럼을 LightGBM 중요도 기준 상위 max_features개 고른다.

    이전에는 지표 컬럼을 등장 순서대로 그냥 앞에서부터 50개 잘라 썼는데, 그러면
    지표 계산 순서가 고정돼 있어서(SMA, EMA, ... 항상 같은 순서) 어떤 종목이든
    "앞쪽 50개"가 늘 똑같이 뽑히는 문제가 있었다. 지금은 종목별 데이터로 가벼운
    LightGBM 회귀 모델을 한 번 학습시켜, "다음 시점 종가를 맞히는 데 실제로 얼마나
    기여했는지"로 지표 순위를 매긴다. NHITS를 학습시키기 직전에 매번 새로 계산되므로
    종목이 바뀌거나 시장 상황(=데이터)이 바뀌면 선택되는 지표도 함께 바뀐다.

    Args:
        df: unique_id/ds/y 및 기술적 지표 컬럼들을 포함한 DataFrame
        max_features: 최대로 사용할 피처 개수 (기본 50개)

    Returns:
        중요도 내림차순으로 정렬된 피처 컬럼명 리스트 (최대 max_features개)
    """
    # unique_id(종목 식별자), ds(날짜), y(정답값=종가)는 피처가 아니라 메타/타깃 컬럼이므로 제외
    exclude = {'unique_id', 'ds', 'y'}
    candidate_cols = [
        c for c in df.columns
        if c not in exclude and df[c].dtype.kind in ('f', 'i')  # 실수(f)/정수(i) 타입만
    ]

    # 중요도 계산용으로만 쓰는 임시 정제(실제 학습에 쓰일 frame과는 별개) -
    # inf를 NaN으로 바꾸고 채운 뒤, 그래도 남은 결측 행은 제거
    work_df = df[candidate_cols + ['y']].replace([np.inf, -np.inf], np.nan).ffill().bfill().dropna()

    # 데이터가 너무 적으면(예: 상장 초기 종목) 중요도 랭킹 자체가 불안정하므로,
    # 안전하게 예전 방식(등장 순서대로 앞에서부터)으로 폴백한다.
    if len(work_df) < 30:
        return candidate_cols[:max_features]

    # "오늘 지표들로 다음 시점 종가를 맞히는" 문제로 정의 - NHITS의 h=1 목표와 동일한 취지
    X = work_df[candidate_cols].iloc[:-1]
    y_next = work_df['y'].shift(-1).iloc[:-1]

    model = LGBMRegressor(n_estimators=200, learning_rate=0.05, random_state=42, verbose=-1)
    model.fit(X, y_next)

    ranked = sorted(zip(candidate_cols, model.feature_importances_), key=lambda pair: pair[1], reverse=True)
    return [name for name, _ in ranked[:max_features]]


def prepare_training_frame(df, unique_id):
    """
    OHLCV+지표 DataFrame을 neuralforecast가 요구하는 표준 형식으로 변환한다.
    neuralforecast는 반드시 'unique_id', 'ds'(날짜), 'y'(예측 대상값) 컬럼이 있어야 동작한다.

    Args:
        df: 날짜가 인덱스로 되어 있고 'close' 컬럼을 포함한 DataFrame
        unique_id: 이 시계열을 구분할 식별자 (여기서는 종목코드를 사용)

    Returns:
        'unique_id', 'ds', 'y' + 원본 지표 컬럼들을 포함한 DataFrame
        (피처 선택은 아직 안 한 상태 - 그건 predict_next_close에서 처리)
    """
    frame = df.reset_index()  # 날짜 인덱스를 일반 컬럼으로 꺼냄

    # FDR 데이터의 날짜 인덱스 컬럼명이 보통 'Date'이지만, 혹시 다른 이름이어도
    # 방어적으로 첫 번째 컬럼을 'ds'로 취급한다.
    if 'Date' in frame.columns:
        frame = frame.rename(columns={'Date': 'ds'})
    else:
        frame = frame.rename(columns={frame.columns[0]: 'ds'})

    frame = frame.rename(columns={'close': 'y'})  # neuralforecast는 예측 대상 컬럼명이 'y'여야 함
    frame['ds'] = pd.to_datetime(frame['ds'])
    frame['unique_id'] = unique_id
    return frame


def predict_next_close(df, unique_id, input_size=30, h=1, max_steps=200):
    """
    한 종목의 데이터로 NHITS 모델을 학습시키고, 다음 영업일 종가를 예측한다.

    Args:
        df: technical_indicators.apply_all_technical_indicators()를 거친 OHLCV+지표 DataFrame
        unique_id: 종목을 구분할 식별자 (종목코드 문자열)
        input_size: 예측에 참고할 과거 데이터 길이 (기본 30일치)
        h: 몇 스텝 앞을 예측할지 (horizon). 1이면 "다음 하루"만 예측
        max_steps: 모델 학습 반복 횟수 상한

    Returns:
        dict: {
            'target_date': 예측 대상 날짜(다음 영업일, 'YYYY-MM-DD'),
            'current_close': 가장 최근 실제 종가,
            'predicted_close': 모델이 예측한 다음 영업일 종가,
            'feature_count': 실제로 학습에 사용된 피처 개수,
            'rows_used': 학습에 사용된 유효 데이터 행 수,
            'top_features': LightGBM 중요도 기준으로 선택된 피처 이름 리스트
                            (나중에 "이 예측이 왜 이렇게 나왔는지" 확인하거나,
                             재계산 없이 재사용하고 싶을 때를 위해 그대로 반환)
        }

    Raises:
        ValueError: 정제 후 남은 데이터가 input_size + h보다 적을 때
                    (최근 상장 종목이거나 결측치가 많아 학습 불가능한 경우)
    """
    frame = prepare_training_frame(df, unique_id)

    feature_cols = select_feature_columns(frame, max_features=50)
    # ⚠️ 순서 중요: 피처를 먼저 "선택(slice)"한 뒤에 결측치를 처리해야 한다.
    # 만약 반대로 하면, 우리가 쓰지도 않을 나머지 지표 컬럼에 낀 NaN 때문에
    # dropna()가 전체 행을 통째로 날려버릴 수 있다.
    frame = frame[['unique_id', 'ds', 'y'] + feature_cols]

    # 일부 지표(예: 거래량이 0인 날의 비율 계산 등)는 inf/-inf를 만들어낼 수 있어
    # 이를 NaN으로 바꾼 뒤 앞/뒤 값으로 채우고, 그래도 남은 결측 행은 제거한다.
    frame = frame.replace([np.inf, -np.inf], np.nan).ffill().bfill()
    frame = frame.dropna()

    if len(frame) < input_size + h:
        raise ValueError(
            f"{unique_id}: 학습 데이터 부족 ({len(frame)}행, 최소 {input_size + h}행 필요)"
        )

    # NHITS 하이퍼파라미터
    #   h            : 예측 스텝 수 (1 = 다음 영업일 하루만)
    #   input_size   : 모델이 한 번에 참고하는 과거 시점 길이
    #   hist_exog_list: 과거값을 그대로 참고할 외생 변수(피처) 목록
    #   max_steps    : 학습 반복 횟수 상한
    #   scaler_type  : 입력 스케일링 방식 ('robust'는 이상치에 덜 민감함)
    model = NHITS(
        h=h,
        input_size=input_size,
        hist_exog_list=feature_cols,
        max_steps=max_steps,
        scaler_type='robust'
    )
    # freq='B'는 영업일(Business day) 단위 시계열이라는 뜻 (주말 제외)
    nf = NeuralForecast(models=[model], freq='B')
    nf.fit(df=frame)
    forecast = nf.predict()

    current_close = float(frame['y'].iloc[-1])          # 가장 최근 실제 종가
    predicted_close = float(forecast['NHITS'].iloc[-1])  # 모델이 예측한 다음 영업일 종가

    next_ds = forecast['ds'].iloc[-1]
    target_date = next_ds.strftime('%Y-%m-%d') if hasattr(next_ds, 'strftime') else str(next_ds)

    return {
        'target_date': target_date,
        'current_close': current_close,
        'predicted_close': predicted_close,
        'feature_count': len(feature_cols),
        'rows_used': len(frame),
        'top_features': feature_cols,
    }
