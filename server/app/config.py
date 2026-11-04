# -*- coding: utf-8 -*-
"""서버 설정. 전부 환경 변수(MYUNI_*)로 바꿀 수 있다.

운영에서 바꿀 일이 있는 것만 여기 둔다. 게임 규칙 수치는 common/rules.py 에 있다
(클라이언트도 같은 값을 써야 해서).
"""
import os
import secrets
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from common.version import VERSION  # noqa: E402,F401

# SQLite 파일. 도커에서는 볼륨(/data)에 둔다 - 컨테이너를 새로 만들어도 남게.
DB_PATH = os.environ.get("MYUNI_DB") or os.path.join(os.path.dirname(_HERE), "myuni.db")

# 학교 목록. 서버가 켜질 때 DB 에 맞춰 넣는다 (이름이 같으면 색 · 동물만 고친다).
SCHOOLS_PATH = os.environ.get("MYUNI_SCHOOLS") or os.path.join(os.path.dirname(_HERE), "data", "schools.json")

# 비밀번호는 PBKDF2-HMAC-SHA256. 검사에서는 빨리 돌게 낮춘다.
PW_ITERATIONS = int(os.environ.get("MYUNI_PW_ITERATIONS", "200000"))
MIN_PASSWORD = 8
MAX_PASSWORD = 72

MIN_NICKNAME = 2
MAX_NICKNAME = 16

# 로그인 유지 기간. 토큰 원본은 클라이언트만 갖고, DB 에는 해시만 넣는다.
TOKEN_DAYS = int(os.environ.get("MYUNI_TOKEN_DAYS", "30"))

# 같은 닉네임으로 이만큼 틀리면 잠시 막는다 (비밀번호 맞혀 보기 방지).
LOGIN_FAIL_LIMIT = int(os.environ.get("MYUNI_LOGIN_FAIL_LIMIT", "10"))
LOGIN_FAIL_WINDOW_SEC = int(os.environ.get("MYUNI_LOGIN_FAIL_WINDOW", "600"))

RANKING_LIMIT = 100


def _device_salt():
    """기기 해시에 섞는 비밀 값.

    환경 변수가 없으면 DB 옆에 파일로 만들어 둔다. **이 값을 잃으면 기기 판정이
    전부 새로 시작된다** (같은 기기가 새 기기로 보인다). 백업할 때 DB 와 같이 챙긴다.
    """
    v = os.environ.get("MYUNI_DEVICE_SALT")
    if v:
        return v
    path = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "device_salt")
    try:
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
        if v:
            return v
    except OSError:
        pass
    v = secrets.token_hex(32)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(v)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return v


DEVICE_SALT = _device_salt()
