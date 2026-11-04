# -*- coding: utf-8 -*-
"""윈도우에서만 쓰는 것들.

투명 배경은 `-transparentcolor` 로 **특정 색**을 뚫는다. 그 색으로 칠한 픽셀은
보이지도 않고 클릭도 그대로 아래로 지나간다. 그래서 도트 둘레를 따로 처리할 일이 없다.
"""
import ctypes
import os

from .platform_base import (NATIVE_MENU, NEEDS_HIT_TRACKING, RIGHT_CLICK,  # noqa: F401
                            SpriteView, activate, before_tk, bind_right, hide_from_dock,
                            mac_address_fallback, missing_requirement)

MUTEX_NAME = "myuni-single-instance"


def transparent_window(win, key):
    win.attributes("-topmost", True)
    win.attributes("-transparentcolor", key)
    win.configure(bg=key)
    return key


def raise_above(win):
    """항상 위로. 테두리 없는 창에 -topmost 를 걸면 (0, 0) 으로 튀는 일이 있어 자리를 되돌린다."""
    try:
        win.update_idletasks()
        before = (win.winfo_x(), win.winfo_y())
        win.attributes("-topmost", True)
        win.update_idletasks()
        if (win.winfo_x(), win.winfo_y()) != before:
            win.geometry("+%d+%d" % before)
    except Exception:                                       # noqa: BLE001
        pass


def work_area(fallback_w, fallback_h):
    """작업표시줄을 뺀 주 화면 영역 (SPI_GETWORKAREA)."""
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

        r = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0):
            return r.left, r.top, r.right, r.bottom
    except Exception:                                       # noqa: BLE001
        pass
    return 0, 0, fallback_w, fallback_h


def idle_seconds():
    """GetLastInputInfo - 이 세션의 마지막 키보드 · 마우스 입력."""
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            # 둘 다 49.7일마다 한 바퀴 도는 32비트 값이라 차이도 32비트로 잘라 본다
            now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
            return ((now - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:                                       # noqa: BLE001
        pass
    return 0.0


def single_lock(data_dir_):
    """이름 있는 뮤텍스. 프로세스가 어떻게 죽든 커널이 놓아준다."""
    from ctypes import wintypes

    ERROR_ALREADY_EXISTS = 183
    k32 = ctypes.windll.kernel32
    k32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
    k32.CreateMutexW.restype = wintypes.HANDLE
    # Local\ : 같은 로그인 세션 안에서만. 여러 사람이 쓰는 PC 에서 남의 것까지 막지 않는다.
    h = k32.CreateMutexW(None, False, "Local\\" + MUTEX_NAME)
    if not h:
        return None, False
    return h, k32.GetLastError() == ERROR_ALREADY_EXISTS


def single_release(handle):
    try:
        ctypes.windll.kernel32.CloseHandle(handle)
    except Exception:                                       # noqa: BLE001
        pass


def data_dir(app_name):
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, app_name)
    os.makedirs(d, exist_ok=True)
    return d


def machine_raw():
    """레지스트리의 MachineGuid (64비트 보기로 읽는다)."""
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                           winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        raw = winreg.QueryValueEx(k, "MachineGuid")[0]
        winreg.CloseKey(k)
        return raw
    except Exception:                                       # noqa: BLE001
        return None


def dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:                                       # noqa: BLE001
        pass


def font_family():
    return "맑은 고딕"


def already_running_hint():
    return ("작업표시줄 오른쪽 끝의 '숨겨진 아이콘 표시'(^) 를 눌러\n"
            "MyUNi 아이콘을 찾아보세요.")
