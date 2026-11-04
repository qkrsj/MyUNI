# -*- coding: utf-8 -*-
"""트레이 아이콘 (윈도우). 맥은 tray_mac.py.

pystray 는 자기 스레드에서 돈다. 거기서 Tk 을 부르면 안 되므로 눌린 항목만 적어 두고
Tk 쪽(_pump)에서 꺼내 실행한다. 메뉴에 무엇이 들어가는지는 app.App.menu_items() 한 곳에 있다.
"""
import queue
import sys
import threading

from . import config, sprites


def make(app):
    if sys.platform == "darwin":
        try:
            from .tray_mac import Tray as MacTray
            return MacTray(app)
        except Exception:                                   # noqa: BLE001
            config.log_exc("메뉴 막대 아이콘을 못 만들었습니다")
            return None
    try:
        import pystray                                      # noqa: F401
    except Exception:                                       # noqa: BLE001
        return None
    return Tray(app)


class Tray(object):
    def __init__(self, app):
        self.app = app
        self.icon = None
        self.q = queue.Queue()
        self._job = None

    def start(self):
        import pystray

        def item(label, key):
            return pystray.MenuItem(label, lambda _i, _m: self.q.put(key))

        self.icon = pystray.Icon(
            "MyUNi", sprites.icon(64), "MyUNi",
            menu=pystray.Menu(
                item("메뉴 열기", "menu"),
                item("랭킹 보기", "ranking"),
                pystray.Menu.SEPARATOR,
                item("로그아웃", "logout"),
                item("MyUNi 종료", "quit")))
        threading.Thread(target=self.icon.run, daemon=True).start()
        self._pump()

    def _pump(self):
        try:
            while True:
                key = self.q.get_nowait()
                self.app.tray_action(key)
        except queue.Empty:
            pass
        except Exception:                                   # noqa: BLE001
            config.log_exc("트레이 처리 실패")
        self._job = self.app.root.after(100, self._pump)

    def stop(self):
        if self._job is not None:
            try:
                self.app.root.after_cancel(self._job)
            except Exception:                               # noqa: BLE001
                pass
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:                               # noqa: BLE001
                pass
            self.icon = None
