# -*- coding: utf-8 -*-
"""MyUNi 서버.

경험치 판정은 전부 서버가 한다. 클라이언트는 결과만 받는다.

    uvicorn app.main:app --port 8080        (server/ 에서)
"""
import datetime
import os
import sys
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (os.path.dirname(_HERE), os.path.dirname(os.path.dirname(_HERE))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contextlib import asynccontextmanager       # noqa: E402

from fastapi import Depends, FastAPI             # noqa: E402
from pydantic import BaseModel                   # noqa: E402

from common.timekeys import SCHOOL_CHANGE_COOLDOWN_DAYS  # noqa: E402
from common.version import VERSION               # noqa: E402

from . import auth, db, deps, progress, rankings  # noqa: E402


@asynccontextmanager
async def lifespan(_app):
    db.init()
    yield


app = FastAPI(title="MyUNi", version=VERSION, lifespan=lifespan)
app.include_router(progress.router)
app.include_router(rankings.router)


class SignupIn(BaseModel):
    nickname: str
    password: str
    school_id: Optional[int] = None
    device_id: str


class LoginIn(BaseModel):
    nickname: str
    password: str
    device_id: str


class SchoolIn(BaseModel):
    school_id: int


# ---------------------------------------------------------------- 공개
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/version")
def version():
    return {"version": VERSION}


@app.get("/api/schools")
def schools():
    rows = db.q("SELECT * FROM schools ORDER BY name")
    return {"schools": [deps.school_dict(r) for r in rows]}


# ---------------------------------------------------------------- 계정
@app.post("/api/signup")
def signup(body: SignupIn):
    name, err = auth.check_nickname(body.nickname)
    if err:
        deps.fail(400, "invalid_nickname", err)
    err = auth.check_password(body.password)
    if err:
        deps.fail(400, "invalid_password", err)
    if not auth.check_device(body.device_id):
        deps.fail(400, "invalid_device", "기기 정보가 올바르지 않습니다.")

    dev = auth.device_hash(body.device_id)
    pw_hash, salt, iters = auth.hash_password(body.password)
    now = auth.now_iso()
    with db.tx():
        if body.school_id is not None and db.q1("SELECT 1 FROM schools WHERE id=?", (body.school_id,)) is None:
            deps.fail(400, "unknown_school", "목록에 없는 학교입니다.")
        if db.q1("SELECT 1 FROM users WHERE nickname=?", (name,)) is not None:
            deps.fail(409, "nickname_taken", "이미 쓰고 있는 닉네임입니다.")
        # 가입 때 학교를 골랐으면 그때부터 30일 동안 못 바꾼다
        cur = db.run(
            "INSERT INTO users (nickname, pw_hash, pw_salt, pw_iter, school_id, school_changed_at,"
            " device_hash, created_at, last_login) VALUES (?,?,?,?,?,?,?,?,?)",
            (name, pw_hash, salt, iters, body.school_id, now if body.school_id else None, dev, now, now))
        uid = cur.lastrowid
        db.run("INSERT INTO characters (user_id, last_synced_at) VALUES (?,?)", (uid, now))
        auth.claim_device(dev, uid)
        token = auth.issue_token(uid, dev)
    return {"token": token, "me": deps.load_me(uid)}


@app.post("/api/login")
def login(body: LoginIn):
    if not auth.check_device(body.device_id):
        deps.fail(400, "invalid_device", "기기 정보가 올바르지 않습니다.")
    if auth.too_many_failures(body.nickname):
        deps.fail(429, "too_many_attempts", "로그인을 너무 많이 틀렸습니다. 10분 뒤에 다시 해 주세요.")
    row = db.q1("SELECT id, pw_hash, pw_salt, pw_iter FROM users WHERE nickname=?", (body.nickname.strip(),))
    if not auth.verify_or_dummy(body.password, row):
        auth.note_failure(body.nickname)
        deps.fail(401, "invalid_credentials", "닉네임 또는 비밀번호가 맞지 않습니다.")
    auth.clear_failures(body.nickname)

    dev = auth.device_hash(body.device_id)
    with db.tx():
        auth.claim_device(dev, row["id"])
        db.run("UPDATE users SET last_login=? WHERE id=?", (auth.now_iso(), row["id"]))
        token = auth.issue_token(row["id"], dev)
    return {"token": token, "me": deps.load_me(row["id"])}


@app.post("/api/logout")
def logout(me=Depends(deps.current)):
    auth.revoke_token(me["token"])
    return {"ok": True}


@app.get("/api/me")
def get_me(me=Depends(deps.current)):
    return deps.load_me(me["user_id"])


@app.put("/api/me/school")
def change_school(body: SchoolIn, me=Depends(deps.current)):
    uid = me["user_id"]
    with db.tx():
        user = db.q1("SELECT school_id, school_changed_at FROM users WHERE id=?", (uid,))
        if user["school_id"] == body.school_id:
            return deps.load_me(uid)
        if db.q1("SELECT 1 FROM schools WHERE id=?", (body.school_id,)) is None:
            deps.fail(400, "unknown_school", "목록에 없는 학교입니다.")
        changed = auth.parse_iso(user["school_changed_at"])
        if changed is not None:
            next_at = changed + datetime.timedelta(days=SCHOOL_CHANGE_COOLDOWN_DAYS)
            if next_at > auth.now():
                deps.fail(409, "school_change_cooldown",
                          "학교는 한 달에 한 번만 바꿀 수 있습니다.", next_allowed_at=next_at.isoformat())
        db.run("UPDATE users SET school_id=?, school_changed_at=? WHERE id=?",
               (body.school_id, auth.now_iso(), uid))
    return deps.load_me(uid)
