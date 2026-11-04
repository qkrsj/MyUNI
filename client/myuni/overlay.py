# -*- coding: utf-8 -*-
"""[표시 층] 화면 아래를 걸어 다니는 캐릭터.

캐릭터 크기만 한 투명 창 하나를 작업표시줄 바로 위에서 옮긴다. 화면 전체를 덮는 창이
아니라서, 캐릭터가 없는 자리는 원래대로 클릭된다.

    윈도우  투명색으로 칠한 자리는 클릭이 그냥 지나간다.
    맥      커서 밑에 도트가 있는지 보고 클릭 통과를 켜고 끈다 (SpriteView.update_hit).

나중에 위젯 · 트레이 방식으로 바꿀 때는 이 파일만 바꾸면 된다.
게임 로직과는 set_view(), say(), react() 로만 이야기한다.
"""
import random
import time
import tkinter as tk

from . import platform_os as PLAT
from . import sprites
from .ui_common import Bubble

KEY = "#ff00fe"           # 윈도우 투명색. 도트에 이 색이 들어가면 그 자리가 뚫린다.
TICK_MS = 40              # 25fps
WALK_SPEED = 38.0         # 초당 px
FRAME_SEC = {"walk": 0.16, "stand": 0.9, "sleep": 0.8, "jump": 1.0}


