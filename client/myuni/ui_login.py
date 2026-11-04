# -*- coding: utf-8 -*-
"""로그인 · 가입 창."""
import re
import tkinter as tk
from tkinter import ttk

from . import platform_os as PLAT
from . import ui_common as U

NICK_RE = re.compile(r"^[0-9A-Za-z가-힣_]+$")
NO_SCHOOL = "선택 안 함 (나중에 선택)"


class LoginWindow(object):
    """on_done(result) 은 서버 응답 {"token", "me"} 를 받는다. on_close 는 창을 그냥 닫았을 때."""

    def __init__(self, root, api, worker, on_done, on_close):
        self.api, self.worker = api, worker
        self.on_done, self.on_close = on_done, on_close
        self.mode = "login"
        self.schools = None

        self.win = tk.Toplevel(root)
        self.win.title("MyUNi")
        self.win.configure(bg=U.BG)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self._closed)

        body = tk.Frame(self.win, bg=U.BG, padx=26, pady=22)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="MyUNi", bg=U.BG, fg=U.FG, font=U.font(20, True)).pack(anchor="w")
        tk.Label(body, text="우리 학교 친구를 키우고 학교 순위를 올려 보세요",
                 bg=U.BG, fg=U.MUTED, font=U.font(9)).pack(anchor="w", pady=(2, 14))

        tabs = tk.Frame(body, bg=U.BG)
        tabs.pack(fill="x", pady=(0, 12))
        self.tab_login = tk.Label(tabs, text="로그인", bg=U.BG, font=U.font(10, True), pady=6, cursor="hand2")
        self.tab_signup = tk.Label(tabs, text="가입하기", bg=U.BG, font=U.font(10), pady=6, cursor="hand2")
        self.tab_login.pack(side="left", expand=True, fill="x")
        self.tab_signup.pack(side="left", expand=True, fill="x")
        self.tab_login.bind("<Button-1>", lambda e: self._set_mode("login"))
        self.tab_signup.bind("<Button-1>", lambda e: self._set_mode("signup"))

        self.nick = self._field(body, "닉네임")
        self.pw = self._field(body, "비밀번호", show="•")

        self.school_box = tk.Frame(body, bg=U.BG)
        tk.Label(self.school_box, text="학교", bg=U.BG, fg=U.MUTED, font=U.font(9)).pack(anchor="w")
        self.school = ttk.Combobox(self.school_box, state="readonly", values=[NO_SCHOOL], font=U.font(10))
        self.school.current(0)
        self.school.pack(fill="x", pady=(2, 10))

        self.submit = tk.Button(body, text="로그인", command=self._submit, bg=U.ACCENT, fg="white",
                                activebackground=U.ACCENT, activeforeground="white", relief="flat",
                                font=U.font(11, True), pady=6, cursor="hand2")
        self.submit.pack(fill="x", pady=(4, 0))
        self.error = tk.Label(body, text="", bg=U.BG, fg=U.ERROR, font=U.font(9), wraplength=300, justify="left")
        self.error.pack(anchor="w", pady=(8, 0))
        self.notice = tk.Label(
            body, bg=U.BG, fg=U.MUTED, font=U.font(8), justify="left", wraplength=300,
            text="학교는 한 달에 한 번만 바꿀 수 있어요.\n"
                 "기기 고유값은 해시로 바꿔 중복 계정 방지용으로만 쓰며, 원본은 저장하지 않아요.")

        self.win.bind("<Return>", lambda e: self._submit())
        self._set_mode("login")
        # 높이는 정하지 않는다 - 가입 탭은 학교 칸과 안내문만큼 길어진다
        self.win.minsize(360, 0)
        self.win.update_idletasks()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry("+%d+%d" % ((sw - 360) // 2, max(40, sh // 5)))
        PLAT.activate()
        self.win.lift()
        self.nick.focus_force()

    def _field(self, parent, label, **kw):
        tk.Label(parent, text=label, bg=U.BG, fg=U.MUTED, font=U.font(9)).pack(anchor="w")
        e = tk.Entry(parent, font=U.font(11), relief="solid", bd=1, highlightthickness=0, **kw)
        e.pack(fill="x", pady=(2, 10), ipady=4)
        return e

    def _set_mode(self, mode):
        self.mode = mode
        login = mode == "login"
        self.tab_login.configure(fg=U.FG if login else U.MUTED, font=U.font(10, login))
        self.tab_signup.configure(fg=U.MUTED if login else U.FG, font=U.font(10, not login))
        self.submit.configure(text="로그인" if login else "가입하고 시작하기")
        self.error.configure(text="")
        if login:
            self.school_box.pack_forget()
            self.notice.pack_forget()
        else:
            self.school_box.pack(fill="x", before=self.submit)
            self.notice.pack(anchor="w", pady=(10, 0))
            if self.schools is None:
                self._load_schools()

    def _load_schools(self):
        def done(res):
            if isinstance(res, Exception):
                self.error.configure(text="학교 목록을 불러오지 못했어요. 서버 연결을 확인해 주세요.")
                return
            self.schools = res
            self.school.configure(values=[NO_SCHOOL] + [s["name"] for s in res])
        self.worker.run(self.api.schools, done, done)

    def _validate(self):
        nick = self.nick.get().strip()
        pw = self.pw.get()
        if not (2 <= len(nick) <= 16):
            return "닉네임은 2~16자로 입력해 주세요."
        if self.mode == "signup" and not NICK_RE.match(nick):
            return "닉네임에는 한글, 영문, 숫자, _ 만 쓸 수 있어요."
        if not pw:
            return "비밀번호를 입력해 주세요."
        if self.mode == "signup" and len(pw) < 8:
            return "비밀번호는 8자 이상이어야 해요."
        return None

    def _selected_school_id(self):
        i = self.school.current()
        if i <= 0 or not self.schools:
            return None
        return self.schools[i - 1]["id"]

    def _submit(self):
        problem = self._validate()
        if problem:
            self.error.configure(text=problem)
            return
        self.submit.configure(state="disabled")
        self.error.configure(text="")
        nick, pw = self.nick.get().strip(), self.pw.get()
        if self.mode == "login":
            call = lambda: self.api.login(nick, pw)                          # noqa: E731
        else:
            sid = self._selected_school_id()
            call = lambda: self.api.signup(nick, pw, sid)                    # noqa: E731

        def done(res):
            self.submit.configure(state="normal")
            if isinstance(res, Exception):
                self.error.configure(text=getattr(res, "message", None) or str(res))
                return
            self.win.destroy()
            self.on_done(res)
        self.worker.run(call, done, done)

    def _closed(self):
        self.win.destroy()
        self.on_close()
