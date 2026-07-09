"""
[4단계용 모듈] DART 공시 수집 + Gemini 기반 요약

흐름: 종목명으로 최근 DART(전자공시시스템) 공시를 최대 3건 가져온 뒤,
      Gemini에게 "이 공시가 투자자에게 어떤 의미인지" 2~3문장으로 요약시킨다.
결과물: {summary, sentiment, key_takeaways} 형태의 분석 결과
"""

import json
import time
from datetime import datetime, timedelta

import pandas as pd
import pytz

from modules import dart_client, gemini_client

KST = pytz.timezone('Asia/Seoul')

# Gemini 무료 티어는 gemini-flash-lite 계열 기준 "분당 15회" 요청 제한이 있다.
# 1.5초 간격(분당 최대 40회)으로는 이 한도를 쉽게 넘겨서 429가 자주 발생했었음 -
# 4.5초 간격(분당 최대 13회)으로 늘려 애초에 한도 안쪽에서 움직이도록 한다.
_GEMINI_REQUEST_DELAY_SEC = 4.5


def fetch_dart_filings(company_name, days=14):
    """
    종목명으로 최근 `days`일간의 DART 공시를 최대 3건 가져온다.

    Args:
        company_name: 종목명 (예: '삼성전자'). DART는 종목코드가 아니라 회사명으로 검색한다.
        days: 오늘로부터 며칠 전까지 조회할지 (기본 14일)

    Returns:
        {'date', 'title', 'source', 'content'} 딕셔너리들의 리스트 (최신순, 최대 3건).
        공시가 없거나 API 호출이 실패하면 빈 리스트를 반환한다.
    """
    end_date = datetime.now(KST)
    start_date = end_date - timedelta(days=days)

    try:
        filings = dart_client.get_client().list(
            company_name,
            start=start_date.strftime('%Y%m%d'),
            end=end_date.strftime('%Y%m%d'),
        )

        if filings is None or filings.empty:
            return []

        raw_data_list = []
        for _, row in filings.head(3).iterrows():
            date_str = pd.to_datetime(row['rcept_dt']).strftime("%Y-%m-%d")
            raw_data_list.append({
                "date": date_str,
                "title": row['report_nm'],
                "source": "DART",
                "content": (
                    f"공시 제출인: {row['flr_nm']}, 접수번호: {row['rcept_no']} - "
                    f"이 공시는 {company_name}의 '{row['report_nm']}'에 관한 주요 경영 사항입니다."
                ),
            })
        return raw_data_list

    except Exception as e:
        print(f"[{company_name}] DART API 호출 중 오류 발생: {e}")
        return []


def analyze_with_gemini(company_name, raw_data):
    """
    공시 하나를 Gemini에게 보내 요약/감성/투자 인사이트를 뽑아낸다.

    Args:
        company_name: 종목명
        raw_data: fetch_dart_filings()가 반환한 딕셔너리 하나 (title/source/content 포함)

    Returns:
        {'summary', 'sentiment', 'key_takeaways'} 딕셔너리. 실패하면 None.
    """
    prompt = f"""
    You are a top quant analyst. Analyze this Korean public disclosure and output JSON.

    [Company]
    {company_name}

    [Data]
    Title: {raw_data['title']}
    Source: {raw_data['source']}
    Context: {raw_data['content']}

    [Required Output Format]
    Ensure your response is valid JSON matching this exact structure, with no markdown code block wrapping:
    {{
        "summary": "공시 제목과 맥락을 바탕으로 이 공시가 기업에 의미하는 바를 2문장으로 요약하세요. 한글로 존댓말을 쓰세요.",
        "sentiment": "긍정, 부정, 중립 중 하나만 선택",
        "key_takeaways": "투자자가 주목해야 할 포인트나 트레이딩 인사이트를 1문장으로 제시하세요. 한글로 존댓말을 쓰세요."
    }}
    """

    try:
        # 호출 전 안정적인 커넥션을 위한 미세 휴식 + rate limit 방지
        time.sleep(_GEMINI_REQUEST_DELAY_SEC)

        response = gemini_client.generate_content_with_retry(
            model='gemini-flash-lite-latest',
            contents=prompt,
        )

        # Gemini가 응답을 ```json ... ``` 코드블록으로 감싸는 경우가 있어 방어적으로 벗겨냄
        text_response = response.text.strip()
        if text_response.startswith("```json"):
            text_response = text_response.split("```json")[1].split("```")[0].strip()
        elif text_response.startswith("```"):
            text_response = text_response.split("```")[1].split("```")[0].strip()

        return json.loads(text_response)

    except Exception as e:
        print(f"  ❌ [{company_name}] Gemini API 오류/파싱 실패: {e}")
        return None
