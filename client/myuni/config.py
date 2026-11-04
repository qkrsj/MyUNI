# -*- coding: utf-8 -*-
"""클라이언트 설정과 로그인 정보, 기록 남기기."""
import datetime
import json
import os
import sys
import traceback

from . import platform_os as PLAT

APP_NAME = "MyUNi"

# 서버 주소. 배포판은 빌드할 때 server_url.txt 를 같이 넣는다 (tools/build_exe.py).
# 개발할 때는 docker compose 로 띄운 서버(8787)로 간다. MYUNI_SERVER 로 바꿀 수 있다.
DEFAULT_SERVER = "http://127.0.0.1:8787"


def _bundled_server_url():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "server_url.txt"), encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


SERVER_URL = (os.environ.get("MYUNI_SERVER") or _bundled_server_url() or DEFAULT_SERVER).rstrip("/")

_DATA_DIR = None


def data_dir():
    global _DATA_DIR
    if _DATA_DIR is None:
        _DATA_DIR = os.environ.get("MYUNI_DATA_DIR") or PLAT.data_dir(APP_NAME)
        os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


def log(msg):
    """문제가 생겼을 때 볼 기록. pythonw 로 돌면 콘솔이 없어서 파일로 남긴다."""
    try:
        path = os.path.join(data_dir(), "myuni.log")
        if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
            os.replace(path, path + ".old")
        with open(path, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg))
    except Exception:                                       # noqa: BLE001
        pass


def log_exc(what):
    log(what + "\n" + traceback.format_exc())


# ---------------------------------------------------------------- 로그인 정보
def _session_path():
    return os.path.join(data_dir(), "session.json")


def load_session():
    """{"token": ..., "me": {...}} 또는 None."""
    try:
        with open(_session_path(), encoding="utf-8") as f:
            s = json.load(f)
        if isinstance(s, dict) and s.get("token") and isinstance(s.get("me"), dict):
            return s
    except (OSError, ValueError):
        pass
    return None


def save_session(token, me):
    path = _session_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"token": token, "me": me}, f, ensure_ascii=False)
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def clear_session():
    try:
        os.remove(_session_path())
    except OSError:
        pass
