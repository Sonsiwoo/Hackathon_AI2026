"""
[4단계용 모듈] DART(전자공시시스템) 클라이언트 싱글턴

gemini_client.py와 동일한 패턴 - OpenDartReader 인스턴스를 매번 새로 만들지 않고
한 번만 생성해서 재사용한다.
"""

import functools

import config

# OpenDartReader 패키지는 버전에 따라 실제 import 구조가 다르다:
#   - 0.3.x (최신, 소문자 패키지명): from opendartreader import OpenDartReader
#   - 0.2.x (구버전, 대문자 패키지명): OpenDartReader/__init__.py가 sys.modules를 자기 자신
#     대신 클래스로 바꿔치기해서, `import OpenDartReader`만 해도 클래스가 바로 잡힘
# 설치된 버전이 뭐든 상관없이 동작하도록 둘 다 시도한다.
try:
    from opendartreader import OpenDartReader
except ImportError:
    import OpenDartReader


@functools.lru_cache(maxsize=1)
def get_client():
    """
    OpenDartReader를 딱 한 번만 생성해서 재사용한다(싱글턴 패턴).

    Returns:
        OpenDartReader 인스턴스
    """
    return OpenDartReader(config.DART_API_KEY)
