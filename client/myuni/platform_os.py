# -*- coding: utf-8 -*-
"""이 컴퓨터에 맞는 구현을 고른다. 부르는 쪽은 이 모듈 하나만 본다.

    from . import platform_os as PLAT

윈도우에서는 platform_mac 을 import 조차 하지 않는다 (pyobjc 가 없다). 반대도 마찬가지.
"""
import sys

if sys.platform == "win32":
    from . import platform_win as _M
elif sys.platform == "darwin":
    from . import platform_mac as _M
else:
    from . import platform_base as _M

NAME = _M.__name__.rsplit(".", 1)[-1]
NEEDS_HIT_TRACKING = _M.NEEDS_HIT_TRACKING
RIGHT_CLICK = _M.RIGHT_CLICK
NATIVE_MENU = _M.NATIVE_MENU

bind_right = _M.bind_right
transparent_window = _M.transparent_window
raise_above = _M.raise_above
SpriteView = _M.SpriteView
work_area = _M.work_area
idle_seconds = _M.idle_seconds
single_lock = _M.single_lock
single_release = _M.single_release
data_dir = _M.data_dir
machine_raw = _M.machine_raw
mac_address_fallback = _M.mac_address_fallback
dpi_aware = _M.dpi_aware
before_tk = _M.before_tk
hide_from_dock = _M.hide_from_dock
activate = _M.activate
missing_requirement = _M.missing_requirement
font_family = _M.font_family
already_running_hint = _M.already_running_hint
