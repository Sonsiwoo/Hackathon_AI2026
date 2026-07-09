"""
SQLite DB 연결 모듈

예측 파이프라인(src/modules/prediction_logger.py)이 쓰는 것과 같은
backend/stock_predictions.db 파일을 읽기 전용으로 조회한다.
가벼운 프로젝트라 SQLAlchemy 같은 ORM 없이 표준 라이브러리 sqlite3만 사용한다.
"""

import os
import sqlite3

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
DB_PATH = os.path.join(_APP_DIR, 'stock_predictions.db')


def get_connection():
    """
    predictions 테이블에 접근할 SQLite 커넥션을 하나 만들어 반환한다.
    row_factory를 sqlite3.Row로 설정해두면 조회 결과를 dict처럼
    컬럼명으로 접근할 수 있어(row['code']) FastAPI 응답 변환이 쉬워진다.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
