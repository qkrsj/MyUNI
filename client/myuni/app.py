# -*- coding: utf-8 -*-
"""MyUNi 클라이언트의 시작점. 화면 · 게임 로직 · 서버 통신을 이어 붙인다.

    [표시 층]   overlay.Pet       화면 아래를 걷는 캐릭터
    [게임 로직] game.Game         활동 시간, 자리 비움, 상호작용 횟수
    [서버 통신] api.Api           로그인, 동기화, 랭킹 (ui_common.Worker 로 다른 스레드에서)
"""
import random
import sys
import tkinter as tk
from tkinter import messagebox

from common import rules as R
from common.version import VERSION, compatible

from . import config
from . import platform_os as PLAT
from . import single, tray
from .api import Api, ApiError
from .game import Game
from .overlay import Pet
from .ui_common import SEP, Worker, popup_menu
from .ui_login import LoginWindow
from .ui_ranking import RankingWindow

MINUTE_MS = 60_000
INTERACT_SYNC_DELAY_MS = 2_000
GREETINGS = ("안녕!", "헤헤", "오늘도 화이팅!", "같이 놀자!")


class App(object):
    def __init__(self):
        PLAT.dpi_aware()
        PLAT.before_tk()
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("MyUNi")
        PLAT.hide_from_dock()

        self.api = Api()
        self.worker = Worker(self.root)
        self.game = None
        self.pet = None
        self.tray = None
        self.syncing = False
        self._minute_job = None
        self._sync_job = None
        self.login_window = None

    # ---------------------------------------------------------------- 시작
    def start(self):
        problem = PLAT.missing_requirement()
        if problem:
            messagebox.showwarning("MyUNi", problem)
        self.tray = tray.make(self)
        if self.tray is not None:
            try:
                self.tray.start()
            except Exception:                               # noqa: BLE001
                config.log_exc("트레이를 못 띄웠습니다")
                self.tray = None

        session = config.load_session()
        if session is None:
            self.show_login()
        else:
            # 저장해 둔 상태로 바로 띄우고, 서버 확인은 뒤에서 한다 (오프라인이어도 켜진다)
            self.api.token = session["token"]
            self.start_game(session["me"])
            self.worker.run(self.api.me, self._refreshed_me, self._sync_failed)
        self.worker.run(self.api.version, self._check_version)

    def _check_version(self, server_version):
        if isinstance(server_version, Exception) or compatible(server_version):
            return
        messagebox.showinfo("MyUNi", "새 버전(%s)이 나왔습니다. 지금 버전: %s\n새 버전을 받아 주세요."
                            % (server_version, VERSION))

    def show_login(self):
        if self.login_window is not None:
            return
        self.login_window = LoginWindow(self.root, self.api, self.worker,
                                        on_done=self._logged_in, on_close=self._login_closed)

    def _logged_in(self, res):
        self.login_window = None
        config.save_session(res["token"], res["me"])
        self.start_game(res["me"])

    def _login_closed(self):
        self.login_window = None
        if self.game is None:
            self.quit()

    def start_game(self, me):
        self.stop_game()
        self.game = Game(me)
        self.pet = Pet(self.root, self._pet_clicked, self.open_menu)
        self.pet.set_view(self.game.view())
        self._minute_job = self.root.after(MINUTE_MS, self._minute)
        if not me.get("ranked", True):
            self.pet.say("이 기기에서는 다른 계정이 랭킹에 반영돼요", 4000)

    def stop_game(self):
        for job in (self._minute_job, self._sync_job):
            if job is not None:
                self.root.after_cancel(job)
        self._minute_job = self._sync_job = None
        if self.pet is not None:
            self.pet.destroy()
        self.pet = None
        self.game = None

    # ---------------------------------------------------------------- 게임 루프
    def _minute(self):
        self._minute_job = self.root.after(MINUTE_MS, self._minute)
        if self.game is None:
            return
        was_sleeping = self.game.sleeping
        due = self.game.tick_minute(PLAT.idle_seconds())
        if self.game.sleeping != was_sleeping:
            self.pet.set_view(self.game.view())
        if due:
            self.sync()

    def sync(self):
        self._sync_job = None
        if self.game is None or self.syncing or not self.game.has_pending():
            return
        self.syncing = True
        game = self.game
        batch = game.take_batch()

        def ok(res):
            self.syncing = False
            if self.game is not game:
                return
            events = game.apply_me(res["me"])
            config.save_session(self.api.token, res["me"])
            self.pet.set_view(game.view())
            for kind, value in events:
                if kind == "evolved":
                    self.pet.react()
                    self.pet.say("진화했어요! (%s)" % R.EVOLUTION_STAGES[value]["name"], 4000)
                elif kind == "level_up":
                    self.pet.react()
                    self.pet.say("레벨 업! Lv.%d" % value, 3000)

        def err(e):
            self.syncing = False
            if self.game is game:
                game.return_batch(batch)          # 다음에 다시 보낸다
            self._sync_failed(e)

        self.worker.run(lambda: self.api.sync(*batch), ok, err)

    def _refreshed_me(self, me):
        if self.game is not None:
            self.game.apply_me(me)
            config.save_session(self.api.token, me)
            self.pet.set_view(self.game.view())

    def _sync_failed(self, e):
        if isinstance(e, ApiError) and e.status == 401:
            self.logout(remote=False)
            messagebox.showinfo("MyUNi", e.message)
        else:
            config.log("동기화 실패: %r" % (e,))

    # ---------------------------------------------------------------- 상호작용
    def _pet_clicked(self):
        if self.game and self.game.sleeping:
            self.pet.say("쿨쿨...", 1500)
        else:
            self.pet.say(random.choice(GREETINGS), 1500)

    def interact(self, kind):
        if self.game is None:
            return
        if self.game.interact(kind) == "limit":
            self.pet.say("오늘은 배불러요" if kind == "feed" else "오늘은 많이 놀았어요")
            return
        self.pet.react()
        self.pet.say("냠냠!" if kind == "feed" else "신난다!")
        if self._sync_job is not None:
            self.root.after_cancel(self._sync_job)
        self._sync_job = self.root.after(INTERACT_SYNC_DELAY_MS, self.sync)

    def menu_items(self):
        if self.game is None:
            return [("로그인", self.show_login), SEP, ("MyUNi 종료", self.quit)]
        v = self.game.view()
        head = "%s · Lv.%d" % (v["nickname"], v["level"])
        if v["school_name"]:
            head += " · " + v["school_name"]
        items = [(head, None), ("오늘 경험치 %d / %d" % (v["today_exp"], v["daily_cap"]), None)]
        if not v["ranked"]:
            items.append(("이 기기의 랭킹 반영 계정이 아니에요", None))
        items.append(SEP)
        for kind, rule in R.INTERACTIONS.items():
            items.append(("%s (오늘 %d번 남음)" % (rule["label"], self.game.left_today(kind)),
                          lambda k=kind: self.interact(k)))
        items += [SEP, ("랭킹 보기", self.show_ranking), SEP,
                  ("로그아웃", self.logout), ("MyUNi 종료", self.quit)]
        return items

    def open_menu(self, x, y):
        popup_menu(self.root, self.menu_items(), x, y)

    def tray_action(self, key):
        if key == "menu":
            x, y = self.root.winfo_pointerxy()
            self.open_menu(x, y - 10)
        elif key == "ranking":
            self.show_ranking()
        elif key == "logout":
            self.logout()
        elif key == "quit":
            self.quit()

    def show_ranking(self):
        RankingWindow(self.root, self.api, self.worker,
                      self.game.me["nickname"] if self.game else None)

    # ---------------------------------------------------------------- 끝내기
    def _flush(self):
        """남은 활동을 보내 본다. 실패해도 끝낸다 (하루 상한 안에서 조금 잃을 뿐이다)."""
        if self.game is not None and self.game.has_pending() and self.api.token:
            try:
                self.api.sync(*self.game.take_batch())
            except Exception:                               # noqa: BLE001
                pass

    def logout(self, remote=True):
        self._flush()
        if remote and self.api.token:
            token_api = Api(token=self.api.token)
            self.worker.run(token_api.logout)
        self.api.token = None
        config.clear_session()
        self.stop_game()
        self.show_login()

    def quit(self):
        self._flush()
        self.stop_game()
        if self.tray is not None:
            self.tray.stop()
        self.root.quit()

    def run(self):
        self.root.after(0, self.start)
        self.root.mainloop()


def main():
    handle, running = single.acquire(config.data_dir())
    if running:
        single.tell_user()
        sys.exit(0)
    try:
        config.log("시작 %s (%s, 서버 %s)" % (VERSION, PLAT.NAME, config.SERVER_URL))
        App().run()
    except Exception:                                       # noqa: BLE001
        config.log_exc("치명적 오류")
        raise
    finally:
        single.release()
