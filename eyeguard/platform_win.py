"""Windows 平台能力。

护眼软件改屏幕，走的是系统公开接口，而不是给每个窗口染色：

- 亮度 / 暖色：改显示器伽马表 SetDeviceGammaRamp。三通道各 256 档，
  亮度是整表按比例缩小，暖色是多压低蓝通道、少压低绿通道。
- 空闲：GetLastInputInfo，距离上次键鼠输入的时间。
- 全屏：前台窗口几乎铺满某一块屏幕时，视为在看视频或玩游戏。
- 关屏：广播 SC_MONITORPOWER。鼠标一动，系统会自己点亮。
- 热键：RegisterHotKey，不安装键盘钩子。
"""

from __future__ import annotations

import ctypes
import os
import sys
import threading
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_D = 0x44
VK_T = 0x54
WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001
HWND_BROADCAST = 0xFFFF
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170

HOTKEY_POSTPONE = 1
HOTKEY_LAMP = 2

_SHELL_CLASSES = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
}


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", ctypes.c_wchar * 32),
    ]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


MONITORENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.c_int, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM
)

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [
    ctypes.POINTER(MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
    wintypes.UINT,
]
user32.PeekMessageW.restype = wintypes.BOOL
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.EnumDisplayMonitors.argtypes = [
    wintypes.HDC,
    ctypes.c_void_p,
    MONITORENUMPROC,
    wintypes.LPARAM,
]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
gdi32.CreateDCW.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.GetDeviceGammaRamp.restype = wintypes.BOOL
gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL


@dataclass(frozen=True)
class Monitor:
    device: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


_original_ramps: dict[str, list[int]] = {}
_gamma_lock = threading.Lock()


def enable_dpi_awareness() -> None:
    """在创建任何窗口之前调用，让屏幕坐标和悬浮窗使用同一套像素。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            return


def monitors() -> list[Monitor]:
    found: list[Monitor] = []

    def callback(hmon, _hdc, _rect, _data):
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            found.append(
                Monitor(
                    info.szDevice,
                    int(info.rcMonitor.left),
                    int(info.rcMonitor.top),
                    int(info.rcMonitor.right),
                    int(info.rcMonitor.bottom),
                )
            )
        return 1

    proc = MONITORENUMPROC(callback)
    user32.EnumDisplayMonitors(None, None, proc, 0)
    return found


def get_idle_seconds() -> float:
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    elapsed = (kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return elapsed / 1000.0


def is_foreground_fullscreen() -> bool:
    hwnd = user32.GetForegroundWindow()
    if not hwnd or user32.IsIconic(hwnd) or not user32.IsWindowVisible(hwnd):
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return False
    class_name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, class_name, 256)
    if class_name.value in _SHELL_CLASSES:
        return False
    rect = RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return False
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    for monitor in monitors():
        if width >= monitor.width - 8 and height >= monitor.height - 8:
            return True
    return False


def apply_display(brightness: float, warmth: float) -> bool:
    """按亮度与暖色重写每台显示器的伽马表。失败时保持原表。"""
    brightness = min(1.0, max(0.3, float(brightness)))
    warmth = min(1.0, max(0.0, float(warmth)))
    gains = (
        brightness,
        brightness * (1.0 - 0.20 * warmth),
        brightness * (1.0 - 0.55 * warmth),
    )
    ok = True
    with _gamma_lock:
        for monitor in monitors():
            dc = gdi32.CreateDCW("DISPLAY", monitor.device, None, None)
            if not dc:
                ok = False
                continue
            try:
                source = _read_original(dc, monitor.device)
                ramp = (ctypes.c_ushort * 768)()
                for channel, gain in enumerate(gains):
                    base = channel * 256
                    for index in range(256):
                        ramp[base + index] = min(65535, int(source[base + index] * gain))
                if not gdi32.SetDeviceGammaRamp(dc, ctypes.byref(ramp)):
                    ok = False
            finally:
                gdi32.DeleteDC(dc)
    return ok


def restore_display() -> None:
    with _gamma_lock:
        for monitor in monitors():
            source = _original_ramps.get(monitor.device)
            if source is None:
                continue
            dc = gdi32.CreateDCW("DISPLAY", monitor.device, None, None)
            if not dc:
                continue
            try:
                ramp = (ctypes.c_ushort * 768)()
                for index, value in enumerate(source):
                    ramp[index] = value
                gdi32.SetDeviceGammaRamp(dc, ctypes.byref(ramp))
            finally:
                gdi32.DeleteDC(dc)
        _original_ramps.clear()


def turn_off_display() -> None:
    user32.SendMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)


def hotkey_loop(stop: threading.Event, sink) -> str:
    """在独立线程里等热键。sink 只能入队，不能直接碰界面。"""
    postpone_ok = bool(
        user32.RegisterHotKey(None, HOTKEY_POSTPONE, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_D)
    )
    lamp_ok = bool(
        user32.RegisterHotKey(None, HOTKEY_LAMP, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_T)
    )
    message = MSG()
    try:
        while not stop.is_set():
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, PM_REMOVE):
                if message.message == WM_HOTKEY:
                    sink(int(message.wParam))
            stop.wait(0.05)
    finally:
        if postpone_ok:
            user32.UnregisterHotKey(None, HOTKEY_POSTPONE)
        if lamp_ok:
            user32.UnregisterHotKey(None, HOTKEY_LAMP)
    missing = []
    if not postpone_ok:
        missing.append("Ctrl+Alt+D")
    if not lamp_ok:
        missing.append("Ctrl+Alt+T")
    if not missing:
        return ""
    return "热键已被其他程序占用：" + "、".join(missing)


def set_run_at_startup(enabled: bool) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    name = "EyeGuard"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if not enabled:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                return
            return
        if getattr(sys, "frozen", False):
            launch = f'"{sys.executable}"'
        else:
            executable = Path(sys.executable)
            pythonw = executable.with_name("pythonw.exe")
            if pythonw.exists():
                executable = pythonw
            launch = f'"{executable}" "{_entry_script()}"'
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, launch)


def window_geometry(width: int, height: int, left: int, top: int) -> str:
    """Tk 几何串。坐标可以为负，副屏在主屏左侧时会用到。"""
    return f"{int(width)}x{int(height)}{int(left):+d}{int(top):+d}"


def _entry_script() -> str:
    override = os.environ.get("EYEGUARD_ENTRY")
    if override:
        return override
    return str(Path(__file__).resolve().parents[1] / "run.py")


def _read_original(dc, device: str) -> list[int]:
    cached = _original_ramps.get(device)
    if cached is not None:
        return cached
    ramp = (ctypes.c_ushort * 768)()
    if not gdi32.GetDeviceGammaRamp(dc, ctypes.byref(ramp)):
        for index in range(256):
            value = index * 257
            ramp[index] = ramp[index + 256] = ramp[index + 512] = value
    copied = [int(ramp[index]) for index in range(768)]
    _original_ramps[device] = copied
    return copied
