"""
[4단계용 모듈] DART(전자공시시스템) 클라이언트 싱글턴

gemini_client.py와 동일한 패턴 - OpenDartReader 인스턴스를 매번 새로 만들지 않고
한 번만 생성해서 재사용한다.
"""

import functools

# pip 패키지명은 대문자 섞인 OpenDartReader지만, 실제 import 가능한 모듈명은 소문자 opendartreader.
# (opendartreader/__init__.py 안에서 `from .dart import OpenDartReader` 로 클래스를 노출함)
from opendartreader import OpenDartReader

import config


@functools.lru_cache(maxsize=1)
def get_client():
    """
    OpenDartReader를 딱 한 번만 생성해서 재사용한다(싱글턴 패턴).

    Returns:
        OpenDartReader 인스턴스
    """
    return OpenDartReader(config.DART_API_KEY)
