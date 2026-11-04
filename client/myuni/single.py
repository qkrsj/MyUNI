# -*- coding: utf-8 -*-
"""한 번에 하나만 돌게 한다.

트레이 아이콘은 숨겨진 아이콘 안으로 들어가기 쉬워서, 켜져 있는 걸 모르고 또 누르기 쉽다.
그러면 캐릭터가 두 마리가 되고 두 클라이언트가 각자 서버로 보낸다.
윈도우는 이름 있는 뮤텍스, 맥은 flock - 프로세스가 어떻게 죽든 커널이 놓아준다.
"""
from . import platform_os as PLAT

_HANDLE = None


def acquire(data_dir):
    global _HANDLE
    _HANDLE, taken = PLAT.single_lock(data_dir)
    return _HANDLE, taken


def release():
    global _HANDLE
    h, _HANDLE = _HANDLE, None
    if h is not None:
        PLAT.single_release(h)


def tell_user():
    try:
        import tkinter as tk
        from tkinter import messagebox
        PLAT.before_tk()
        r = tk.Tk()
        r.withdraw()
        messagebox.showinfo("MyUNi", "이미 실행 중입니다.\n\n" + PLAT.already_running_hint())
        r.destroy()
    except Exception:                                       # noqa: BLE001
        pass
