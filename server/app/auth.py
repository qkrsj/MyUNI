# -*- coding: utf-8 -*-
"""계정, 세션, 기기.

비밀번호는 PBKDF2-HMAC-SHA256 으로만 저장한다(평문 저장 안 함).
토큰은 원본을 주고 DB 에는 해시만 넣는다. DB 가 새어도 토큰을 못 쓴다.

기기: 클라이언트는 SHA-256(기기 고유값) 만 보낸다. 서버는 거기에 비밀 salt 로
HMAC 을 한 번 더 걸어 저장한다. DB 가 새어도 salt 없이는 어느 기기인지 대조할 수 없다.
"""
import datetime
import hashlib
import hmac
import re
import secrets
import threading
import time

from . import config, db

NICKNAME_RE = re.compile(r"^[0-9A-Za-z가-힣_]+$")
DEVICE_RE = re.compile(r"^[0-9a-f]{64}$")


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def now_iso():
    return now().isoformat()


def parse_iso(s):
    try:
        return datetime.datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- 검사
def check_nickname(name):
    name = (name or "").strip()
    if not (config.MIN_NICKNAME <= len(name) <= config.MAX_NICKNAME):
        return None, "닉네임은 %d~%d자여야 합니다." % (config.MIN_NICKNAME, config.MAX_NICKNAME)
    if not NICKNAME_RE.match(name):
        return None, "닉네임에는 한글, 영문, 숫자, _ 만 쓸 수 있습니다."
    return name, None


def check_password(pw):
    pw = pw or ""
    if not (config.MIN_PASSWORD <= len(pw) <= config.MAX_PASSWORD):
        return "비밀번호는 %d~%d자여야 합니다." % (config.MIN_PASSWORD, config.MAX_PASSWORD)
    return None


def check_device(device_id):
    return bool(device_id) and bool(DEVICE_RE.match(device_id))


# ---------------------------------------------------------------- 비밀번호
def hash_password(password, salt=None, iterations=None):
    salt = salt or secrets.token_bytes(16)
    iterations = iterations or config.PW_ITERATIONS
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return h, salt, iterations


def verify_password(password, pw_hash, salt, iterations):
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(h, pw_hash)


# 없는 닉네임으로 로그인해도 같은 시간이 걸리게 (닉네임이 있는지 떠보기 방지)
_DUMMY = hash_password("dummy-password-for-timing")


def verify_or_dummy(password, row):
    if row is None:
        verify_password(password, *_DUMMY)
        return False
    return verify_password(password, row["pw_hash"], row["pw_salt"], row["pw_iter"])


# ---------------------------------------------------------------- 로그인 시도 제한
_fail_lock = threading.Lock()
_fails = {}          # 닉네임(소문자) -> [시각, ...]


def too_many_failures(nickname):
    key = (nickname or "").lower()
    cutoff = time.monotonic() - config.LOGIN_FAIL_WINDOW_SEC
    with _fail_lock:
        recent = [t for t in _fails.get(key, []) if t > cutoff]
        _fails[key] = recent
        return len(recent) >= config.LOGIN_FAIL_LIMIT


def note_failure(nickname):
    with _fail_lock:
        _fails.setdefault((nickname or "").lower(), []).append(time.monotonic())


def clear_failures(nickname):
    with _fail_lock:
        _fails.pop((nickname or "").lower(), None)


# ---------------------------------------------------------------- 기기
def device_hash(device_id):
    return hmac.new(config.DEVICE_SALT.encode("utf-8"), device_id.encode("ascii"),
                    hashlib.sha256).hexdigest()


def claim_device(dev_hash, user_id):
    """이 기기에 아직 랭킹 반영 계정이 없으면 이 계정을 지정한다."""
    db.run("INSERT OR IGNORE INTO devices (device_hash, ranked_user_id, created_at) VALUES (?,?,?)",
           (dev_hash, user_id, now_iso()))


def is_ranked(user_id):
    return db.q1("SELECT 1 FROM devices WHERE ranked_user_id=?", (user_id,)) is not None


# ---------------------------------------------------------------- 토큰
def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(user_id, dev_hash):
    token = secrets.token_urlsafe(32)
    t = now()
    db.run("INSERT INTO sessions (token_hash, user_id, device_hash, created_at, last_seen, expires_at)"
           " VALUES (?,?,?,?,?,?)",
           (token_hash(token), user_id, dev_hash, t.isoformat(), t.isoformat(),
            (t + datetime.timedelta(days=config.TOKEN_DAYS)).isoformat()))
    return token


def lookup_session(token):
    if not token:
        return None
    row = db.q1("SELECT * FROM sessions WHERE token_hash=?", (token_hash(token),))
    if row is None:
        return None
    exp = parse_iso(row["expires_at"])
    if exp is None or exp < now():
        db.run("DELETE FROM sessions WHERE token_hash=?", (row["token_hash"],))
        return None
    return row


def touch_session(row):
    """마지막 사용 시각. 매 요청마다 쓰면 낭비라 10분에 한 번만."""
    last = parse_iso(row["last_seen"])
    if last is None or (now() - last).total_seconds() > 600:
        db.run("UPDATE sessions SET last_seen=? WHERE token_hash=?", (now_iso(), row["token_hash"]))


def revoke_token(token):
    db.run("DELETE FROM sessions WHERE token_hash=?", (token_hash(token),))
