# -*- coding: utf-8 -*-
"""맥 메뉴 막대 아이콘.

메뉴 막대에는 **단추만** 올리고, 누르면 Tk 으로 그린 메뉴를 띄운다. NSMenu 를 붙이면
메뉴가 열린 동안 macOS 가 중첩 런루프를 돌리고, 그 사이 Tk 의 after 타이머가 돌다
파이썬이 죽는다 (캐릭터가 쉬지 않고 움직이므로 메뉴를 여는 순간이 마지막이 된다).

지킬 것: tkinter.Tk() 를 먼저 만든다. objc 콜백 안에서는 tkinter 를 부르지 않는다.
"""
import io

import AppKit
import Foundation
import objc

from . import config, sprites


class _Target(AppKit.NSObject):
    def initWithTray_(self, tray):
        self = objc.super(_Target, self).init()
        if self is None:
            return None
        self._tray = tray
        return self

    def clicked_(self, _sender):
        self._tray.pending = True          # 여기서 Tk 을 부르지 않는다


class Tray(object):
    def __init__(self, app):
        self.app = app
        self.item = None
        self._target = None
        self._image = None
        self.pending = False
        self._job = None

    def start(self):
        bar = AppKit.NSStatusBar.systemStatusBar()
        self.item = bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self._target = _Target.alloc().initWithTray_(self)
        pt = max(16, int(bar.thickness()) - 4)
        self._image = self._nsimage(pt)
        btn = self.item.button()
        btn.setImage_(self._image)
        btn.setToolTip_("MyUNi")
        btn.setTarget_(self._target)
        btn.setAction_(b"clicked:")
        self._pump()

    def _pump(self):
        try:
            if self.pending:
                self.pending = False
                x, y = self.app.root.winfo_pointerxy()
                self.app.open_menu(x - 10, y + 12)
        except Exception:                                   # noqa: BLE001
            config.log_exc("메뉴 막대 처리 실패")
        if self.item is not None:
            self._job = self.app.root.after(60, self._pump)

    def _nsimage(self, points):
        ns = AppKit.NSImage.alloc().initWithSize_(AppKit.NSMakeSize(points, points))
        for scale in (1, 2):
            b = io.BytesIO()
            sprites.icon(points * scale).save(b, "png")
            raw = b.getvalue()
            rep = AppKit.NSBitmapImageRep.imageRepWithData_(
                Foundation.NSData.dataWithBytes_length_(raw, len(raw)))
            if rep is not None:
                rep.setSize_(AppKit.NSMakeSize(points, points))
                ns.addRepresentation_(rep)
        return ns

    def stop(self):
        if self._job is not None:
            try:
                self.app.root.after_cancel(self._job)
            except Exception:                               # noqa: BLE001
                pass
        if self.item is not None:
            try:
                AppKit.NSStatusBar.systemStatusBar().removeStatusItem_(self.item)
            except Exception:                               # noqa: BLE001
                pass
        self.item = self._target = self._image = None
