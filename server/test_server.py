# -*- coding: utf-8 -*-
"""서버 검사. 임시 폴더의 SQLite 파일에 서버를 띄워 실제 요청을 보낸다.

    cd server && python -m pytest
"""
import datetime
import hashlib
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="myuni-test-")
os.environ["MYUNI_DB"] = os.path.join(_TMP, "test.db")
os.environ["MYUNI_PW_ITERATIONS"] = "1000"          # 검사는 빨리
os.environ["MYUNI_LOGIN_FAIL_LIMIT"] = "3"

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

import pytest                                       # noqa: E402
from fastapi.testclient import TestClient          # noqa: E402

from common import rules as R                       # noqa: E402
from app import auth, db                            # noqa: E402
from app.main import app                            # noqa: E402

TABLES = ("sessions", "devices", "daily_progress", "user_weekly_scores", "weekly_scores",
          "characters", "users")


@pytest.fixture()
def client():
    with TestClient(app) as c:
        for t in TABLES:
            db.run("DELETE FROM %s" % t)
        auth._fails.clear()
        yield c


def device(name):
    return hashlib.sha256(name.encode()).hexdigest()


def signup(client, nickname, dev, school_id=1):
    return client.post("/api/signup", json={
        "nickname": nickname, "password": "password123", "school_id": school_id,
        "device_id": device(dev)})


def bearer(res):
    return {"Authorization": "Bearer " + res.json()["token"]}


def backdate_sync(user_id, minutes):
    t = auth.now() - datetime.timedelta(minutes=minutes)
    db.run("UPDATE characters SET last_synced_at=? WHERE user_id=?", (t.isoformat(), user_id))


def test_signup_login_and_duplicate_nickname(client):
    r = signup(client, "Duck", "pc1")
    assert r.status_code == 200, r.text
    me = r.json()["me"]
    assert me["ranked"] is True
    assert me["school"]["animal"] == "tiger"
    assert me["character"] == {"level": 1, "total_exp": 0, "evolution_stage": 0}

    assert signup(client, "duck", "pc2").status_code == 409

    ok = client.post("/api/login", json={"nickname": "DUCK", "password": "password123",
                                         "device_id": device("pc1")})
    assert ok.status_code == 200
    bad = client.post("/api/login", json={"nickname": "Duck", "password": "wrong-password",
                                          "device_id": device("pc1")})
    assert bad.status_code == 401
    assert bad.json()["detail"]["message"]


def test_login_lockout_after_repeated_failures(client):
    signup(client, "Alice", "pc1")
    for _ in range(3):
        client.post("/api/login", json={"nickname": "Alice", "password": "nope-nope",
                                        "device_id": device("pc1")})
    r = client.post("/api/login", json={"nickname": "Alice", "password": "password123",
                                        "device_id": device("pc1")})
    assert r.status_code == 429


def test_rejects_bad_input(client):
    assert signup(client, "a", "pc1").status_code == 400                 # 너무 짧다
    assert signup(client, "space name", "pc1").status_code == 400        # 공백
    assert signup(client, "Alice", "pc1", school_id=999).status_code == 400
    r = client.post("/api/signup", json={"nickname": "Alice", "password": "password123",
                                         "school_id": None, "device_id": "raw-guid"})
    assert r.status_code == 400


def test_never_stores_raw_device_id(client):
    signup(client, "Alice", "pc1")
    stored = db.q1("SELECT device_hash FROM users")["device_hash"]
    assert len(stored) == 64 and stored != device("pc1")


def test_only_first_account_per_device_is_ranked(client):
    a = signup(client, "Alice", "shared-pc")
    b = signup(client, "Bob", "shared-pc")
    assert a.json()["me"]["ranked"] is True
    assert b.json()["me"]["ranked"] is False

    for res in (a, b):
        backdate_sync(res.json()["me"]["id"], 30)
        s = client.post("/api/progress/sync", headers=bearer(res),
                        json={"active_minutes": 20, "interactions": {}})
        assert s.json()["granted"] == 20

    users = client.get("/api/rankings/users").json()["entries"]
    assert [e["nickname"] for e in users] == ["Alice"]
    assert users[0]["school_name"] == "고려대학교"
    schools = client.get("/api/rankings/schools").json()["entries"]
    assert schools[0]["rank"] == 1 and schools[0]["score"] == 20 and schools[0]["members"] == 1


def test_active_minutes_capped_by_elapsed_time_and_daily_cap(client):
    r = signup(client, "Alice", "pc1")
    # 방금 가입: 흐른 시간 0분 -> 1분만 인정
    s = client.post("/api/progress/sync", headers=bearer(r),
                    json={"active_minutes": 600, "interactions": {}})
    assert s.json()["granted"] == 1

    backdate_sync(r.json()["me"]["id"], 24 * 60)
    s = client.post("/api/progress/sync", headers=bearer(r),
                    json={"active_minutes": 1000, "interactions": {"feed": 99}}).json()
    assert s["me"]["today"]["exp"] == R.DAILY_EXP_CAP
    assert s["me"]["today"]["interactions"]["feed"] == R.INTERACTIONS["feed"]["daily_limit"]
    assert s["me"]["character"]["total_exp"] == R.DAILY_EXP_CAP
    assert s["me"]["character"]["level"] > 1


def test_unknown_interaction_rejected(client):
    r = signup(client, "Alice", "pc1")
    s = client.post("/api/progress/sync", headers=bearer(r),
                    json={"active_minutes": 0, "interactions": {"hack": 1}})
    assert s.status_code == 400


def test_school_change_once_per_month(client):
    r = signup(client, "Alice", "pc1", school_id=None)
    change = lambda sid: client.put("/api/me/school", headers=bearer(r), json={"school_id": sid})  # noqa: E731
    assert change(1).status_code == 200
    blocked = change(2)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "school_change_cooldown"

    old = (auth.now() - datetime.timedelta(days=31)).isoformat()
    db.run("UPDATE users SET school_changed_at=?", (old,))
    assert change(2).json()["school"]["id"] == 2


def test_auth_required_and_logout(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    r = signup(client, "Alice", "pc1")
    assert client.get("/api/me", headers=bearer(r)).status_code == 200
    assert client.post("/api/logout", headers=bearer(r)).status_code == 200
    assert client.get("/api/me", headers=bearer(r)).status_code == 401


def test_tokens_stored_hashed(client):
    r = signup(client, "Alice", "pc1")
    token = r.json()["token"]
    assert db.q1("SELECT 1 FROM sessions WHERE token_hash=?", (token,)) is None
    assert db.q1("SELECT 1 FROM sessions WHERE token_hash=?", (auth.token_hash(token),)) is not None
