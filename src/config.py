"""
[공통 모듈] 환경변수(.env) 로딩 및 필수값 검증

예전에는 main_step1.py/step2.py 소스코드에 Naver/Gemini API 키가 평문으로
그대로 박혀 있었다(그리고 git에 커밋되어 유출됨). 이 파일은 .env 파일에서
키를 읽어와서 코드에는 값이 노출되지 않도록 한다.

.env 파일은 저장소 루트(HACKATHON/.env)에 두면 된다. python-dotenv의
load_dotenv()는 이 파일(src/config.py) 위치부터 상위 폴더로 거슬러 올라가며
.env를 찾으므로, src/ 안으로 옮겨져도 별도 경로 설정 없이 잘 찾는다.

사용법:
  1) .env.example을 복사해 .env를 만들고 실제 키 값을 채운다 (.env는 git에 커밋되지 않음)
  2) 각 진입점 스크립트 맨 앞에서 config.validate([...])를 호출해
     자신에게 필요한 키가 실제로 채워져 있는지 확인한다
"""

import os
import sys

from dotenv import load_dotenv

# .env 파일 내용을 os.environ으로 로드 (파일이 없으면 조용히 아무 것도 안 하고 넘어감)
# override=True: 이미 시스템/세션에 같은 이름의 환경변수가 설정돼 있어도
# .env 파일의 값으로 덮어쓴다. (기본값 False면 기존 환경변수가 우선이라,
# 예전에 터미널에 set으로 넣어뒀던 값이나 시스템 환경변수가 새로 바꾼 .env 값을
# 조용히 무시해버리는 혼란스러운 상황이 생길 수 있어 명시적으로 override시킴)
load_dotenv(override=True)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# validate()에서 이름(문자열) → 실제 값을 찾아보기 위한 매핑
_VALUES = {
    "NAVER_CLIENT_ID": NAVER_CLIENT_ID,
    "NAVER_CLIENT_SECRET": NAVER_CLIENT_SECRET,
    "GEMINI_API_KEY": GEMINI_API_KEY,
}


def validate(required_keys):
    """
    이 스크립트를 실행하는 데 필요한 환경변수가 모두 채워져 있는지 확인한다.
    하나라도 비어있으면 어떤 값이 빠졌는지 한글 메시지로 안내하고 즉시 프로그램을 종료한다.
    (API를 호출하기 전에 미리 걸러내서, 호출 도중 애매한 에러가 나는 것을 방지)

    Args:
        required_keys: 확인할 환경변수 이름 리스트
                        예: ['NAVER_CLIENT_ID', 'NAVER_CLIENT_SECRET', 'GEMINI_API_KEY']
    """
    missing = [key for key in required_keys if not _VALUES.get(key)]
    if missing:
        print(f"❌ .env 파일에 다음 값이 없습니다: {', '.join(missing)} (.env.example 참고)")
        sys.exit(1)
