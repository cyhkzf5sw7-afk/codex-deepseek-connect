"""Small Windows Credential Manager adapter (generic credentials)."""
from __future__ import annotations
import ctypes

DWORD = ctypes.c_uint32
BYTE = ctypes.c_ubyte
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
ERROR_NOT_FOUND = 1168
TARGET = "codex-deepseek-connect/api-key/v1"


class FILETIME(ctypes.Structure):
    _fields_ = [("dwLowDateTime", DWORD), ("dwHighDateTime", DWORD)]


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", DWORD), ("Type", DWORD), ("TargetName", ctypes.c_wchar_p),
        ("Comment", ctypes.c_wchar_p), ("LastWritten", FILETIME),
        ("CredentialBlobSize", DWORD), ("CredentialBlob", ctypes.POINTER(BYTE)),
        ("Persist", DWORD), ("AttributeCount", DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", ctypes.c_wchar_p), ("UserName", ctypes.c_wchar_p),
    ]


PCREDENTIALW = ctypes.POINTER(CREDENTIALW)


def _load_api():
    api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    api.CredReadW.argtypes = [ctypes.c_wchar_p, DWORD, DWORD, ctypes.POINTER(PCREDENTIALW)]
    api.CredReadW.restype = ctypes.c_int
    api.CredWriteW.argtypes = [PCREDENTIALW, DWORD]
    api.CredWriteW.restype = ctypes.c_int
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api, ctypes.get_last_error


def _get_pointer(api, get_error):
    pointer = PCREDENTIALW()
    if api.CredReadW(TARGET, CRED_TYPE_GENERIC, 0, ctypes.byref(pointer)):
        return pointer
    error = get_error()
    if error == ERROR_NOT_FOUND:
        return None
    raise ValueError(f"Windows 凭据管理器读取失败（错误码 {error}）。")


def read_key():
    api, get_error = _load_api()
    pointer = _get_pointer(api, get_error)
    if pointer is None:
        raise ValueError("未找到 DeepSeek 凭据；请先执行 credential-save。")
    try:
        item = pointer.contents
        if not item.CredentialBlob or not 0 < item.CredentialBlobSize <= 2560:
            raise ValueError("Windows 凭据内容无效。")
        try:
            return ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize).decode("utf-16-le")
        except UnicodeDecodeError as exc:
            raise ValueError("Windows 凭据内容编码无效。") from exc
    finally:
        api.CredFree(pointer)


def save_key(key):
    api, get_error = _load_api()
    existing = _get_pointer(api, get_error)
    if existing is not None:
        api.CredFree(existing)
        raise ValueError("同名 Windows 凭据已存在，未覆盖。")
    secret = bytearray(key.encode("utf-16-le"))
    if not secret or len(secret) > 2560:
        raise ValueError("API Key 长度无效。")
    array = (BYTE * len(secret)).from_buffer(secret)
    item = CREDENTIALW()
    item.Type = CRED_TYPE_GENERIC
    item.TargetName = TARGET
    item.CredentialBlobSize = len(secret)
    item.CredentialBlob = ctypes.cast(array, ctypes.POINTER(BYTE))
    item.Persist = CRED_PERSIST_LOCAL_MACHINE
    item.UserName = "DeepSeek"
    try:
        if not api.CredWriteW(ctypes.byref(item), 0):
            raise ValueError(f"Windows 凭据管理器写入失败（错误码 {get_error()}）。")
    finally:
        ctypes.memset(array, 0, len(secret))
