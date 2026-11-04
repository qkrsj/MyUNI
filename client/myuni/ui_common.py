# -*- coding: utf-8 -*-
"""여러 화면이 같이 쓰는 것들 - 글꼴, 색, 말풍선, 뜨는 메뉴, 백그라운드 작업."""
import queue
import threading
import tkinter as tk

from . import config
from . import platform_os as PLAT

BG = "#ffffff"
FG = "#1c1c1f"
MUTED = "#6b6b76"
LINE = "#d9d9e0"
ACCENT = "#2f6fed"
ERROR = "#d1343f"


def font(size=10, bold=False):
    return (PLAT.font_family(), size, "bold" if bold else "normal")


# ---------------------------------------------------------------- 백그라운드 작업
class Worker(object):
    """네트워크처럼 느린 일을 다른 스레드에서 돌리고, 결과는 Tk 스레드에서 받는다.

    Tk 은 자기 스레드 밖에서 부르면 안 된다. 그래서 결과를 큐에 넣고 Tk 쪽에서 꺼낸다.
    """

    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self._pump()

    def run(self, fn, ok=None, err=None):
        def job():
            try:
                self.q.put((ok, fn(), None))
            except Exception as e:                          # noqa: BLE001
                self.q.put((err, None, e))

        threading.Thread(target=job, daemon=True).start()

    def _pump(self):
        try:
            while True:
                cb, res, exc = self.q.get_nowait()
                if cb is None:
                    if exc is not None:
                        config.log("백그라운드 작업 실패: %r" % (exc,))
                    continue
                try:
                    cb(exc if exc is not None else res)
                except Exception:                           # noqa: BLE001
                    config.log_exc("백그라운드 작업 결과 처리 실패")
        except queue.Empty:
            pass
        self.root.after(50, self._pump)


# ---------------------------------------------------------------- 말풍선
class Bubble(object):
    """캐릭터 머리 위에 뜨는 말풍선. 테두리 없는 작은 창이다."""

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.withdraw()
        self.win.configure(bg=LINE)
        self.label = tk.Label(self.win, bg=BG, fg=FG, font=font(9), padx=7, pady=3, justify="center")
        self.label.pack(padx=1, pady=1)
        self._job = None
        self.visible = False

    def show(self, text, anchor_x, bottom_y, ms=None):
        self.label.configure(text=text)
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        self.win.geometry("+%d+%d" % (int(anchor_x - w / 2), int(bottom_y - h)))
        if not self.visible:
            self.win.deiconify()
            PLAT.raise_above(self.win)
            self.visible = True
        self.win.lift()                 # 캐릭터 창보다 위에
        if self._job is not None:
            self.win.after_cancel(self._job)
            self._job = None
        if ms:
            self._job = self.win.after(ms, self.hide)

    def move(self, anchor_x, bottom_y):
        if self.visible:
            w, h = self.win.winfo_width(), self.win.winfo_height()
            self.win.geometry("+%d+%d" % (int(anchor_x - w / 2), int(bottom_y - h)))

    def hide(self):
        self._job = None
        if self.visible:
            self.win.withdraw()
            self.visible = False

    def destroy(self):
        self.win.destroy()


# ---------------------------------------------------------------- 뜨는 메뉴
SEP = None


def popup_menu(root, items, x, y):
    """items: [(글자, 할일 또는 None(회색 글자)), SEP, ...] 를 (x, y) 에 띄운다.

    윈도우는 tk.Menu 를 쓴다. 맥은 NSMenu 가 열린 동안 Tk 타이머가 돌다 죽으므로 직접 그린다.
    """
    if PLAT.NATIVE_MENU:
        m = tk.Menu(root, tearoff=0, font=font(10))
        for it in items:
            if it is SEP:
                m.add_separator()
            else:
                label, fn = it
                m.add_command(label=label, command=fn, state="normal" if fn else "disabled")
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()
        return m
    return DrawnMenu(root, items, x, y)


class DrawnMenu(object):
    """Tk 으로 그린 메뉴 (맥). 항목을 누르거나, 바깥을 누르거나(포커스를 잃거나), Esc 로 닫힌다."""

    def __init__(self, root, items, x, y):
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.configure(bg=LINE)
        body = tk.Frame(self.win, bg=BG, padx=4, pady=4)
        body.pack(padx=1, pady=1)
        for it in items:
            if it is SEP:
                tk.Frame(body, bg=LINE, height=1).pack(fill="x", pady=3)
                continue
            label, fn = it
            lbl = tk.Label(body, text=label, anchor="w", bg=BG, fg=FG if fn else MUTED,
                           font=font(10), padx=10, pady=3)
            lbl.pack(fill="x")
            if fn:
                lbl.bind("<Enter>", lambda e, w=lbl: w.configure(bg="#eef2ff"))
                lbl.bind("<Leave>", lambda e, w=lbl: w.configure(bg=BG))
                lbl.bind("<Button-1>", lambda e, f=fn: self._pick(f))
        self.win.update_idletasks()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        self.win.geometry("+%d+%d" % (min(x, sw - w - 4), min(y, sh - h - 4)))
        PLAT.raise_above(self.win)
        PLAT.activate()
        self.win.focus_force()
        self.win.bind("<FocusOut>", lambda e: self.close())
        self.win.bind("<Escape>", lambda e: self.close())
        self._timeout = self.win.after(20000, self.close)

    def _pick(self, fn):
        self.close()
        fn()

    def alive(self):
        try:
            return bool(self.win.winfo_exists())
        except tk.TclError:
            return False

    def close(self):
        if self.alive():
            self.win.destroy()
