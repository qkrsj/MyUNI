# -*- coding: utf-8 -*-
"""맥에서만 쓰는 것들. pyobjc 가 있어야 한다.

## 투명 배경
맥 Tk 에는 `-transparentcolor` 가 없다. 대신 `-transparent` 로 창 배경 전체를 투명하게
만든다. 그런데 Tk 8.6 aqua 는 배경이 systemTransparent 인 위젯에 그림(photo image)을
올리면 그리지 않는다. 그래서 창 · 좌표 · 마우스는 Tk 이 맡고, **도트는 CALayer 가 그린다**.
(색빼기가 아니라 진짜 알파라 가장자리도 깔끔하다.)

## 클릭 통과
Tk 창은 알파 0 인 자리도 클릭을 먹는다. 통과시키는 수단은 창 전체에 걸리는
`ignoresMouseEvents` 뿐이라, 커서 밑에 도트가 있는지 보고 그때그때 켜고 끈다 (update_hit).

## 메뉴
NSMenu 가 열리면 macOS 가 중첩 런루프를 돌리고, 그동안 Tk 의 after 타이머가 돌면서
파이썬이 죽는다. 그래서 메뉴는 Tk 으로 직접 그린다 (NATIVE_MENU = False).

이 방식은 poketdesktop 이 맥에서 겪고 정리한 내용을 따른 것이다.
"""
import ctypes
import os
import subprocess

from .platform_base import mac_address_fallback            # noqa: F401

APP_NAME = "MyUNi"
NEEDS_HIT_TRACKING = True
RIGHT_CLICK = ("<Button-2>", "<Button-3>", "<Control-Button-1>")
NATIVE_MENU = False

try:
    import objc                                             # noqa: F401
    import AppKit
    import Foundation
    import Quartz
    from Quartz import CALayer, CATransaction
    _ok = True
except Exception:                                           # noqa: BLE001
    _ok = False

_CS = Quartz.CGColorSpaceCreateDeviceRGB() if _ok else None


def bind_right(widget, fn):
    for seq in RIGHT_CLICK:
        widget.bind(seq, fn)


def missing_requirement():
    if _ok:
        return None
    return ("맥에서 돌리려면 pyobjc 가 필요합니다.\n\n"
            "  pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz\n\n"
            "(없으면 캐릭터가 네모난 판 위에 뜹니다.)")


# ---------------------------------------------------------------- NSWindow 찾기
_getview = None


def _root_control():
    """Tk 이 내보내는 함수로 Tk 창 -> NSView 를 얻는다 (winfo_id 는 NSView 가 아니다)."""
    global _getview
    if _getview is None:
        _getview = False
        try:
            lib = ctypes.CDLL(None)
            for name in ("TkMacOSXGetRootControl", "Tk_MacOSXGetNSViewForDrawable"):
                fn = getattr(lib, name, None)
                if fn is not None:
                    fn.restype = ctypes.c_void_p
                    fn.argtypes = [ctypes.c_void_p]
                    _getview = fn
                    break
        except Exception:                                   # noqa: BLE001
            _getview = False
    return _getview


def nswindow(win):
    cached = getattr(win, "_myuni_nswindow", None)
    if cached is not None:
        return cached
    fn = _root_control()
    if not fn or not _ok:
        return None
    try:
        win.update_idletasks()
        ptr = fn(ctypes.c_void_p(win.winfo_id()))
        if not ptr:
            return None
        nsw = objc.objc_object(c_void_p=ctypes.c_void_p(ptr)).window()
        win._myuni_nswindow = nsw
        return nsw
    except Exception:                                       # noqa: BLE001
        return None


# ---------------------------------------------------------------- 창
def transparent_window(win, key):
    if not _ok:
        win.configure(bg=key)
        return key
    win.attributes("-transparent", True)
    win.configure(bg="systemTransparent")
    return "systemTransparent"


def raise_above(win):
    """맥에서 -topmost 는 창이 화면에 올라간 뒤에 걸어야 먹는다."""
    try:
        win.update_idletasks()
        win.attributes("-topmost", True)
    except Exception:                                       # noqa: BLE001
        pass
    nsw = nswindow(win)
    if nsw is not None:
        try:
            nsw.setLevel_(AppKit.NSFloatingWindowLevel)
            nsw.setCollectionBehavior_(
                AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
                | AppKit.NSWindowCollectionBehaviorStationary)
            nsw.setHasShadow_(False)
        except Exception:                                   # noqa: BLE001
            pass


