# -*- coding: utf-8 -*-
"""규칙 계산 검사. 화면도 서버도 필요 없다.

    python -m pytest common
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import rules as R                    # noqa: E402
from common.timekeys import day_key, week_key    # noqa: E402

UTC = datetime.timezone.utc


def test_level_round_trip():
    for lv in range(1, 40):
        assert R.level_from_total_exp(R.total_exp_for_level(lv)) == lv
        if lv > 1:
            assert R.level_from_total_exp(R.total_exp_for_level(lv) - 1) == lv - 1


def test_evolution_stages():
    assert R.evolution_stage_for_level(1) == 0
    assert R.evolution_stage_for_level(3) == 1
    assert R.evolution_stage_for_level(99) == 3


def test_gain_active_and_interactions():
    granted, day_exp, counts = R.apply_gain(0, {}, 10, {"feed": 2})
    assert granted == 10 + 2 * R.INTERACTIONS["feed"]["exp"]
    assert day_exp == granted
    assert counts["feed"] == 2


def test_interaction_daily_limit():
    _, exp1, c1 = R.apply_gain(0, {}, 0, {"play": 4})
    granted, _, c2 = R.apply_gain(exp1, c1, 0, {"play": 10})
    assert c2["play"] == R.INTERACTIONS["play"]["daily_limit"]
    assert granted == R.INTERACTIONS["play"]["exp"]


def test_daily_cap():
    granted, day_exp, counts = R.apply_gain(0, {}, 10000, {})
    assert granted == R.DAILY_EXP_CAP
    assert R.apply_gain(day_exp, counts, 5, {"feed": 1})[0] == 0


def test_ignores_negative_input():
    assert R.apply_gain(0, {}, -5, {"feed": -1})[0] == 0


def test_day_rolls_at_kst_midnight():
    assert day_key(datetime.datetime(2026, 11, 3, 14, 59, 59, tzinfo=UTC)) == "2026-11-03"
    assert day_key(datetime.datetime(2026, 11, 3, 15, 0, 0, tzinfo=UTC)) == "2026-11-04"


def test_season_rolls_monday_kst():
    # 2026-11-09 은 월요일
    assert week_key(datetime.datetime(2026, 11, 8, 14, 59, 59, tzinfo=UTC)) == "2026-W45"
    assert week_key(datetime.datetime(2026, 11, 8, 15, 0, 0, tzinfo=UTC)) == "2026-W46"
    assert week_key(datetime.datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC)) == "2026-W53"
