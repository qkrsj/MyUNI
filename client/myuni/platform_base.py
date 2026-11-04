# -*- coding: utf-8 -*-
"""플랫폼마다 다른 것들의 **계약**과, 어느 쪽도 아닐 때(리눅스 개발용) 쓸 기본 구현.

부르는 쪽은 `from . import platform_os as PLAT` 하나만 본다.

    transparent_window(win, key)   창을 투명하게. 도트 위젯 배경색을 돌려준다
    raise_above(win)               항상 위로
    SpriteView                     투명 창 안에서 도트(PIL RGBA)를 그린다
    work_area(w, h)                작업표시줄 · 독을 뺀 주 화면 영역 (x1, y1, x2, y2)
    idle_seconds()                 마지막 키보드 · 마우스 입력 뒤로 흐른 초
    machine_raw()                  기기 고유값 원본 (None 이면 MAC 주소로 간다)
    data_dir(app)                  설정 · 로그인 정보를 둘 폴더
    single_lock / single_release   중복 실행 막기
    hide_from_dock / activate      맥: 독에서 숨기기, 우리 창 앞으로

여기 구현은 "죽지는 않는다" 수준이다. 리눅스에서 띄우면 도트가 네모난 판 위에 뜬다.
"""
import os
import uuid

# 커서를 좇아가며 클릭 통과를 켜고 꺼야 하는가 (맥). 윈도우는 투명색 자리가 알아서 통과한다.
NEEDS_HIT_TRACKING = False

# 오른쪽 클릭 이벤트. 맥 Tk 은 오른쪽이 2번이다.
RIGHT_CLICK = ("<Button-3>",)

# tk.Menu 를 써도 되는가. 맥에서는 NSMenu 가 열린 동안 Tk 의 after 타이머가 돌다 죽는다.
NATIVE_MENU = True


def bind_right(widget, fn):
    for seq in RIGHT_CLICK:
        widget.bind(seq, fn)


# ---------------------------------------------------------------- 창
def transparent_window(win, key):
    try:
        win.attributes("-topmost", True)
    except Exception:                                       # noqa: BLE001
        pass
    win.configure(bg=key)
    return key


def raise_above(win):
    try:
        win.attributes("-topmost", True)
    except Exception:                                       # noqa: BLE001
        pass


class SpriteView(object):
    """창 하나에 도트를 그린다. 기본 구현은 투명색 방식 (윈도우와 같다).

    도트는 PIL RGBA 로 받는다. 알파가 반 넘게 남은 픽셀만 칠하고 나머지는 투명색으로
    채운다 - 투명색 방식은 반투명이 없어서, 가장자리를 흐리게 두면 투명색 테두리가 남는다.
    """

    def __init__(self, win, key, w, h):
        import tkinter as tk

        self.win, self.key, self.w, self.h = win, key, w, h
        self._mask = None
        self.widget = tk.Label(win, bd=0, highlightthickness=0, bg=key,
                               width=w, height=h, anchor="nw")
        self.widget.pack()
        self._keep = None

    def frames(self, images):
        """PIL RGBA 목록 -> 이 플랫폼이 그릴 수 있는 것 목록."""
        from PIL import Image, ImageTk

        bg = Image.new("RGB", (self.w, self.h), self.key)
        out = []
        for im in images:
            canvas = bg.copy()
            alpha = im.split()[3].point(lambda a: 255 if a >= 128 else 0)
            canvas.paste(im.convert("RGB"), (0, 0), alpha)
            out.append(_TkFrame(ImageTk.PhotoImage(canvas), alpha))
        return out

    def show(self, frame):
        self._mask = frame.mask
        self.widget.configure(image=frame.photo)

    def solid_at(self, lx, ly):
        """창 안 (lx, ly) 에 도트가 있는가."""
        m = self._mask
        if m is None or not (0 <= lx < m.width and 0 <= ly < m.height):
            return False
        return m.getpixel((lx, ly)) > 0

    def update_hit(self, lx, ly):
        """맥에서만 할 일이 있다 (커서 밑이 비었으면 클릭을 통과시킨다)."""

    def destroy(self):
        pass


class _TkFrame(object):
    __slots__ = ("photo", "mask")

    def __init__(self, photo, mask):
        self.photo, self.mask = photo, mask


# ---------------------------------------------------------------- 화면 · 입력
def work_area(fallback_w, fallback_h):
    return 0, 0, fallback_w, fallback_h


def idle_seconds():
    """알 수 없으면 0 (늘 쓰는 중으로 친다)."""
    return 0.0


# ---------------------------------------------------------------- 프로세스
def single_lock(data_dir_):
    """(잠금, 이미돌고있음). 잠금을 못 걸었다고 게임을 막지는 않는다."""
    path = os.path.join(data_dir_, "running.pid")
    try:
        if os.path.exists(path):
            with open(path) as f:
                pid = int((f.read() or "0").strip() or 0)
            if pid and pid != os.getpid():
                try:
                    os.kill(pid, 0)
                    return None, True
                except OSError:
                    pass
        with open(path, "w") as f:
            f.write(str(os.getpid()))
        return path, False
    except Exception:                                       # noqa: BLE001
        return None, False


def single_release(handle):
    try:
        os.remove(handle)
    except (OSError, TypeError):
        pass


def data_dir(app_name):
    d = os.path.join(os.path.expanduser("~"), "." + app_name.lower())
    os.makedirs(d, exist_ok=True)
    return d


def machine_raw():
    try:
        with open("/etc/machine-id") as f:
            return f.read().strip() or None
    except OSError:
        return None


def mac_address_fallback():
    """기기 고유값을 못 읽었을 때. 바뀔 수 있어서 최후의 수단이다."""
    return "mac-%012x" % uuid.getnode()


def dpi_aware():
    pass


def before_tk():
    pass


def hide_from_dock():
    pass


def activate():
    pass


def missing_requirement():
    """없어서 못 도는 것이 있으면 사람에게 보여줄 문장. 없으면 None."""
    return None


def font_family():
    return "TkDefaultFont"


def already_running_hint():
    return "이미 떠 있는 MyUNi 를 찾아보세요."
