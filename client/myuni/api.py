# -*- coding: utf-8 -*-
"""서버와 이야기하는 곳. 화면 코드는 여기만 부른다.

**Tk 스레드에서 직접 부르지 않는다** - 네트워크가 느리면 캐릭터가 멈춘다.
app.Worker 가 다른 스레드에서 부르고 결과만 Tk 쪽으로 넘긴다.
"""
import requests

from . import config
from .device import device_id

TIMEOUT = 10


class ApiError(Exception):
    def __init__(self, status, code, message):
        Exception.__init__(self, message)
        self.status, self.code, self.message = status, code, message


class Api(object):
    def __init__(self, base=None, token=None):
        self.base = (base or config.SERVER_URL).rstrip("/")
        self.token = token
        self.http = requests.Session()

    def _call(self, method, path, body=None, params=None):
        headers = {"Authorization": "Bearer " + self.token} if self.token else {}
        try:
            r = self.http.request(method, self.base + path, json=body, params=params,
                                  headers=headers, timeout=TIMEOUT)
        except requests.RequestException:
            raise ApiError(0, "network", "서버에 연결할 수 없습니다.")
        try:
            data = r.json()
        except ValueError:
            data = {}
        if r.status_code >= 400:
            detail = data.get("detail") if isinstance(data, dict) else None
            if isinstance(detail, dict):
                raise ApiError(r.status_code, detail.get("code", "error"),
                               detail.get("message") or "요청이 실패했습니다.")
            raise ApiError(r.status_code, "error", "요청이 실패했습니다. (%d)" % r.status_code)
        return data

    # ---------------------------------------------------------------- 공개
    def version(self):
        return self._call("GET", "/api/version").get("version")

    def schools(self):
        return self._call("GET", "/api/schools")["schools"]

    def school_rankings(self, week=None):
        return self._call("GET", "/api/rankings/schools", params={"week": week} if week else None)

    def user_rankings(self, week=None, school_id=None):
        params = {k: v for k, v in (("week", week), ("school_id", school_id)) if v}
        return self._call("GET", "/api/rankings/users", params=params or None)

    # ---------------------------------------------------------------- 계정
    def signup(self, nickname, password, school_id):
        r = self._call("POST", "/api/signup", {"nickname": nickname, "password": password,
                                               "school_id": school_id, "device_id": device_id()})
        self.token = r["token"]
        return r

    def login(self, nickname, password):
        r = self._call("POST", "/api/login", {"nickname": nickname, "password": password,
                                              "device_id": device_id()})
        self.token = r["token"]
        return r

    def logout(self):
        try:
            self._call("POST", "/api/logout")
        finally:
            self.token = None

    def me(self):
        return self._call("GET", "/api/me")

    def change_school(self, school_id):
        return self._call("PUT", "/api/me/school", {"school_id": school_id})

    def sync(self, active_minutes, interactions):
        return self._call("POST", "/api/progress/sync",
                          {"active_minutes": active_minutes, "interactions": interactions})
