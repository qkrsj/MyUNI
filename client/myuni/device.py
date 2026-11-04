# -*- coding: utf-8 -*-
"""서버로 보내는 기기 식별값.

원본(윈도우 MachineGuid, 맥 IOPlatformUUID)은 **이 컴퓨터 밖으로 나가지 않는다.**
SHA-256 으로 바꾼 값만 보내고, 서버는 거기에 비밀 salt 로 HMAC 을 한 번 더 걸어 저장한다.
"""
import hashlib

from . import platform_os as PLAT

_cached = None


def device_id():
    global _cached
    if _cached is None:
        raw = PLAT.machine_raw() or PLAT.mac_address_fallback()
        _cached = hashlib.sha256(("myuni-device:" + raw).encode("utf-8")).hexdigest()
    return _cached
