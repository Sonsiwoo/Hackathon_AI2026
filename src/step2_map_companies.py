"""
[2단계] 트렌드 키워드 → 실제 상장 종목(대장주) 매핑

실행 순서:
  1) 1단계가 만든 src/llm_top5_trends.csv에서 트렌드 키워드 5개를 읽음
  2) Gemini에게 "이 키워드들의 대장주 5개씩" 추천을 요청
  3) FinanceDataReader로 받은 실제 KRX 상장 종목 목록과 대조해 정확한 종목코드/시장구분을 붙임
  4) 결과를 src/step2_mapped_companies.csv로 저장
     (3단계 step3_predict_stock_price.py가 이 파일의 상위 5행을 예측 대상으로 사용함)

실행: python step2_map_companies.py  (1단계를 먼저 실행해서 llm_top5_trends.csv가 있어야 함)
필요 환경변수(.env, 저장소 루트에 위치): GEMINI_API_KEY
"""

import os
import sys

import pandas as pd

import config
from modules import company_mapper

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TRENDS_CSV = os.path.join(_SCRIPT_DIR, 'llm_top5_trends.csv')
_COMPANIES_CSV = os.path.join(_SCRIPT_DIR, 'step2_mapped_companies.csv')

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    config.validate(['GEMINI_API_KEY'])

    print("🚀 [Step 2] LLM 기반 종목 정밀 매핑 시작...")

    try:
        df_trends = pd.read_csv(_TRENDS_CSV, encoding='utf-8-sig')
        keywords = df_trends['Keyword'].tolist()
    except FileNotFoundError:
        print("❌ 에러: 'llm_top5_trends.csv' 파일이 없습니다. 1단계를 먼저 실행해주세요.")
        sys.exit(1)

    # 1. LLM에게 키워드별 대장주 후보 텍스트 받아오기 ("키워드,종목명" 형태의 줄들)
    llm_result_lines = company_mapper.request_llm_company_candidates(keywords)

    # 2. KRX 전체 상장 종목 목록 로드 (종목코드/시장구분을 찾기 위한 '정답지')
    print("📊 KRX 상장 종목 데이터와 교차 검증 중...")
    df_krx = company_mapper.load_krx_listing()

    # 3. LLM 응답을 파싱해서 실제 종목코드가 붙은 최종 리스트로 변환
    final_data = company_mapper.map_companies_to_krx(llm_result_lines, df_krx)

    if final_data:
        final_result_df = pd.DataFrame(final_data)
        print("\n🏆 [최종 매핑된 기업 리스트]")
        print(final_result_df.to_string(index=False))

        final_result_df.to_csv(_COMPANIES_CSV, index=False, encoding='utf-8-sig')
        print(f"\n✅ 매핑 완료! 총 {len(final_result_df)}개 기업이 완벽하게 정리되어 'step2_mapped_companies.csv'로 저장되었습니다.")
    else:
        print("⚠️ 매핑에 실패했습니다.")
