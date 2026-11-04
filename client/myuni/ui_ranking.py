# -*- coding: utf-8 -*-
"""이번 주 랭킹 창 (학교 / 개인)."""
import tkinter as tk

from . import platform_os as PLAT
from . import ui_common as U

ANIMAL_KR = {"tiger": "호랑이", "eagle": "독수리", "duck": "오리", "bear": "곰", "lion": "사자",
             "owl": "부엉이", "dragon": "용", "horse": "말", "magpie": "까치", "crane": "학"}


class RankingWindow(object):
    def __init__(self, root, api, worker, my_nickname=None):
        self.api, self.worker, self.me = api, worker, my_nickname
        self.win = tk.Toplevel(root)
        self.win.title("MyUNi 랭킹")
        self.win.configure(bg=U.BG)
        self.win.geometry("380x520")

        head = tk.Frame(self.win, bg=U.BG, padx=18, pady=14)
        head.pack(fill="x")
        self.title = tk.Label(head, text="이번 주 랭킹", bg=U.BG, fg=U.FG, font=U.font(15, True))
        self.title.pack(anchor="w")
        tabs = tk.Frame(head, bg=U.BG)
        tabs.pack(fill="x", pady=(10, 0))
        self.tabs = {}
        for key, label in (("schools", "학교"), ("users", "개인")):
            t = tk.Label(tabs, text=label, bg=U.BG, font=U.font(10), pady=5, cursor="hand2")
            t.pack(side="left", expand=True, fill="x")
            t.bind("<Button-1>", lambda e, k=key: self.show(k))
            self.tabs[key] = t

        self.list = tk.Frame(self.win, bg=U.BG, padx=18)
        self.list.pack(fill="both", expand=True)
        PLAT.activate()
        self.win.lift()
        self.show("schools")

    def show(self, which):
        for k, t in self.tabs.items():
            t.configure(fg=U.FG if k == which else U.MUTED, font=U.font(10, k == which))
        self._message("불러오는 중...")
        call = self.api.school_rankings if which == "schools" else self.api.user_rankings

        def done(res):
            if not self.win.winfo_exists():
                return
            if isinstance(res, Exception):
                self._message(getattr(res, "message", None) or "랭킹을 불러오지 못했어요.")
                return
            self.title.configure(text="이번 주 랭킹 · %s" % res["week"])
            self._fill(which, res["entries"])
        self.worker.run(call, done, done)

    def _clear(self):
        for c in self.list.winfo_children():
            c.destroy()

    def _message(self, text):
        self._clear()
        tk.Label(self.list, text=text, bg=U.BG, fg=U.MUTED, font=U.font(10)).pack(pady=30)

    def _fill(self, which, entries):
        self._clear()
        if not entries:
            self._message("아직 이번 주 기록이 없어요.")
            return
        for e in entries[:30]:
            row = tk.Frame(self.list, bg=U.BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="%d" % e["rank"], width=3, anchor="e", bg=U.BG, fg=U.MUTED,
                     font=U.font(10, True)).pack(side="left")
            if which == "schools":
                name = "%s  (%s)" % (e["school"]["name"], ANIMAL_KR.get(e["school"]["animal"], e["school"]["animal"]))
                sub = "%d명" % e["members"]
                mine = False
            else:
                name = e["nickname"]
                sub = e["school_name"] or "학교 없음"
                mine = e["nickname"] == self.me
            tk.Label(row, text=name, anchor="w", bg=U.BG, fg=U.ACCENT if mine else U.FG,
                     font=U.font(10, mine)).pack(side="left", padx=(8, 4))
            tk.Label(row, text=sub, anchor="w", bg=U.BG, fg=U.MUTED, font=U.font(9)).pack(side="left")
            tk.Label(row, text="%d" % e["score"], anchor="e", bg=U.BG, fg=U.FG,
                     font=U.font(10)).pack(side="right")
