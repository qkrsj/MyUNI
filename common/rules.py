# -*- coding: utf-8 -*-
"""게임 규칙. 클라이언트(즉시 반응용 예측)와 서버(최종 판정)가 같은 코드를 쓴다.

수치는 모두 임시값이다. 플레이 테스트 뒤 여기만 고치면 양쪽에 같이 적용된다.
(docs/ARCHITECTURE.md 의 "미정 규칙" 참고)
"""

# 컴퓨터를 쓰는 중(자리 비움 아님)일 때 1분에 얻는 경험치
ACTIVE_EXP_PER_MINUTE = 1

# 이 시간(초) 이상 입력이 없으면 자리 비움으로 본다. 캐릭터도 잠든다.
IDLE_THRESHOLD_SEC = 300

# 하루 경험치 상한 (모든 출처 합계)
DAILY_EXP_CAP = 300

# 상호작용: 한 번에 얻는 경험치와 하루 횟수 제한
INTERACTIONS = {
    "feed": {"exp": 5, "daily_limit": 5, "label": "먹이 주기"},
    "play": {"exp": 8, "daily_limit": 5, "label": "놀아 주기"},
}
INTERACTION_KINDS = tuple(INTERACTIONS)

# 서버가 인정하는 활동 시간 = 실제 흐른 시간 x 이 값 (+1분). 타이머 오차 여유.
ACTIVE_MINUTES_SLACK = 1.1

MAX_LEVEL = 99

# 진화 단계 (단계 수 · 조건은 미정, 임시)
EVOLUTION_STAGES = (
    {"stage": 0, "key": "egg", "name": "알", "min_level": 1},
    {"stage": 1, "key": "baby", "name": "아기", "min_level": 3},
    {"stage": 2, "key": "teen", "name": "청소년", "min_level": 10},
    {"stage": 3, "key": "adult", "name": "어른", "min_level": 25},
)


# ---------------------------------------------------------------- 레벨
def exp_to_next_level(level):
    """레벨 n -> n+1 에 필요한 경험치."""
    return int(round(50 * level ** 1.4))


def total_exp_for_level(level):
    """그 레벨에 막 도달했을 때의 누적 경험치."""
    return sum(exp_to_next_level(lv) for lv in range(1, level))


def level_from_total_exp(total_exp):
    level, remaining = 1, total_exp
    while level < MAX_LEVEL and remaining >= exp_to_next_level(level):
        remaining -= exp_to_next_level(level)
        level += 1
    return level


def level_progress(total_exp, level):
    """현재 레벨 안에서의 진행도 0..1."""
    if level >= MAX_LEVEL:
        return 1.0
    inside = total_exp - total_exp_for_level(level)
    return max(0.0, min(1.0, inside / float(exp_to_next_level(level))))


def evolution_stage_for_level(level):
    stage = 0
    for s in EVOLUTION_STAGES:
        if level >= s["min_level"]:
            stage = s["stage"]
    return stage


# ---------------------------------------------------------------- 하루 경험치
def empty_interactions():
    return {k: 0 for k in INTERACTION_KINDS}


def normalize_interactions(raw):
    out = empty_interactions()
    if isinstance(raw, dict):
        for k in INTERACTION_KINDS:
            v = raw.get(k)
            if isinstance(v, int) and not isinstance(v, bool):
                out[k] = v
    return out


def apply_gain(day_exp, day_interactions, active_minutes, interactions):
    """하루 기록에 이번 획득분을 적용한다.

    횟수 제한과 하루 상한을 넘는 부분은 버린다.
    돌려주는 것: (실제로 주는 경험치, 새 하루 경험치, 새 상호작용 횟수)
    """
    counts = normalize_interactions(day_interactions)
    raw = max(0, int(active_minutes or 0)) * ACTIVE_EXP_PER_MINUTE

    for kind in INTERACTION_KINDS:
        rule = INTERACTIONS[kind]
        requested = max(0, int((interactions or {}).get(kind) or 0))
        allowed = min(requested, max(0, rule["daily_limit"] - counts[kind]))
        counts[kind] += allowed
        raw += allowed * rule["exp"]

    granted = min(raw, max(0, DAILY_EXP_CAP - day_exp))
    return granted, day_exp + granted, counts
