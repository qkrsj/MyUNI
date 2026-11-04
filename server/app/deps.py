# -*- coding: utf-8 -*-
"""여러 라우터가 같이 쓰는 것들 - 로그인 확인, 오류 응답, 내 정보 모으기."""
import json

from fastapi import Header, HTTPException

from common import rules as R
from common.timekeys import day_key

from . import auth, db


def fail(status, code, message, **extra):
    """오류 응답. 클라이언트는 detail.message 를 그대로 사람에게 보여준다."""
    detail = {"code": code, "message": message}
    detail.update(extra)
    raise HTTPException(status, detail)


def current(authorization: str = Header(default="")):
    """Bearer 토큰을 확인하고 사용자 id 와 토큰을 돌려준다."""
    if not authorization.lower().startswith("bearer "):
        fail(401, "unauthorized", "로그인이 필요합니다.")
    token = authorization[7:].strip()
    sess = auth.lookup_session(token)
    if sess is None:
        fail(401, "unauthorized", "로그인이 만료되었습니다. 다시 로그인해 주세요.")
    auth.touch_session(sess)
    return {"user_id": sess["user_id"], "token": token}


def school_dict(row, prefix=""):
    if row is None or row[prefix + "id"] is None:
        return None
    return {
        "id": row[prefix + "id"],
        "name": row[prefix + "name"],
        "animal": row[prefix + "animal"],
        "color_primary": row[prefix + "color_primary"],
        "color_secondary": row[prefix + "color_secondary"],
        "sprite_set": row[prefix + "sprite_set"],
    }


def load_me(user_id, when=None):
    """내 정보 · 캐릭터 · 오늘 진행도. 클라이언트가 화면에 그리는 것 전부."""
    r = db.q1(
        "SELECT u.id, u.nickname, u.school_changed_at,"
        "       s.id AS s_id, s.name AS s_name, s.animal AS s_animal,"
        "       s.color_primary AS s_color_primary, s.color_secondary AS s_color_secondary,"
        "       s.sprite_set AS s_sprite_set,"
        "       c.level, c.total_exp, c.evolution_stage,"
        "       dp.exp AS today_exp, dp.interactions AS today_interactions"
        "  FROM users u"
        "  JOIN characters c ON c.user_id = u.id"
        "  LEFT JOIN schools s ON s.id = u.school_id"
        "  LEFT JOIN daily_progress dp ON dp.user_id = u.id AND dp.day = ?"
        " WHERE u.id = ?",
        (day_key(when), user_id))
    if r is None:
        fail(404, "not_found", "계정을 찾을 수 없습니다.")
    try:
        today = json.loads(r["today_interactions"] or "{}")
    except ValueError:
        today = {}
    return {
        "id": r["id"],
        "nickname": r["nickname"],
        "school": school_dict(r, "s_"),
        "school_changed_at": r["school_changed_at"],
        "ranked": auth.is_ranked(user_id),
        "character": {
            "level": r["level"],
            "total_exp": r["total_exp"],
            "evolution_stage": r["evolution_stage"],
        },
        "today": {
            "day": day_key(when),
            "exp": r["today_exp"] or 0,
            "interactions": R.normalize_interactions(today),
        },
    }
