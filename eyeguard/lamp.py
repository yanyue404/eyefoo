"""关灯：一块纯黑遮罩。单击或再次按热键恢复，双击关闭显示器。"""

from __future__ import annotations

import tkinter as tk

from eyeguard.platform_win import window_geometry


class LampOverlay:
    def __init__(self, master: tk.Misc, on_dismiss, on_screen_off) -> None:
        self._master = master
        self._on_dismiss = on_dismiss
        self._on_screen_off = on_screen_off
        self._windows: list[tk.Toplevel] = []
        self._pending = None

    @property
    def visible(self) -> bool:
        return bool(self._windows)

    def toggle(self, areas: list[tuple[int, int, int, int]]) -> bool:
        if self._windows:
            self.close()
            return False
        self.show(areas)
        return True

    def show(self, areas: list[tuple[int, int, int, int]]) -> None:
        self.close()
        for left, top, width, height in areas:
            window = tk.Toplevel(self._master)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.configure(bg="#000000")
            window.geometry(window_geometry(width, height, left, top))
            window.bind("<Button-1>", lambda _event: self._schedule_dismiss())
            window.bind("<Double-Button-1>", lambda _event: self._screen_off())
            tk.Label(
                window,
                text="单击恢复    双击关闭显示器    Ctrl+Alt+T",
                fg="#6e6e6e",
                bg="#000000",
                font=("Microsoft YaHei UI", 12),
            ).place(relx=0.5, rely=0.5, anchor="center")
            self._windows.append(window)

    def close(self) -> None:
        self._cancel_pending()
        for window in self._windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self._windows.clear()

    def _schedule_dismiss(self) -> None:
        self._cancel_pending()
        self._pending = self._master.after(280, self._on_dismiss)

    def _screen_off(self) -> None:
        self._cancel_pending()
        self._on_screen_off()

    def _cancel_pending(self) -> None:
        if self._pending is not None:
            try:
                self._master.after_cancel(self._pending)
            except tk.TclError:
                pass
            self._pending = None
