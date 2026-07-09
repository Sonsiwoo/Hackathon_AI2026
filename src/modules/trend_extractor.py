"""
[1단계용 모듈] 뉴스 기반 트렌드 키워드 추출

흐름: 네이버 뉴스 검색 API로 최신 금융 뉴스 헤드라인을 모은 뒤,
      Gemini(LLM)에게 "요즘 가장 핫한 산업/테마 TOP 5"를 뽑아달라고 요청한다.
결과물: 트렌드 키워드 리스트 (예: ['반도체', '인공지능', '바이오', '원전', '우주항공'])
"""

import json
import re
import urllib.request
import urllib.parse

import config
from modules import gemini_client


def fetch_financial_news(display=100):
    """
    네이버 뉴스 검색 API로 '특징주/주가/관련주/수혜주' 관련 최신 기사를 가져온다.

    Args:
        display: 가져올 기사 개수 (네이버 API 기본 제한상 최대 100)

    Returns:
        기사 정보(dict)의 리스트. 각 dict에는 'title'(제목), 'description'(요약) 등이 들어있다.
        API 요청이 실패하면 빈 리스트를 반환한다 (파이프라인 전체가 죽지 않도록 방어).
    """
    query = "특징주 | 주가 | 관련주 | 수혜주"
    # 네이버 API는 한글/특수문자가 섞인 쿼리를 URL에 넣을 때 인코딩이 필요함
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/news?query={encText}&display={display}&sort=date"

    request = urllib.request.Request(url)
    # 네이버 오픈API는 헤더에 클라이언트 ID/Secret을 함께 보내야 인증됨
    request.add_header("X-Naver-Client-Id", config.NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", config.NAVER_CLIENT_SECRET)

    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            return json.loads(response.read().decode('utf-8'))['items']
    except Exception as e:
        # 네트워크 오류, 인증 실패 등 어떤 이유든 여기서 잡아서 빈 리스트로 처리
        print(f"네이버 API 에러: {e}")
    return []


def extract_trends_with_llm(news_items):
    """
    뉴스 헤드라인 목록을 Gemini에게 보내 '가장 핫한 산업/테마 키워드 TOP 5'를 추출한다.

    Args:
        news_items: fetch_financial_news()가 반환한 기사 dict 리스트

    Returns:
        트렌드 키워드 문자열 리스트 (예: ['반도체', '인공지능', ...]).
        LLM 호출이 실패하면 빈 리스트를 반환한다.
    """
    # 네이버 API가 제목에 <b>강조태그</b> 등 HTML 태그를 섞어 보내므로 제거
    headlines = [re.sub(r'<[^>]*>', '', item['title']) for item in news_items]
    headlines_text = "\n".join(headlines)

    prompt = f"""
    다음은 주식 시장 최신 뉴스 헤드라인 100개입니다.
    가장 핫한 '산업군, 테마, 기술 트렌드' 키워드 TOP 5를 추출해주세요.

    [출력 규칙 - 반드시 지켜주세요]
    1. 오직 키워드 5개만 콤마로 구분해서 한 줄로 출력하세요. (예: 반도체,인공지능,바이오,원전,우주항공)
    2. 설명, 인사말, 번호, 마크다운(**) 등 키워드 외의 어떤 텍스트도 절대 포함하지 마세요.
    3. '지정', '상승' 같은 공시/주식 일반 용어는 제외하고 오직 산업/테마 명사만 사용하세요.

    [헤드라인]
    {headlines_text}
    """
    try:
        response = gemini_client.generate_content_with_retry(
            model='gemini-flash-lite-latest',
            contents=prompt
        )
        result_text = response.text.strip()

        # 프롬프트로 지시해도 LLM이 가끔 설명 문장을 앞에 덧붙이거나(예: "분석 결과는 다음과 같습니다.")
        # 마크다운(**)으로 감싸는 경우가 있어, 방어적으로 정제한다:
        # 여러 줄이면 실제 키워드 목록일 가능성이 가장 높은 "마지막 줄"만 사용하고, 마크다운 기호를 제거.
        lines = [line.strip() for line in result_text.split('\n') if line.strip()]
        last_line = lines[-1] if lines else result_text
        last_line = last_line.replace('*', '').strip()

        # LLM이 "반도체, 인공지능, 바이오, ..." 형태의 콤마 구분 문자열로 응답하므로 split 후 공백 제거
        return [kw.strip() for kw in last_line.split(',') if kw.strip()]
    except Exception as e:
        print(f"Gemini API 에러: {e}")
        return []
