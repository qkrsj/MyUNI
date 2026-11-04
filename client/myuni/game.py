# -*- coding: utf-8 -*-
"""게임 로직 (클라이언트 쪽). 화면도 네트워크도 모른다 - 그래서 창 없이 검사할 수 있다.

    * 1분마다 자리 비움인지 보고, 아니면 활동 1분을 쌓는다. 자리 비움이면 캐릭터가 잔다.
    * 쌓인 활동 · 상호작용을 서버로 보낼 묶음으로 꺼내 준다 (take_batch).
    * 보내다 실패하면 묶음을 돌려받아 다음에 다시 보낸다 (return_batch).
    * 서버가 준 결과로 상태를 바꾸고, 레벨 업 · 진화 같은 일을 알려준다 (apply_me).

경험치의 최종 판정은 서버가 한다. 여기서 횟수 제한을 보는 것은 바로 반응하기 위해서다.
"""
from common import rules as R
from common.timekeys import day_key


class Game(object):
    SYNC_EVERY_MINUTES = 5

    def __init__(self, me):
        self.me = me
        self.sleeping = False
        self.minutes = 0
        self.pending_active = 0
        self.pending_inter = R.empty_interactions()

    # ---------------------------------------------------------------- 시간
    def tick_minute(self, idle_sec):
        """1분마다 부른다. 이번에 서버로 보낼 때가 됐으면 True."""
        idle = idle_sec >= R.IDLE_THRESHOLD_SEC
        if not idle:
            self.pending_active += 1
        self.sleeping = idle
        self.minutes += 1
        return self.minutes % self.SYNC_EVERY_MINUTES == 0

    # ---------------------------------------------------------------- 상호작용
    def _server_today(self):
        """서버가 알려준 오늘 기록. 날이 바뀌었으면 0 부터."""
        today = self.me.get("today") or {}
        if today.get("day") != day_key():
            return 0, R.empty_interactions()
        return today.get("exp", 0), R.normalize_interactions(today.get("interactions"))

    def used_today(self, kind):
        return self._server_today()[1][kind] + self.pending_inter[kind]

    def left_today(self, kind):
        return max(0, R.INTERACTIONS[kind]["daily_limit"] - self.used_today(kind))

    def interact(self, kind):
        """'ok' 또는 'limit'."""
        if self.left_today(kind) <= 0:
            return "limit"
        self.pending_inter[kind] += 1
        return "ok"

    # ---------------------------------------------------------------- 서버와 맞추기
    def has_pending(self):
        return self.pending_active > 0 or any(self.pending_inter.values())

    def take_batch(self):
        batch = (self.pending_active, dict(self.pending_inter))
        self.pending_active = 0
        self.pending_inter = R.empty_interactions()
        return batch

    def return_batch(self, batch):
        active, inter = batch
        self.pending_active += active
        for k, v in inter.items():
            self.pending_inter[k] += v

    def apply_me(self, me):
        """서버가 준 새 상태. 일어난 일 목록을 돌려준다: [("level_up", 3), ("evolved", 1)]."""
        before = self.me["character"]
        after = me["character"]
        self.me = me
        events = []
        if after["level"] > before["level"]:
            events.append(("level_up", after["level"]))
        if after["evolution_stage"] > before["evolution_stage"]:
            events.append(("evolved", after["evolution_stage"]))
        return events

    # ---------------------------------------------------------------- 화면에 줄 것
    def view(self):
        ch = self.me["character"]
        school = self.me.get("school") or {}
        today_exp = self._server_today()[0]
        return {
            "nickname": self.me["nickname"],
            "level": ch["level"],
            "stage": ch["evolution_stage"],
            "progress": R.level_progress(ch["total_exp"], ch["level"]),
            "today_exp": today_exp,
            "daily_cap": R.DAILY_EXP_CAP,
            "ranked": self.me.get("ranked", True),
            "sleeping": self.sleeping,
            "animal": school.get("animal") or "duck",
            "color_primary": school.get("color_primary") or "#F4C430",
            "color_secondary": school.get("color_secondary") or "#FFFFFF",
            "school_name": school.get("name"),
        }
