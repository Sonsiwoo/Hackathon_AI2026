"""
[공통 모듈] Gemini API 클라이언트 싱글턴

1단계(트렌드 추출)와 2단계(종목 매핑) 모두 Gemini를 호출해야 하는데,
예전에는 각 파일이 client = genai.Client(...)를 따로따로 생성해서
API 키가 두 파일에 중복돼 있었다. 이 모듈로 client 생성을 한 곳으로 모은다.
"""

import functools

from google import genai

import config


@functools.lru_cache(maxsize=1)
def get_client():
    """
    genai.Client를 딱 한 번만 생성해서 재사용한다(싱글턴 패턴).

    functools.lru_cache(maxsize=1)를 쓰면 이 함수가 처음 호출될 때만 실제로
    genai.Client(...)를 만들고, 이후 호출에서는 캐시된 같은 객체를 그대로 반환한다.
    호출부(trend_extractor.py, company_mapper.py)는 매번 새로 만들 필요 없이
    이 함수만 불러 쓰면 된다.

    Returns:
        google.genai.Client 인스턴스
    """
    return genai.Client(api_key=config.GEMINI_API_KEY)
