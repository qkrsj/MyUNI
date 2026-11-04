# -*- coding: utf-8 -*-
"""주간 랭킹.

학교 점수 = 그 주에 랭킹 반영 계정들이 얻은 경험치 합계 (기준은 아직 미정 - 문서 참고).
개인 점수 = 그 주에 얻은 경험치. 닉네임 옆에 지금 학교를 같이 보여준다.
"""
import re
from typing import Optional

from fastapi import APIRouter, Query

from common.timekeys import week_key

from . import config, db, deps

router = APIRouter()

WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")


def _week(week):
    if week is None:
        return week_key()
    if not WEEK_RE.match(week):
        deps.fail(400, "invalid_request", "주차는 2026-W45 같은 꼴이어야 합니다.")
    return week


@router.get("/api/rankings/schools")
def school_rankings(week: Optional[str] = None):
    week = _week(week)
    rows = db.q(
        "SELECT RANK() OVER (ORDER BY ws.score DESC) AS rank,"
        "       s.id, s.name, s.animal, ws.score,"
        "       (SELECT COUNT(*) FROM user_weekly_scores u"
        "         WHERE u.week = ws.week AND u.school_id = ws.school_id) AS members"
        "  FROM weekly_scores ws JOIN schools s ON s.id = ws.school_id"
        " WHERE ws.week = ?"
        " ORDER BY ws.score DESC, s.name LIMIT ?",
        (week, config.RANKING_LIMIT))
    return {"week": week, "entries": [
        {"rank": r["rank"], "school": {"id": r["id"], "name": r["name"], "animal": r["animal"]},
         "score": r["score"], "members": r["members"]} for r in rows]}


@router.get("/api/rankings/users")
def user_rankings(week: Optional[str] = None, school_id: Optional[int] = Query(default=None)):
    """개인 랭킹. school_id 를 주면 그 학교 안의 랭킹 (학과별은 2차)."""
    week = _week(week)
    rows = db.q(
        "SELECT RANK() OVER (ORDER BY uws.score DESC) AS rank,"
        "       u.nickname, s.name AS school_name, uws.score"
        "  FROM user_weekly_scores uws"
        "  JOIN users u ON u.id = uws.user_id"
        "  LEFT JOIN schools s ON s.id = u.school_id"
        " WHERE uws.week = ? AND (? IS NULL OR uws.school_id = ?)"
        " ORDER BY uws.score DESC, u.nickname LIMIT ?",
        (week, school_id, school_id, config.RANKING_LIMIT))
    return {"week": week, "entries": [
        {"rank": r["rank"], "nickname": r["nickname"], "school_name": r["school_name"],
         "score": r["score"]} for r in rows]}
