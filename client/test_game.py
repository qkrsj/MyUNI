# -*- coding: utf-8 -*-
"""클라이언트 게임 로직 검사. 창도 서버도 필요 없다.

    python -m pytest client
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))

from common import rules as R                # noqa: E402
from common.timekeys import day_key          # noqa: E402
from myuni import sprites                    # noqa: E402
from myuni.game import Game                  # noqa: E402


def make_me(level=1, total=0, stage=0, feed=0, day=None):
    return {
        "id": 1, "nickname": "오리", "ranked": True,
        "school": {"name": "테스트대", "animal": "tiger", "color_primary": "#8B0029",
                   "color_secondary": "#FFFFFF"},
        "character": {"level": level, "total_exp": total, "evolution_stage": stage},
        "today": {"day": day or day_key(), "exp": 0, "interactions": {"feed": feed, "play": 0}},
    }


def test_idle_minutes_do_not_count():
    g = Game(make_me())
    g.tick_minute(idle_sec=10)
    g.tick_minute(idle_sec=R.IDLE_THRESHOLD_SEC + 1)
    assert g.pending_active == 1
    assert g.sleeping is True
    g.tick_minute(idle_sec=0)
    assert g.sleeping is False


def test_sync_every_five_minutes():
    g = Game(make_me())
    due = [g.tick_minute(0) for _ in range(10)]
    assert due == [False, False, False, False, True] * 2


def test_interaction_limit_counts_server_and_pending():
    limit = R.INTERACTIONS["feed"]["daily_limit"]
    g = Game(make_me(feed=limit - 1))
    assert g.interact("feed") == "ok"
    assert g.interact("feed") == "limit"


def test_new_day_resets_local_limit():
    limit = R.INTERACTIONS["feed"]["daily_limit"]
    g = Game(make_me(feed=limit, day="2000-01-01"))
    assert g.left_today("feed") == limit


def test_failed_sync_returns_batch():
    g = Game(make_me())
    g.tick_minute(0)
    g.interact("play")
    batch = g.take_batch()
    assert not g.has_pending()
    g.return_batch(batch)
    assert g.pending_active == 1 and g.pending_inter["play"] == 1


def test_apply_me_reports_level_up_and_evolution():
    g = Game(make_me())
    events = g.apply_me(make_me(level=3, total=R.total_exp_for_level(3), stage=1))
    assert ("level_up", 3) in events and ("evolved", 1) in events
    assert g.view()["stage"] == 1


def test_sprites_have_every_pose_and_fixed_size():
    frames = sprites.build_frames(3, "eagle", "#003876", "#FFFFFF")
    for pose, n in sprites.POSES.items():
        for facing in (1, -1):
            imgs = frames[(pose, facing)]
            assert len(imgs) == n
            assert all(im.size == (sprites.WIDTH, sprites.HEIGHT) for im in imgs)
            assert all(im.getbbox() for im in imgs)          # 빈 그림이 없다
