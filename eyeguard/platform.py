"""按当前系统挑选屏幕、热键和开机启动的实现。

界面和计时从这里取能力，不要直接依赖某一套系统接口。
Windows 的实现在 platform_win.py。macOS 和 Linux 的对应文件还没写，
接口和阶段安排见项目根目录的 DESIGN.md。
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from eyeguard.platform_win import (
        HOTKEY_LAMP,
        HOTKEY_POSTPONE,
        apply_display,
        enable_dpi_awareness,
        get_idle_seconds,
        hotkey_loop,
        is_foreground_fullscreen,
        monitors,
        restore_display,
        set_run_at_startup,
        turn_off_display,
        window_geometry,
    )
else:

    def enable_dpi_awareness() -> None:
        return

    def _unavailable(*_args, **_kwargs):
        raise RuntimeError(f"{sys.platform} 还没有护眼计时的系统实现，见 DESIGN.md")

    HOTKEY_LAMP = 2
    HOTKEY_POSTPONE = 1
    apply_display = _unavailable
    get_idle_seconds = _unavailable
    hotkey_loop = _unavailable
    is_foreground_fullscreen = _unavailable
    monitors = _unavailable
    restore_display = _unavailable
    set_run_at_startup = _unavailable
    turn_off_display = _unavailable
    window_geometry = _unavailable

__all__ = [
    "HOTKEY_LAMP",
    "HOTKEY_POSTPONE",
    "apply_display",
    "enable_dpi_awareness",
    "get_idle_seconds",
    "hotkey_loop",
    "is_foreground_fullscreen",
    "monitors",
    "restore_display",
    "set_run_at_startup",
    "turn_off_display",
    "window_geometry",
]
