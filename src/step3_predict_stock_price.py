"""
[3단계] 5개 분야(키워드) 전체 종목의 다음 영업일 종가를 NHITS 모델로 예측

실행 순서:
  1) 2단계가 만든 src/step2_mapped_companies.csv에 있는 '모든 행'을 예측 대상으로 사용
     (반도체/인공지능/바이오/원전/우주항공 등 5개 분야에 속한 기업 전부 - 특정 분야만
      뽑지 않는다. 분야마다 매핑된 종목 수가 다를 수 있음 - KRX 상장 목록과 매칭 안 되는
      LLM 추천 종목은 2단계에서 이미 제외되었기 때문. 예: 4개만 매핑된 분야도 있을 수 있음)
  2) 오늘 기준 최근 1년치 OHLCV 데이터를 종목별로 조회
  3) 기술적 지표(약 130개)를 계산하고, 종목별로 LightGBM을 학습시켜 중요도 상위
     50개 지표를 선택 (종목마다 다른 지표가 선택될 수 있음)
  4) NHITS 모델을 종목별로 학습시켜 "다음 영업일 종가"를 예측
  5) 예측 결과(+ 사용된 핵심 지표 목록)를 predictions/stock_prediction_log.csv에 기록

  지표기반 프로젝트의 step3_technical.py와 달리, 09:00/12:00/16:00 시간대 구분 없이
  스크립트를 실행하는 시점 기준으로 항상 "다음 영업일 하루"만 예측한다.

  종목 하나가 실패해도(데이터 부족, 네트워크 오류 등) 나머지 종목은 계속 진행하며,
  실패한 종목은 건너뛴다는 메시지만 출력하고 최종 요약에서 제외된다.
  (전체 종목 수가 많아질수록 - 현재 약 20여 개 - 종목당 NHITS 학습 시간이 누적되어
   전체 실행 시간이 비례해서 늘어난다.)

실행: python step3_predict_stock_price.py  (2단계를 먼저 실행해서 step2_mapped_companies.csv가 있어야 함)
필요 환경변수(.env): 없음 (이 단계는 Gemini/Naver API를 쓰지 않음)
"""

import os
import sys

import pandas as pd

from modules import stock_price_fetcher, technical_indicators, nhits_predictor, prediction_logger

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_COMPANIES_CSV = os.path.join(_SCRIPT_DIR, 'step2_mapped_companies.csv')

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("🚀 [Step 3] 전체 분야 기업 NHITS 주가 예측 시작...")

    # 1. 읽기: step2 결과 CSV에 있는 모든 기업(모든 분야)을 예측 대상으로 사용
    #    dtype={'Code': str}로 읽지 않으면 pandas가 "005930"을 5930으로 잘못 해석해버림
    try:
        df_companies = pd.read_csv(
            _COMPANIES_CSV, dtype={'Code': str}, encoding='utf-8-sig'
        )
    except FileNotFoundError:
        print("❌ 에러: 'step2_mapped_companies.csv' 파일이 없습니다. 2단계를 먼저 실행해주세요.")
        sys.exit(1)

    df_companies['Code'] = df_companies['Code'].str.zfill(6)  # 앞자리 0 소실 방어(이중 안전장치)

    total = len(df_companies)
    keyword_counts = df_companies['Keyword'].value_counts()
    print(f"🏆 예측 대상: 총 {total}개 기업 ({len(keyword_counts)}개 분야)")
    for keyword, count in keyword_counts.items():
        print(f"   - {keyword}: {count}개")

    # 2. 조회 구간: 오늘 기준 최근 1년 (전체 종목이 같은 구간을 쓰므로 한 번만 계산)
    start_date, end_date = stock_price_fetcher.get_trailing_year_range()
    print(f"📅 데이터 조회 구간: {start_date} ~ {end_date}")

    results = []
    for i, row in enumerate(df_companies.itertuples(index=False), 1):
        print(f"\n[{i}/{total}] 📊 [{row.Keyword}] {row.Name}({row.Code}) 처리 중...")

        # 무거운 연산(가격 조회/지표 계산/NHITS 학습)을 시작하기 전에 먼저 확인:
        # 오늘 이미 이 종목을 예측해뒀다면 계산 자체를 하지 않고 바로 다음 종목으로 넘어간다.
        if prediction_logger.already_logged_today(row.Code):
            print(f"⏭ {row.Name}({row.Code}) 오늘 이미 예측 완료 - 계산 건너뜀")
            continue

        try:
            # 종목별로: 가격 조회 → 기술적 지표 계산 → NHITS 학습/예측 → 로그 저장
            ohlcv = stock_price_fetcher.fetch_ohlcv(row.Code, start_date, end_date)
            feat_df = technical_indicators.apply_all_technical_indicators(ohlcv)
            pred = nhits_predictor.predict_next_close(feat_df, unique_id=row.Code)

            prediction_logger.log_stock_prediction(
                keyword=row.Keyword, code=row.Code, name=row.Name, market=row.Market,
                target_date=pred['target_date'],
                current_close=pred['current_close'],
                predicted_close=pred['predicted_close'],
                top_features=pred['top_features'],
            )

            direction = '📈 상승' if pred['predicted_close'] > pred['current_close'] else '📉 하락'
            print(
                f"✅ {row.Name}: {pred['current_close']:,.0f} → {pred['predicted_close']:,.0f} "
                f"({direction}, {pred['target_date']})"
            )
            results.append({**row._asdict(), **pred})
        except Exception as e:
            # 한 종목의 실패가 나머지 종목 처리를 막지 않도록 여기서 잡고 다음 종목으로 넘어감
            print(f"⚠️ {row.Name}({row.Code}) 예측 실패, 건너뜁니다: {e}")
            continue

    print("\n==================================================")
    if results:
        print(f"🏆 [Step 3 완료] {len(results)}/{total}개 기업 예측 성공")
        print(pd.DataFrame(results).to_string(index=False))
    else:
        print("⚠️ 모든 기업에 대한 예측이 실패했습니다.")
    print("==================================================")
