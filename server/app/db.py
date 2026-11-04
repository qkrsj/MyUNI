# -*- coding: utf-8 -*-
"""저장소. SQLite 파일 하나.

서버와 DB 를 한 대(Lightsail)에 두므로 왕복이 없다. FastAPI 는 동기 함수를
스레드 풀에서 돌리므로 연결은 스레드마다 하나씩 연다.

여러 줄을 함께 바꾸는 곳(경험치 동기화, 학교 변경)은 `with db.tx():` 로 감싼다.
BEGIN IMMEDIATE 라서 같은 사람이 동시에 두 번 보내도 차례로 처리된다.
"""
import contextlib
import json
import os
import sqlite3
import threading

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS schools (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL UNIQUE,
    animal           TEXT NOT NULL,
    color_primary    TEXT NOT NULL,
    color_secondary  TEXT NOT NULL,
    sprite_set       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname           TEXT NOT NULL UNIQUE COLLATE NOCASE,
    pw_hash            BLOB NOT NULL,
    pw_salt            BLOB NOT NULL,
    pw_iter            INTEGER NOT NULL,
    school_id          INTEGER REFERENCES schools(id),
    school_changed_at  TEXT,
    -- 가입한 기기 (HMAC 값. 원본 기기 ID 는 서버에 오지도 않는다)
    device_hash        TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    last_login         TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash   TEXT PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_hash  TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    expires_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- 기기당 랭킹 반영 계정 1개. 그 기기에서 처음 가입/로그인한 계정이 들어간다.
CREATE TABLE IF NOT EXISTS devices (
    device_hash     TEXT PRIMARY KEY,
    ranked_user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(ranked_user_id);

CREATE TABLE IF NOT EXISTS characters (
    user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    level            INTEGER NOT NULL DEFAULT 1,
    total_exp        INTEGER NOT NULL DEFAULT 0,
    evolution_stage  INTEGER NOT NULL DEFAULT 0,
    last_active_at   TEXT,
    -- 활동 시간을 실제로 흐른 시간 안으로 자를 때 쓴다
    last_synced_at   TEXT NOT NULL
);

-- 하루 상한 / 상호작용 횟수 제한 판정용
CREATE TABLE IF NOT EXISTS daily_progress (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    day           TEXT NOT NULL,
    exp           INTEGER NOT NULL DEFAULT 0,
    interactions  TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (user_id, day)
);

-- 주간 개인 점수. school_id 는 점수를 얻은 때의 소속
CREATE TABLE IF NOT EXISTS user_weekly_scores (
    week       TEXT NOT NULL,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    school_id  INTEGER REFERENCES schools(id),
    score      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (week, user_id)
);
CREATE INDEX IF NOT EXISTS idx_uws_rank ON user_weekly_scores(week, score DESC);

-- 주간 학교 점수 (랭킹 반영 계정만 더한다)
CREATE TABLE IF NOT EXISTS weekly_scores (
    week       TEXT NOT NULL,
    school_id  INTEGER NOT NULL REFERENCES schools(id),
    score      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (week, school_id)
);
CREATE INDEX IF NOT EXISTS idx_ws_rank ON weekly_scores(week, score DESC);
"""


def connect():
    conn = getattr(_local, "conn", None)
    if conn is None:
        d = os.path.dirname(os.path.abspath(config.DB_PATH))
        os.makedirs(d, exist_ok=True)
        # isolation_level=None: 트랜잭션은 tx() 가 직접 연다
        conn = sqlite3.connect(config.DB_PATH, timeout=15, isolation_level=None,
                               check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=15000")
        _local.conn = conn
    return conn


def close():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def init():
    conn = connect()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    seed_schools()


def seed_schools(path=None):
    """data/schools.json 을 DB 에 맞춘다. 지우지는 않는다 (점수가 걸려 있다)."""
    path = path or config.SCHOOLS_PATH
    try:
        with open(path, encoding="utf-8") as f:
            schools = json.load(f)
    except OSError:
        return
    with tx():
        for s in schools:
            run("INSERT INTO schools (name, animal, color_primary, color_secondary, sprite_set)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(name) DO UPDATE SET animal=excluded.animal,"
                " color_primary=excluded.color_primary, color_secondary=excluded.color_secondary,"
                " sprite_set=excluded.sprite_set",
                (s["name"], s["animal"], s["color_primary"], s["color_secondary"],
                 s.get("sprite_set") or s["animal"]))


@contextlib.contextmanager
def tx():
    conn = connect()
    if conn.in_transaction:          # 이미 열려 있으면 그 안에서 돈다
        yield conn
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def q(sql, args=()):
    return connect().execute(sql, args).fetchall()


def q1(sql, args=()):
    return connect().execute(sql, args).fetchone()


def run(sql, args=()):
    return connect().execute(sql, args)
