"""
[공통 모듈] Gemini API 클라이언트 싱글턴 + 재시도 로직

1단계(트렌드 추출), 2단계(종목 매핑), 4단계(공시 요약) 모두 Gemini를 호출해야 하는데,
예전에는 각 파일이 client = genai.Client(...)를 따로따로 생성해서
API 키가 여러 파일에 중복돼 있었다. 이 모듈로 client 생성을 한 곳으로 모은다.

또한 Gemini 서버가 일시적으로 과부하 상태일 때 나는 503(UNAVAILABLE) 같은 오류는
"잠시 후 다시 시도"하면 대부분 해결되는 일시적 오류라, 호출부마다 재시도 로직을
따로 만들지 않도록 generate_content_with_retry()에서 공통으로 처리한다.
(특히 cron으로 매일 무인 실행될 때, 이런 일시적 오류로 그날 하루치 데이터가
통째로 실패해버리는 걸 막기 위해 필요함)
"""

import functools
import time

from google import genai

import config


@functools.lru_cache(maxsize=1)
def get_client():
    """
    genai.Client를 딱 한 번만 생성해서 재사용한다(싱글턴 패턴).

    functools.lru_cache(maxsize=1)를 쓰면 이 함수가 처음 호출될 때만 실제로
    genai.Client(...)를 만들고, 이후 호출에서는 캐시된 같은 객체를 그대로 반환한다.

    Returns:
        google.genai.Client 인스턴스
    """
    return genai.Client(api_key=config.GEMINI_API_KEY)


def generate_content_with_retry(model, contents, max_retries=3, initial_delay_sec=5):
    """
    Gemini API를 호출하되, 503(서버 과부하) 같은 일시적 오류가 나면
    잠깐 기다렸다가 자동으로 재시도한다 (지수 백오프: 5초 -> 10초 -> 20초 ...).

    Args:
        model: 사용할 모델명 (예: 'gemini-flash-latest')
        contents: Gemini에게 보낼 프롬프트 문자열
        max_retries: 최대 시도 횟수 (기본 3번)
        initial_delay_sec: 첫 재시도 전 대기 시간(초). 재시도할 때마다 2배씩 늘어남

    Returns:
        generate_content() 응답 객체

    Raises:
        마지막 시도까지 실패하면 그때 발생한 예외를 그대로 다시 던진다.
        (호출부가 이미 try/except로 감싸고 있으므로, 거기서 최종적으로 처리됨)
    """
    delay = initial_delay_sec
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return get_client().models.generate_content(model=model, contents=contents)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                print(f"  ⚠️ Gemini 호출 실패 (시도 {attempt}/{max_retries}): {e}")
                print(f"     {delay}초 후 재시도합니다...")
                time.sleep(delay)
                delay *= 2

    raise last_error
