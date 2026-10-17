"""柠檬片悬浮窗。左键拖动，右键打开菜单。

菜单打开时不再改置顶，也不再改菜单文字。之前每 0.2 秒都做这两件事，
Windows 会把弹出的菜单反复重画，点击落空。
"""

from __future__ import annotations

import tkinter as tk

from eyeguard.platform_win import window_geometry
from eyeguard.skins import clamp_size, draw_slice, normalize_skin

PHASE_LABEL = {
    "work": "工作中",
    "warn": "即将休息",
    "rest": "休息中",
    "paused": "已暂停",
}

# 窗口上这个颜色会变成透明，柠檬片以外的方块不再挡住桌面。
_CLEAR = "#010203"


class FloatWindow(tk.Toplevel):
    def __init__(self, master: tk.Misc, on_command, skin: str = "green", size: int = 240) -> None:
        super().__init__(master)
        self._on_command = on_command
        self._drag_x = 0
        self._drag_y = 0
        self._moved = False
        self._skin = normalize_skin(skin)
        self._size = clamp_size(size)
        self._clock = ""
        self._phase = ""
        self._topmost: bool | None = None
        self._pause_shown: bool | None = None
        self._menu_open = False
        self._pending: tuple[str, str, bool] | None = None
        self._pending_pause: bool | None = None
        self.overrideredirect(True)
        self.configure(bg=_CLEAR)
        self.attributes("-transparentcolor", _CLEAR)
        self.geometry(f"{self._size}x{self._size}")

        self.canvas = tk.Canvas(
            self,
            width=self._size,
            height=self._size,
            bg=_CLEAR,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self.menu = tk.Menu(self, tearoff=0, font=("Microsoft YaHei UI", 10))
        self._pause_index = 2
        for label, command in (
            ("立即休息", "rest_now"),
            ("推迟休息", "postpone"),
            ("暂停计时", "toggle_pause"),
            ("关灯", "lamp"),
        ):
            self.menu.add_command(label=label, command=lambda name=command: self._defer(name))

        self.skin_var = tk.StringVar(value=self._skin)
        skin_menu = tk.Menu(self.menu, tearoff=0, font=("Microsoft YaHei UI", 10))
        skin_menu.add_radiobutton(
            label="青柠",
            variable=self.skin_var,
            value="green",
            command=lambda: self._defer("skin"),
        )
        skin_menu.add_radiobutton(
            label="橙片",
            variable=self.skin_var,
            value="orange",
            command=lambda: self._defer("skin"),
        )
        skin_menu.add_separator()
        skin_menu.add_command(label="放大", command=lambda: self._defer("zoom_in"))
        skin_menu.add_command(label="缩小", command=lambda: self._defer("zoom_out"))
        self.menu.add_cascade(label="皮肤", menu=skin_menu)

        for label, command in (
            ("亮度与方案", "settings"),
            ("定时关机", "shutdown"),
            ("隐藏悬浮窗", "hide"),
            ("退出", "quit"),
        ):
            self.menu.add_command(label=label, command=lambda name=command: self._defer(name))

        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Button-3>", self._popup)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self._draw("00:00", "work")

    @property
    def size(self) -> int:
        return self._size

    def render(self, clock: str, phase: str, topmost: bool) -> None:
        if self._menu_open:
            self._pending = (clock, phase, topmost)
            return
        self._paint(clock, phase, topmost)

    def set_skin(self, skin: str) -> None:
        skin = normalize_skin(skin)
        if self.skin_var.get() != skin:
            self.skin_var.set(skin)
        if skin == self._skin:
            return
        self._skin = skin
        self._draw(self._clock or "00:00", self._phase or "work")

    def set_size(self, size: int) -> None:
        size = clamp_size(size)
        if size == self._size:
            return
        left, top = self.winfo_x(), self.winfo_y()
        self._size = size
        self.canvas.configure(width=size, height=size)
        self.geometry(window_geometry(size, size, left, top))
        self._draw(self._clock or "00:00", self._phase or "work")

    def set_pause_label(self, paused: bool) -> None:
        if self._menu_open:
            self._pending_pause = paused
            return
        self._apply_pause(paused)

    def place_initial(self, x: int | None, y: int | None) -> None:
        self.update_idletasks()
        if x is None or y is None:
            x = max(0, self.winfo_screenwidth() - self._size - 28)
            y = 48
        self.geometry(window_geometry(self._size, self._size, x, y))

    def _paint(self, clock: str, phase: str, topmost: bool) -> None:
        if clock != self._clock or phase != self._phase:
            self._draw(clock, phase)
        if self._topmost != topmost:
            self.attributes("-topmost", bool(topmost))
            self._topmost = bool(topmost)

    def _apply_pause(self, paused: bool) -> None:
        if paused == self._pause_shown:
            return
        self.menu.entryconfigure(self._pause_index, label="继续计时" if paused else "暂停计时")
        self._pause_shown = paused

    def _draw(self, clock: str, phase: str) -> None:
        self._clock = clock
        self._phase = phase
        draw_slice(self.canvas, self._skin, clock, phase, PHASE_LABEL.get(phase, "工作中"), self._size)

    def _defer(self, name: str) -> None:
        # 每次点击单独排队。不要存进一个格子里等菜单返回再取，
        # Windows 会在菜单函数返回之后才调用 command，格子里会变成上一次的功能。
        self.after(0, lambda command=name: self._on_command(command))

    def _press(self, event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()
        self._moved = False

    def _drag(self, event) -> None:
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        if abs(x - self.winfo_x()) > 2 or abs(y - self.winfo_y()) > 2:
            self._moved = True
        self.geometry(window_geometry(self._size, self._size, x, y))

    def _release(self, _event) -> None:
        if self._moved:
            self._on_command("moved")

    def _popup(self, event) -> None:
        self._menu_open = True
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._menu_open = False
            try:
                self.menu.grab_release()
            except tk.TclError:
                pass
        self._flush_pending()

    def _wheel(self, event) -> None:
        step = 20 if event.delta > 0 else -20
        self.set_size(self._size + step)
        self._on_command("resized")

    def _flush_pending(self) -> None:
        pending = self._pending
        self._pending = None
        if pending is not None:
            self._paint(*pending)
        if self._pending_pause is not None:
            self._apply_pause(self._pending_pause)
            self._pending_pause = None
