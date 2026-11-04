# -*- coding: utf-8 -*-
"""버전은 여기 한 곳에만 적는다.

서버, 클라이언트, exe 빌드가 전부 이 값을 읽는다.
릴리스할 때는 이 숫자를 올리고 같은 이름의 태그(v0.1.0)를 민다.
"""

VERSION = "0.1.0"


def series(v=None):
    """앞 두 자리. 서버와 클라이언트는 이게 같아야 함께 쓸 수 있다."""
    parts = (v or VERSION).split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else (v or VERSION)


def compatible(other):
    """서버가 알려준 버전과 함께 써도 되는지."""
    if not other:
        return True
    return series(other) == series()
