"""macOS default-keychain adapter using Security.framework."""
from __future__ import annotations
import ctypes
from i18n import tr

SERVICE = b"org.codex-deepseek-connect.api-key.v1"
ACCOUNT = b"default"
DUPLICATE_ITEM = -25299
ITEM_NOT_FOUND = -25300


def _load_api():
    sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    ptr = ctypes.c_void_p
    u32 = ctypes.c_uint32
    sec.SecKeychainCopyDefault.argtypes = [ctypes.POINTER(ptr)]
    sec.SecKeychainCopyDefault.restype = ctypes.c_int32
    sec.SecKeychainAddGenericPassword.argtypes = [ptr, u32, ctypes.c_char_p, u32, ctypes.c_char_p, u32, ptr, ctypes.POINTER(ptr)]
    sec.SecKeychainAddGenericPassword.restype = ctypes.c_int32
    sec.SecKeychainFindGenericPassword.argtypes = [ptr, u32, ctypes.c_char_p, u32, ctypes.c_char_p, ctypes.POINTER(u32), ctypes.POINTER(ptr), ctypes.POINTER(ptr)]
    sec.SecKeychainFindGenericPassword.restype = ctypes.c_int32
    sec.SecKeychainItemFreeContent.argtypes = [ptr, ptr]
    sec.SecKeychainItemFreeContent.restype = ctypes.c_int32
    cf.CFRelease.argtypes = [ptr]
    cf.CFRelease.restype = None
    return sec, cf


def _default_keychain(sec):
    keychain = ctypes.c_void_p()
    status = sec.SecKeychainCopyDefault(ctypes.byref(keychain))
    if status != 0 or not keychain.value:
        raise ValueError(tr("无法打开默认钥匙串（状态码 {status}）。", status=status))
    return keychain


def save_key(key):
    secret = bytearray(key.encode("utf-8"))
    if not secret:
        raise ValueError(tr("API Key 长度无效。"))
    buffer = (ctypes.c_ubyte * len(secret)).from_buffer(secret)
    try:
        sec, cf = _load_api()
        keychain = _default_keychain(sec)
        try:
            status = sec.SecKeychainAddGenericPassword(
                keychain, len(SERVICE), SERVICE, len(ACCOUNT), ACCOUNT,
                len(secret), ctypes.cast(buffer, ctypes.c_void_p), None)
            if status == DUPLICATE_ITEM:
                raise ValueError(tr("同名钥匙串项目已存在，未覆盖。"))
            if status != 0:
                raise ValueError(tr("无法保存钥匙串项目（状态码 {status}）。", status=status))
        finally:
            cf.CFRelease(keychain)
    finally:
        ctypes.memset(buffer, 0, len(secret))


def read_key():
    sec, cf = _load_api()
    keychain = _default_keychain(sec)
    length = ctypes.c_uint32()
    data = ctypes.c_void_p()
    try:
        status = sec.SecKeychainFindGenericPassword(
            keychain, len(SERVICE), SERVICE, len(ACCOUNT), ACCOUNT,
            ctypes.byref(length), ctypes.byref(data), None)
        if status == ITEM_NOT_FOUND:
            raise ValueError(tr("未找到钥匙串项目；请先执行 credential-save。"))
        if status != 0:
            raise ValueError(tr("无法读取钥匙串项目（状态码 {status}）。", status=status))
        try:
            if not data.value or not 0 < length.value <= 65536:
                raise ValueError(tr("钥匙串项目内容无效。"))
            try:
                return ctypes.string_at(data, length.value).decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(tr("钥匙串项目编码无效。")) from exc
        finally:
            if data.value:
                sec.SecKeychainItemFreeContent(None, data)
    finally:
        cf.CFRelease(keychain)