def _cgimage(rgba):
    """RGBA -> 알파를 미리 곱한(PIL 'RGBa') CGImage."""
    raw = rgba.convert("RGBa").tobytes()
    w, h = rgba.size
    data = Foundation.NSData.dataWithBytes_length_(raw, len(raw))
    prov = Quartz.CGDataProviderCreateWithCFData(data)
    return Quartz.CGImageCreate(
        w, h, 8, 32, w * 4, _CS,
        Quartz.kCGImageAlphaPremultipliedLast | Quartz.kCGBitmapByteOrderDefault,
        prov, None, False, Quartz.kCGRenderingIntentDefault)


class _LayerFrame(object):
    __slots__ = ("img", "mask")

    def __init__(self, img, mask):
        self.img, self.mask = img, mask


class SpriteView(object):
    """맥판. 위젯은 빈 Frame 이고 그림은 CALayer 가 그린다."""

    HIT_MARGIN = 3       # 도트 가장자리에서 클릭이 새지 않게 두는 여유 (px)

    def __init__(self, win, key, w, h):
        import tkinter as tk

        self.win, self.w, self.h = win, w, h
        self.layer = None
        self._mask = None
        self._ignoring = False
        if not _ok:
            from .platform_base import SpriteView as Fallback
            self._fallback = Fallback(win, key, w, h)
            self.widget = self._fallback.widget
            return
        self._fallback = None
        self.widget = tk.Frame(win, width=w, height=h, bg=key, bd=0, highlightthickness=0)
        self.widget.pack()
        raise_above(win)
        nsw = nswindow(win)
        if nsw is None:
            return
        try:
            cv = nsw.contentView()
            cv.setWantsLayer_(True)
            lay = CALayer.layer()
            lay.setFrame_(((0, 0), (w, h)))
            lay.setContentsScale_(nsw.backingScaleFactor())
            lay.setMagnificationFilter_("nearest")      # 도트가 뭉개지지 않게
            lay.setMinificationFilter_("nearest")
            cv.layer().addSublayer_(lay)
            self.layer = lay
        except Exception:                                   # noqa: BLE001
            self.layer = None

    def frames(self, images):
        if self._fallback is not None:
            return self._fallback.frames(images)
        out = []
        for im in images:
            mask = im.split()[3].point(lambda a: 255 if a >= 128 else 0)
            out.append(_LayerFrame(_cgimage(im) if self.layer is not None else None, mask))
        return out

    def show(self, frame):
        if self._fallback is not None:
            return self._fallback.show(frame)
        self._mask = frame.mask
        if self.layer is None or frame.img is None:
            return
        CATransaction.begin()
        CATransaction.setDisableActions_(True)      # 프레임마다 크로스페이드가 붙지 않게
        try:
            self.layer.setContents_(frame.img)
        finally:
            CATransaction.commit()

    def solid_at(self, lx, ly):
        m = self._mask
        if m is None:
            return False
        r = self.HIT_MARGIN
        for y in range(max(0, ly - r), min(m.height, ly + r + 1)):
            for x in range(max(0, lx - r), min(m.width, lx + r + 1)):
                if m.getpixel((x, y)):
                    return True
        return False

    def update_hit(self, lx, ly):
        """커서 밑이 비었으면 클릭을 통과시키고, 도트 위면 받는다. 창 밖이면 받아 둔다
        (통과 상태로 두면 커서가 도트로 들어온 직후의 클릭이 바탕화면으로 샌다)."""
        if self._fallback is not None or self.layer is None:
            return
        want = lx is not None and 0 <= lx < self.w and 0 <= ly < self.h and not self.solid_at(lx, ly)
        if want == self._ignoring:
            return
        nsw = nswindow(self.win)
        if nsw is None:
            return
        try:
            nsw.setIgnoresMouseEvents_(want)
            self._ignoring = want
        except Exception:                                   # noqa: BLE001
            pass

    def destroy(self):
        if self.layer is not None:
            try:
                self.layer.removeFromSuperlayer()
            except Exception:                               # noqa: BLE001
                pass
            self.layer = None


