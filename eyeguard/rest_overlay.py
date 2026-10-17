"""休息遮罩。每块屏幕一个置顶窗口，到点由主程序关掉。

窗口会周期性地回到最前，避免被普通软件盖住。
不拦截系统热键，任务管理器仍然可以结束本程序。
"""

from __future__ import annotations

import tkinter as tk

from eyeguard.platform_win import window_geometry

EXERCISES = [
    "闭眼，双手搓热后轻轻捂住双眼",
    "眼球缓慢地向上、下、左、右看",
    "看向六米以外，让眼睛停止对焦",
    "自然眨眼二十次，让泪膜重新铺开",
]


class RestOverlay:
    def __init__(self, master: tk.Misc, on_postpone, on_finish, on_screen_off) -> None:
        self._master = master
        self._on_postpone = on_postpone
        self._on_finish = on_finish
        self._on_screen_off = on_screen_off
        self._windows: list[tk.Toplevel] = []
        self._clocks: list[tk.Label] = []
        self._tips: list[tk.Label] = []
        self._exercise = 0
        self._after_id = None

    @property
    def visible(self) -> bool:
        return bool(self._windows)

    def show(self, areas: list[tuple[int, int, int, int]]) -> None:
        self.close()
        if not areas:
            areas = [(0, 0, self._master.winfo_screenwidth(), self._master.winfo_screenheight())]
        for index, (left, top, width, height) in enumerate(areas):
            window = tk.Toplevel(self._master)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.configure(bg="#1a120c")
            window.geometry(window_geometry(width, height, left, top))
            window.bind("<Double-Button-1>", lambda _event: self._on_screen_off())

            title = tk.Label(
                window,
                text="离开屏幕，休息一下",
                fg="#f3e6d4",
                bg="#1a120c",
                font=("Microsoft YaHei UI", 28, "bold"),
            )
            title.pack(pady=(height // 5, 12))

            clock = tk.Label(
                window,
                text="00:00",
                fg="#f6c98a",
                bg="#1a120c",
                font=("Microsoft YaHei UI", 48, "bold"),
            )
            clock.pack()
            self._clocks.append(clock)

            tip = tk.Label(
                window,
                text=EXERCISES[0],
                fg="#e7d7c4",
                bg="#1a120c",
                font=("Microsoft YaHei UI", 16),
            )
            tip.pack(pady=18)
            self._tips.append(tip)

            hint = tk.Label(
                window,
                text="双击屏幕关闭显示器    Ctrl+Alt+D 紧急推迟",
                fg="#b7a898",
                bg="#1a120c",
                font=("Microsoft YaHei UI", 11),
            )
            hint.pack(pady=(0, 20))

            if index == 0:
                buttons = tk.Frame(window, bg="#1a120c")
                buttons.pack()
                self._button(buttons, "紧急推迟", self._on_postpone).pack(side="left", padx=8)
                self._button(buttons, "结束休息", self._on_finish).pack(side="left", padx=8)
            self._windows.append(window)
        self._after_id = self._master.after(8000, self._rotate_tip)

    def render(self, clock: str) -> None:
        for label in self._clocks:
            if label.winfo_exists():
                label.configure(text=clock)
        for window in self._windows:
            if window.winfo_exists():
                window.lift()
                window.attributes("-topmost", True)

    def close(self) -> None:
        if self._after_id is not None:
            try:
                self._master.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        for window in self._windows:
            try:
                window.destroy()
            except tk.TclError:
                pass
        self._windows.clear()
        self._clocks.clear()
        self._tips.clear()

    def _rotate_tip(self) -> None:
        if not self._tips:
            return
        self._exercise = (self._exercise + 1) % len(EXERCISES)
        text = EXERCISES[self._exercise]
        for label in self._tips:
            if label.winfo_exists():
                label.configure(text=text)
        self._after_id = self._master.after(8000, self._rotate_tip)

    @staticmethod
    def _button(parent, text, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei UI", 12),
            fg="#1a120c",
            bg="#f3e6d4",
            activebackground="#f6c98a",
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
        )
