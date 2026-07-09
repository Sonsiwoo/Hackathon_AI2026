"""
[4단계] DART 공시 수집 → Gemini 요약 → 웹사이트용 CSV 저장

실행 순서:
  1) src/step2_mapped_companies.csv에 있는 모든 종목명을 대상으로
  2) 종목별 최근 14일 DART 공시를 최대 3건씩 조회
  3) 공시마다 Gemini에게 "투자자 관점 요약/감성/인사이트"를 뽑게 함
  4) 결과를 src/llm_dart_news_summary.csv로 저장
     (app/APP.py의 "실시간 공시 브리핑" 탭이 이 파일을 읽어 화면에 보여줌)

  이 스크립트는 매번 실행될 때 CSV를 통째로 새로 씀(append 아님) - 공시는
  "최근 14일"이라는 상대적 기준으로 뽑히므로, 지난 결과에 이어붙이기보다
  매번 최신 스냅샷으로 덮어쓰는 게 맞다.

실행: python step4_summarize_disclosures.py  (2단계를 먼저 실행해서 step2_mapped_companies.csv가 있어야 함)
필요 환경변수(.env): DART_API_KEY, GEMINI_API_KEY
"""

import os
import sys

import pandas as pd

import config
from modules import disclosure_summarizer

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_COMPANIES_CSV = os.path.join(_SCRIPT_DIR, 'step2_mapped_companies.csv')
_SAVE_PATH = os.path.join(_SCRIPT_DIR, 'llm_dart_news_summary.csv')

if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    config.validate(['DART_API_KEY', 'GEMINI_API_KEY'])

    print("🚀 실시간 DART & Gemini 분석 파이프라인 시작...")

    try:
        df_mapping = pd.read_csv(_COMPANIES_CSV, encoding='utf-8-sig')
        target_companies = df_mapping['Name'].unique().tolist()
    except FileNotFoundError:
        print("❌ 에러: 'step2_mapped_companies.csv' 파일이 없습니다. 2단계를 먼저 실행해주세요.")
        sys.exit(1)

    final_results = []

    for company in target_companies:
        print(f"📡 {company} DART 공시 데이터 수집 중...")
        raw_items = disclosure_summarizer.fetch_dart_filings(company, days=14)

        if not raw_items:
            print(f"  - 최근 14일간 {company}의 주요 공시가 없습니다.")
            continue

        for item in raw_items:
            print(f"  🧠 Gemini 분석 중: {item['title']}...")
            llm_result = disclosure_summarizer.analyze_with_gemini(company, item)

            if llm_result:
                final_results.append({
                    "name": company,
                    "date": item["date"],
                    "title": item["title"],
                    "summary": llm_result.get("summary", "요약 정보 없음"),
                    "sentiment": llm_result.get("sentiment", "중립"),
                    "source": item["source"],
                    "key_takeaways": llm_result.get("key_takeaways", "인사이트 준비 중"),
                })
                print(f"    -> 분석 성공 ({llm_result.get('sentiment')})")

    if final_results:
        df_summary = pd.DataFrame(final_results)
        df_summary.to_csv(_SAVE_PATH, index=False, encoding='utf-8-sig')
        print(f"\n✅ 파이프라인 완료! 데이터가 성공적으로 저장되었습니다: {_SAVE_PATH}")
    else:
        print("\n⚠️ 수집되었으나 분석에 성공한 공시 데이터가 없습니다.")