# ---------------------------------------------------------------- 화면 · 입력
def work_area(fallback_w, fallback_h):
    """메뉴 막대와 독을 뺀 주 화면. AppKit 은 왼쪽 아래가 원점이라 뒤집는다."""
    if not _ok:
        return 0, 0, fallback_w, fallback_h
    try:
        screens = AppKit.NSScreen.screens()
        prim = screens[0]
        h = prim.frame().size.height
        v = prim.visibleFrame()
        x1 = int(round(v.origin.x))
        x2 = int(round(v.origin.x + v.size.width))
        y1 = int(round(h - (v.origin.y + v.size.height)))
        y2 = int(round(h - v.origin.y))
        if x2 > x1 and y2 > y1:
            return x1, y1, x2, y2
    except Exception:                                       # noqa: BLE001
        pass
    return 0, 0, fallback_w, fallback_h


def idle_seconds():
    if _ok:
        try:
            return float(Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateCombinedSessionState, Quartz.kCGAnyInputEventType))
        except Exception:                                   # noqa: BLE001
            pass
    try:
        out = subprocess.run(["/usr/sbin/ioreg", "-c", "IOHIDSystem"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if "HIDIdleTime" in line:
                return int(line.rsplit("=", 1)[1].strip()) / 1e9
    except Exception:                                       # noqa: BLE001
        pass
    return 0.0


# ---------------------------------------------------------------- 프로세스
_LOCK = None


def single_lock(data_dir_):
    """flock. 프로세스가 어떻게 죽든 커널이 놓아준다."""
    global _LOCK
    import fcntl

    try:
        f = open(os.path.join(data_dir_, "running.lock"), "a+")
    except OSError:
        return None, False
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None, True
    _LOCK = f                 # 닫히면 잠금이 풀린다
    return f, False


def single_release(handle):
    global _LOCK
    _LOCK = None
    try:
        handle.close()
    except Exception:                                       # noqa: BLE001
        pass


def data_dir(app_name=APP_NAME):
    d = os.path.join(os.path.expanduser("~/Library/Application Support"), app_name)
    os.makedirs(d, exist_ok=True)
    return d


def machine_raw():
    """IOPlatformUUID. libSystem 의 gethostuuid 가 같은 값을 프로세스 안에서 바로 준다."""
    try:
        import uuid as _uuid
        buf = (ctypes.c_ubyte * 16)()
        wait = (ctypes.c_int64 * 2)(0, 0)
        libc = ctypes.CDLL("/usr/lib/libSystem.dylib")
        if libc.gethostuuid(buf, wait) == 0:
            return str(_uuid.UUID(bytes=bytes(buf))).upper()
    except Exception:                                       # noqa: BLE001
        pass
    try:
        out = subprocess.run(["/usr/sbin/ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                             capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if "IOPlatformUUID" in line:
                return line.split('"')[3].strip() or None
    except Exception:                                       # noqa: BLE001
        pass
    return None


def dpi_aware():
    pass


def before_tk():
    """비정상 종료 뒤 "창을 복구할까요?" 대화상자가 Tk 초기화 안에서 떠 멈추는 것을 막는다."""
    if not _ok:
        return
    try:
        Foundation.NSUserDefaults.standardUserDefaults().registerDefaults_(
            {"ApplePersistenceIgnoreState": True, "NSQuitAlwaysKeepsWindows": False})
    except Exception:                                       # noqa: BLE001
        pass


def hide_from_dock():
    """독과 Cmd+Tab 에서 숨긴다. tk.Tk() 를 만든 **뒤에** 불러야 한다."""
    if not _ok:
        return
    try:
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(
            AppKit.NSApplicationActivationPolicyAccessory)
    except Exception:                                       # noqa: BLE001
        pass


def activate():
    """독에 없는 앱은 창을 띄워도 앞에 안 온다. 로그인 창처럼 글자를 칠 창을 띄울 때 부른다."""
    if not _ok:
        return
    try:
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    except Exception:                                       # noqa: BLE001
        pass


def font_family():
    return "Apple SD Gothic Neo"


def already_running_hint():
    return "화면 위쪽 메뉴 막대에서 MyUNi 아이콘을 찾아보세요."
