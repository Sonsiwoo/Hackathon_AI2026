"""
[1단계] 최신 금융 뉴스 → LLM 기반 트렌드 키워드 TOP 5 추출

실행 순서:
  1) 네이버 뉴스 검색 API로 '특징주/주가' 관련 최신 기사 100개 수집
  2) Gemini에게 헤드라인을 보여주고 "요즘 가장 핫한 산업/테마 TOP 5" 추출 요청
  3) 결과를 src/llm_top5_trends.csv로 저장 (2단계 step2_map_companies.py가 이 파일을 읽어감)

실행: python step1_extract_trends.py  (src/ 폴더 안에서 실행하거나 python src/step1_extract_trends.py)
필요 환경변수(.env, 저장소 루트에 위치): NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, GEMINI_API_KEY
"""

import os
import sys

import pandas as pd

import config
from modules import trend_extractor

# 스크립트 자신의 위치(src/) 기준으로 CSV 경로를 고정한다.
# 이렇게 하면 어느 폴더(cwd)에서 실행하든 항상 src/llm_top5_trends.csv를 정확히 가리킨다.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TRENDS_CSV = os.path.join(_SCRIPT_DIR, 'llm_top5_trends.csv')

if __name__ == "__main__":
    # Windows 콘솔(cp949)에서 이모지 출력 시 UnicodeEncodeError가 나는 것을 방지
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # .env에 필요한 키가 하나라도 비어있으면 여기서 바로 에러 메시지 출력 후 종료
    config.validate(['NAVER_CLIENT_ID', 'NAVER_CLIENT_SECRET', 'GEMINI_API_KEY'])

    print("🚀 실시간 뉴스 기반 LLM 트렌드 분석 시작...")

    news_data = trend_extractor.fetch_financial_news(display=100)

    if news_data:
        print(f"✅ {len(news_data)}개의 금융 기사 수집 완료. LLM이 진짜 산업 테마를 솎아내는 중...")
        top_5_trends = trend_extractor.extract_trends_with_llm(news_data)

        print("\n🔥 [LLM이 도출한 현재 주식 시장 산업 트렌드 TOP 5] 🔥")
        for i, keyword in enumerate(top_5_trends, 1):
            print(f"{i}위: {keyword}")

        pd.DataFrame({'Keyword': top_5_trends}).to_csv(
            _TRENDS_CSV, index=False, encoding='utf-8-sig'
        )
    else:
        print("❌ 뉴스 수집 실패로 트렌드 분석을 중단합니다.")
