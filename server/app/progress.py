# -*- coding: utf-8 -*-
"""경험치 동기화 - 서버가 최종 판정한다.

클라이언트는 마지막 동기화 뒤로 쌓인 "활동 몇 분, 먹이 몇 번" 만 보낸다.
경험치 계산과 모든 제한은 여기서 한다.

    1. 활동 시간 <= 마지막 동기화 뒤 실제로 흐른 시간 x 1.1 (+1분)
    2. 상호작용별 하루 횟수 제한
    3. 하루 경험치 상한
    4. 레벨 · 진화 단계 다시 계산
    5. 랭킹 반영 계정이면 주간 개인 점수에, 학교가 있으면 주간 학교 점수에 더한다
"""
import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from common import rules as R
from common.timekeys import day_key, week_key

from . import auth, db, deps

router = APIRouter()


class SyncIn(BaseModel):
    active_minutes: int = Field(ge=0, le=24 * 60)
    interactions: dict[str, int] = Field(default_factory=dict)


def allowed_active_minutes(requested, last_synced_at, when):
    last = auth.parse_iso(last_synced_at)
    elapsed_min = 0.0 if last is None else max(0.0, (when - last).total_seconds() / 60.0)
    return min(requested, int(elapsed_min * R.ACTIVE_MINUTES_SLACK) + 1)


@router.post("/api/progress/sync")
def sync(body: SyncIn, me=Depends(deps.current)):
    uid = me["user_id"]
    for k, v in body.interactions.items():
        if k not in R.INTERACTIONS or not (0 <= v <= 1000):
            deps.fail(400, "invalid_request", "알 수 없는 상호작용입니다: %s" % k)

    when = auth.now()
    day = day_key(when)
    with db.tx():
        ch = db.q1("SELECT total_exp, last_synced_at FROM characters WHERE user_id=?", (uid,))
        if ch is None:
            deps.fail(404, "not_found", "캐릭터를 찾을 수 없습니다.")
        active = allowed_active_minutes(body.active_minutes, ch["last_synced_at"], when)

        db.run("INSERT OR IGNORE INTO daily_progress (user_id, day) VALUES (?,?)", (uid, day))
        dp = db.q1("SELECT exp, interactions FROM daily_progress WHERE user_id=? AND day=?", (uid, day))
        granted, day_exp, counts = R.apply_gain(
            dp["exp"], json.loads(dp["interactions"] or "{}"), active, body.interactions)
        db.run("UPDATE daily_progress SET exp=?, interactions=? WHERE user_id=? AND day=?",
               (day_exp, json.dumps(counts), uid, day))

        total = ch["total_exp"] + granted
        level = R.level_from_total_exp(total)
        did_something = active > 0 or any(v > 0 for v in body.interactions.values())
        db.run("UPDATE characters SET total_exp=?, level=?, evolution_stage=?, last_synced_at=?,"
               " last_active_at = CASE WHEN ? THEN ? ELSE last_active_at END"
               " WHERE user_id=?",
               (total, level, R.evolution_stage_for_level(level), when.isoformat(),
                int(did_something), when.isoformat(), uid))

        if granted > 0:
            _add_weekly(uid, week_key(when), granted)

    return {"granted": granted, "me": deps.load_me(uid, when)}


def _add_weekly(uid, week, amount):
    if not auth.is_ranked(uid):
        return
    school_id = db.q1("SELECT school_id FROM users WHERE id=?", (uid,))["school_id"]
    db.run("INSERT INTO user_weekly_scores (week, user_id, school_id, score) VALUES (?,?,?,?)"
           " ON CONFLICT(week, user_id) DO UPDATE SET score = score + excluded.score,"
           " school_id = excluded.school_id",
           (week, uid, school_id, amount))
    if school_id is not None:
        db.run("INSERT INTO weekly_scores (week, school_id, score) VALUES (?,?,?)"
               " ON CONFLICT(week, school_id) DO UPDATE SET score = score + excluded.score",
               (week, school_id, amount))