class Pet(object):
    def __init__(self, root, on_left_click, on_right_click):
        self.root = root
        self.on_left_click = on_left_click
        self.on_right_click = on_right_click

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        bg = PLAT.transparent_window(self.win, KEY)
        self.sprite = PLAT.SpriteView(self.win, bg, sprites.WIDTH, sprites.HEIGHT)
        w = self.sprite.widget
        w.bind("<Button-1>", self._left)
        PLAT.bind_right(w, self._right)
        w.bind("<Enter>", lambda e: self._hover(True))
        w.bind("<Leave>", lambda e: self._hover(False))

        self.bubble = Bubble(root)
        self.view = None
        self._look = None
        self._frames = {}
        self._sprite_top = 0

        self.area = PLAT.work_area(root.winfo_screenwidth(), root.winfo_screenheight())
        self._area_at = time.monotonic()
        self.x = float(random.randint(self.area[0] + 50, max(self.area[0] + 51, self.area[2] - 150)))
        self.facing = random.choice((1, -1))
        self.mode, self.mode_until = "stand", 0.0
        self.jump_until = 0.0
        self.hovering = False
        self.anim_t = 0.0
        self.last = time.monotonic()
        self._placed = None
        self._shown = None
        self._message_until = 0.0
        self._raised_at = 0.0

        self._place()
        self.win.after(100, lambda: PLAT.raise_above(self.win))
        self._job = self.win.after(TICK_MS, self._tick)

    # ---------------------------------------------------------------- 밖에서 부르는 것
    def set_view(self, view):
        self.view = view
        look = (view["stage"], view["animal"], view["color_primary"], view["color_secondary"])
        if look != self._look:
            self._look = look
            raw = sprites.build_frames(*look)
            self._frames = {k: self.sprite.frames(v) for k, v in raw.items()}
            # 말풍선은 창 위가 아니라 도트 머리 위에 띄운다 (창 위쪽은 비어 있다)
            self._sprite_top = min((im.getbbox() or (0, 0, 0, 0))[1]
                                   for ims in raw.values() for im in ims)
            self._shown = None
        if self.hovering:
            self._show_info()

    def say(self, text, ms=2200):
        self._message_until = time.monotonic() + ms / 1000.0
        self.bubble.show(text, *self._bubble_anchor(), ms=ms)

    def react(self):
        """통통 뛴다 (클릭, 먹이 주기 등)."""
        self.jump_until = time.monotonic() + 0.4

    def destroy(self):
        try:
            self.win.after_cancel(self._job)
        except Exception:                                   # noqa: BLE001
            pass
        self.sprite.destroy()
        self.bubble.destroy()
        self.win.destroy()

    # ---------------------------------------------------------------- 마우스
    def _left(self, _e):
        self.react()
        self.on_left_click()

    def _right(self, e):
        self.on_right_click(e.x_root, e.y_root)

    def _hover(self, on):
        self.hovering = on
        if on:
            self._show_info()
        elif time.monotonic() >= self._message_until:
            self.bubble.hide()

    def _show_info(self):
        if not self.view or time.monotonic() < self._message_until:
            return
        v = self.view
        self.bubble.show("%s  Lv.%d\n오늘 %d / %d" % (v["nickname"], v["level"], v["today_exp"], v["daily_cap"]),
                         *self._bubble_anchor())

    # ---------------------------------------------------------------- 움직임
    def _bubble_anchor(self):
        return self.x + sprites.WIDTH / 2, self._y() + self._sprite_top - 4

    def _y(self):
        return self.area[3] - sprites.HEIGHT

    def _place(self):
        pos = (int(self.x), int(self._y()))
        if pos != self._placed:
            self.win.geometry("%dx%d+%d+%d" % (sprites.WIDTH, sprites.HEIGHT, pos[0], pos[1]))
            self._placed = pos

    def _choose_mode(self, now):
        if self.mode == "walk":
            self.mode, self.mode_until = "stand", now + random.uniform(2, 6)
        else:
            if random.random() < 0.4:
                self.facing = -self.facing
            self.mode, self.mode_until = "walk", now + random.uniform(3, 9)

    def _tick(self):
        try:
            self._step()
        except Exception:                                   # noqa: BLE001
            from . import config
            config.log_exc("캐릭터 움직임 오류")
        self._job = self.win.after(TICK_MS, self._tick)

    def _step(self):
        now = time.monotonic()
        dt = min(0.2, now - self.last)
        self.last = now

        if now - self._area_at > 2.0:            # 작업표시줄 · 해상도가 바뀌었을 수 있다
            self.area = PLAT.work_area(self.root.winfo_screenwidth(), self.root.winfo_screenheight())
            self._area_at = now
        if now - self._raised_at > 10.0:         # 나중에 뜬 '항상 위' 창에 가려지지 않게
            PLAT.raise_above(self.win)
            if self.bubble.visible:
                PLAT.raise_above(self.bubble.win)       # 말풍선은 캐릭터보다 위에
            self._raised_at = now

        sleeping = bool(self.view and self.view["sleeping"])
        if not sleeping and not self.hovering:
            if now > self.mode_until:
                self._choose_mode(now)
            if self.mode == "walk":
                speed = WALK_SPEED * (0.4 if self._look and self._look[0] == 0 else 1.0)
                self.x += self.facing * speed * dt
                lo, hi = self.area[0] + 4, self.area[2] - sprites.WIDTH - 4
                if self.x < lo:
                    self.x, self.facing = lo, 1
                elif self.x > hi:
                    self.x, self.facing = hi, -1
        self._place()
        self.bubble.move(*self._bubble_anchor())

        if now < self.jump_until:
            pose = "jump"
        elif sleeping:
            pose = "sleep"
        elif self.mode == "walk" and not self.hovering:
            pose = "walk"
        else:
            pose = "stand"
        frames = self._frames.get((pose, self.facing))
        if frames:
            self.anim_t += dt
            idx = int(self.anim_t / FRAME_SEC[pose]) % len(frames)
            if (pose, self.facing, idx) != self._shown:
                self.sprite.show(frames[idx])
                self._shown = (pose, self.facing, idx)

        if PLAT.NEEDS_HIT_TRACKING:
            px, py = self.win.winfo_pointerxy()
            lx, ly = px - self._placed[0], py - self._placed[1]
            inside = 0 <= lx < sprites.WIDTH and 0 <= ly < sprites.HEIGHT
            self.sprite.update_hit(lx if inside else None, ly if inside else None)
