"""
[3단계용 모듈] 예측 결과를 CSV 로그 파일에 기록

종목별 예측 결과(현재가/예측가/방향/사용된 핵심 지표 등)를 predictions/stock_prediction_log.csv에
한 줄씩 누적 저장한다. (지표기반 프로젝트의 predictions/prediction_log.csv와 같은 위치 관례)
같은 날 같은 종목을 이미 예측해 기록해뒀다면 중복으로 또 쌓지 않도록 방지 로직도 포함한다.

이 CSV는 app/APP.py(Streamlit 대시보드)가 직접 읽어가는 데이터 소스이기도 하다.
"""

import os
from datetime import datetime

import pandas as pd
import pytz

KST = pytz.timezone('Asia/Seoul')

# 이 파일 경로: HACKATHON/src/modules/prediction_logger.py
# 여기서 3단계 위(modules -> src -> HACKATHON)로 올라가면 저장소 루트가 된다.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PREDICTIONS_DIR = os.path.join(_REPO_ROOT, 'predictions')
_DEFAULT_LOG_PATH = os.path.join(_PREDICTIONS_DIR, 'stock_prediction_log.csv')


def already_logged_today(code, model='NHITS_stock', log_path=None):
    """
    오늘 이 종목(code)/모델(model) 조합으로 이미 예측을 기록했는지 미리 확인한다.

    step3_predict_stock_price.py에서 이 함수를 데이터 조회/지표 계산/NHITS 학습을
    시작하기 '전'에 호출해서, 이미 오늘 처리된 종목이면 무거운 연산 자체를 건너뛸 수 있게 한다.
    (log_stock_prediction() 안에도 같은 체크가 있지만, 그건 학습이 다 끝난 '뒤'에야
     저장 단계에서 걸러내므로 시간 낭비가 있음 - 이 함수는 그 낭비를 막기 위한 사전 체크용)

    Args:
        code: 종목코드
        model: 예측 모델 태그 (기본값 'NHITS_stock')
        log_path: CSV 로그 파일 경로 (지정 안 하면 predictions/stock_prediction_log.csv 사용)

    Returns:
        True면 오늘 이미 기록됨(건너뛰어도 됨), False면 아직 기록 안 됨(계속 진행해야 함)
    """
    log_path = log_path or _DEFAULT_LOG_PATH
    if not os.path.exists(log_path):
        return False

    today_str = datetime.now(KST).strftime('%Y-%m-%d')
    try:
        existing = pd.read_csv(log_path, dtype={'code': str})
        already = existing[
            (existing['run_datetime'].str.startswith(today_str)) &
            (existing['code'] == str(code)) &
            (existing['model'] == model)
        ]
        return not already.empty
    except Exception:
        # 로그 파일을 못 읽으면 "아직 기록 안 됨"으로 간주하고 정상적으로 계속 진행시킨다.
        return False


def log_stock_prediction(keyword, code, name, market, target_date,
                          current_close, predicted_close,
                          model='NHITS_stock', log_path=None, top_features=None):
    """
    한 종목의 예측 결과를 predictions/stock_prediction_log.csv에 한 줄 추가(append)한다.

    Args:
        keyword: 이 종목이 속한 트렌드 키워드 (예: '반도체')
        code, name, market: 종목코드/종목명/시장구분
        target_date: 예측 대상 날짜 (다음 영업일)
        current_close: 예측 시점 기준 최근 실제 종가
        predicted_close: 모델이 예측한 종가
        model: 어떤 모델로 만든 예측인지 표시하는 태그 (기본값 'NHITS_stock').
               지표기반 프로젝트의 prediction_log.csv에 쓰이는 'NHITS'/'NHITS_technical'
               태그와 헷갈리지 않도록 구분되는 이름을 사용한다.
        log_path: CSV 로그 파일 경로 (지정 안 하면 predictions/stock_prediction_log.csv 사용)
        top_features: 이 예측에 실제로 사용된 핵심 지표 이름 리스트 (nhits_predictor.
                      predict_next_close()가 반환하는 'top_features'를 그대로 넘기면 됨).
                      나중에 "이 예측이 왜 이렇게 나왔는지" 확인하거나, 다시 추출할 필요 없이
                      재사용할 수 있도록 CSV에 같이 저장해둔다. None이면 빈 값으로 저장.

    Returns:
        없음. 파일에 쓰거나, 이미 오늘 같은 종목을 기록했다면 그냥 스킵하고 메시지만 출력한다.
    """
    log_path = log_path or _DEFAULT_LOG_PATH

    # --- 중복 실행 방지 가드 ---
    # 스크립트를 하루에 여러 번 돌려도 같은 (오늘 날짜, 종목코드, 모델) 조합이면
    # 이미 기록된 것으로 보고 새로 쌓지 않는다. (already_logged_today와 동일 로직 재사용)
    if already_logged_today(code, model, log_path):
        print(f"⏭ [{model} / {name}] 오늘 예측 이미 저장됨 - 스킵")
        return

    if predicted_close > current_close:
        direction = '상승'
    elif predicted_close < current_close:
        direction = '하락'
    else:
        direction = '보합'

    result = {
        'run_datetime': datetime.now(KST).strftime('%Y-%m-%d %H:%M'),
        'keyword': keyword,
        'code': str(code),
        'name': name,
        'market': market,
        'target_date': target_date,
        'current_close': round(current_close, 2),
        'predicted_close': round(predicted_close, 2),
        'direction': direction,
        'change': round(predicted_close - current_close, 2),
        'model': model,
        # 콤마 대신 '|'로 구분 - CSV 컬럼 구분자(,)와 겹치지 않아 따옴표 처리 없이도 안전하게 저장됨
        'top_features': '|'.join(top_features) if top_features else '',
    }

    # predictions/ 폴더가 아직 없으면 만들어준다 (최초 실행 대비)
    os.makedirs(_PREDICTIONS_DIR, exist_ok=True)

    # mode='a' : 기존 파일에 이어 붙이기 (덮어쓰지 않음)
    # header= : 파일이 아직 없을 때만 헤더(컬럼명 줄)를 새로 씀
    # encoding='utf-8-sig' : 엑셀에서 한글이 깨지지 않도록 BOM 포함 UTF-8로 저장 (기존 프로젝트 관례)
    pd.DataFrame([result]).to_csv(
        log_path, mode='a', header=not os.path.exists(log_path),
        index=False, encoding='utf-8-sig'
    )

    print(f"✅ [{model}] {name}({code}) 예측 결과 저장 완료 (target={target_date}, {direction})")
