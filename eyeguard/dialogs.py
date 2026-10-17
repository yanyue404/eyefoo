"""设置、密码和定时关机对话框。"""

from __future__ import annotations

import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from eyeguard.config import Scheme, Settings, set_pin, verify_pin
from eyeguard.skins import MAX_SLICE_SIZE, MIN_SLICE_SIZE, clamp_size, normalize_skin


def ask_pin(master: tk.Misc, settings: Settings, title: str) -> bool:
    if not settings.pin_hash:
        return True
    dialog = tk.Toplevel(master)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.configure(bg="#f6f1ea")
    result = {"ok": False}

    tk.Label(dialog, text="请输入密码", bg="#f6f1ea", font=("Microsoft YaHei UI", 11)).pack(padx=24, pady=(18, 8))
    value = tk.StringVar()
    entry = tk.Entry(dialog, textvariable=value, show="*", width=24, font=("Microsoft YaHei UI", 12))
    entry.pack(padx=24)
    entry.focus_set()

    def accept(_event=None) -> None:
        if verify_pin(settings, value.get()):
            result["ok"] = True
            dialog.destroy()
            return
        messagebox.showwarning("密码不对", "请再试一次。", parent=dialog)
        value.set("")

    def cancel() -> None:
        dialog.destroy()

    buttons = tk.Frame(dialog, bg="#f6f1ea")
    buttons.pack(pady=16)
    tk.Button(buttons, text="确定", command=accept, width=8).pack(side="left", padx=6)
    tk.Button(buttons, text="取消", command=cancel, width=8).pack(side="left", padx=6)
    dialog.bind("<Return>", accept)
    dialog.bind("<Escape>", lambda _event: cancel())
    reveal(dialog)
    dialog.grab_set()
    dialog.wait_window()
    return result["ok"]


def open_settings(
    master: tk.Misc,
    settings: Settings,
    on_preview,
    on_saved,
    on_skin=None,
    on_size=None,
) -> tk.Toplevel | None:
    if not ask_pin(master, settings, "打开设置"):
        return None
    dialog = tk.Toplevel(master)
    dialog.title("亮度与方案")
    dialog.resizable(False, False)
    dialog.configure(bg="#f6f1ea")

    original_brightness = settings.brightness
    original_warmth = settings.warmth
    original_skin = normalize_skin(settings.skin)
    original_size = clamp_size(settings.slice_size)
    schemes = [Scheme(item.name, item.work_minutes, item.rest_minutes) for item in settings.schemes]

    pad = {"padx": 12, "pady": 4, "sticky": "w"}
    skin_var = tk.StringVar(value=original_skin)

    def preview_skin() -> None:
        if on_skin is not None:
            on_skin(normalize_skin(skin_var.get()))

    skin_bar = tk.Frame(dialog, bg="#f6f1ea")
    skin_bar.pack(fill="x", padx=16, pady=(14, 0))
    tk.Label(skin_bar, text="皮肤", bg="#f6f1ea", font=("Microsoft YaHei UI", 10)).pack(side="left")
    tk.Radiobutton(
        skin_bar,
        text="青柠",
        variable=skin_var,
        value="green",
        command=preview_skin,
        bg="#f6f1ea",
        font=("Microsoft YaHei UI", 10),
    ).pack(side="left", padx=(12, 0))
    tk.Radiobutton(
        skin_bar,
        text="橙片",
        variable=skin_var,
        value="orange",
        command=preview_skin,
        bg="#f6f1ea",
        font=("Microsoft YaHei UI", 10),
    ).pack(side="left", padx=(8, 0))

    size_var = tk.IntVar(value=original_size)

    def preview_size(value) -> None:
        if on_size is not None:
            on_size(clamp_size(value))

    size_row = tk.Frame(dialog, bg="#f6f1ea")
    size_row.pack(fill="x", padx=16, pady=(6, 0))
    tk.Label(size_row, text="大小", bg="#f6f1ea", font=("Microsoft YaHei UI", 10)).pack(side="left")
    tk.Scale(
        size_row,
        from_=MIN_SLICE_SIZE,
        to=MAX_SLICE_SIZE,
        orient="horizontal",
        variable=size_var,
        resolution=20,
        length=220,
        bg="#f6f1ea",
        highlightthickness=0,
        command=preview_size,
    ).pack(side="left", padx=(12, 0))

    form = tk.Frame(dialog, bg="#f6f1ea")
    form.pack(fill="both", expand=True, padx=8, pady=8)

    tk.Label(form, text="方案", bg="#f6f1ea").grid(row=0, column=0, **pad)
    scheme_names = tk.StringVar()
    scheme_box = ttk.Combobox(form, textvariable=scheme_names, state="readonly", width=22)
    scheme_box.grid(row=0, column=1, **pad)

    name_var = tk.StringVar()
    work_var = tk.IntVar()
    rest_var = tk.IntVar()
    warn_var = tk.IntVar(value=settings.warn_seconds)
    idle_var = tk.IntVar(value=settings.idle_pause_seconds)
    postpone_var = tk.IntVar(value=settings.postpone_minutes)
    limit_var = tk.IntVar(value=settings.postpone_limit)
    brightness_var = tk.DoubleVar(value=settings.brightness * 100)
    warmth_var = tk.DoubleVar(value=settings.warmth * 100)
    sound_var = tk.StringVar(value=settings.rest_sound)
    pin_var = tk.StringVar()
    fullscreen_var = tk.BooleanVar(value=settings.pause_on_fullscreen)
    startup_var = tk.BooleanVar(value=settings.start_with_windows)
    top_var = tk.BooleanVar(value=settings.always_on_top)
    resume_var = tk.BooleanVar(value=settings.resume_unfinished_rest)

    selected = {"index": 0}
    updating = {"on": False}

    def refresh_names(select: int) -> None:
        updating["on"] = True
        try:
            scheme_box["values"] = [item.name for item in schemes]
            if not schemes:
                return
            select = max(0, min(select, len(schemes) - 1))
            selected["index"] = select
            scheme_box.current(select)
            load_scheme(select)
        finally:
            updating["on"] = False

    def load_scheme(index: int) -> None:
        scheme = schemes[index]
        name_var.set(scheme.name)
        scheme_names.set(scheme.name)
        work_var.set(scheme.work_minutes)
        rest_var.set(scheme.rest_minutes)

    def store_current() -> None:
        index = selected["index"]
        if index < 0 or index >= len(schemes):
            return
        schemes[index].name = name_var.get().strip() or schemes[index].name
        schemes[index].work_minutes = _safe_int(_read_var(work_var), schemes[index].work_minutes)
        schemes[index].rest_minutes = _safe_int(_read_var(rest_var), schemes[index].rest_minutes)
        schemes[index].clamp()
        scheme_box["values"] = [item.name for item in schemes]

    def on_scheme_change(_event=None) -> None:
        if updating["on"]:
            return
        new_index = scheme_box.current()
        store_current()
        refresh_names(new_index)

    scheme_box.bind("<<ComboboxSelected>>", on_scheme_change)
    refresh_names(settings.active_scheme)

    _labeled_entry(form, 1, "方案名称", name_var)
    _labeled_spin(form, 2, "工作分钟", work_var, 1, 180)
    _labeled_spin(form, 3, "休息分钟", rest_var, 1, 60)
    _labeled_spin(form, 4, "提前提示秒", warn_var, 0, 180)
    _labeled_spin(form, 5, "无操作暂停秒", idle_var, 0, 3600)
    _labeled_spin(form, 6, "推迟分钟", postpone_var, 1, 60)
    _labeled_spin(form, 7, "每轮推迟次数", limit_var, 0, 20)

    tk.Label(form, text="亮度", bg="#f6f1ea").grid(row=8, column=0, **pad)
    brightness = tk.Scale(
        form,
        from_=30,
        to=100,
        orient="horizontal",
        variable=brightness_var,
        length=220,
        bg="#f6f1ea",
        highlightthickness=0,
        command=lambda _value: on_preview(brightness_var.get() / 100, warmth_var.get() / 100),
    )
    brightness.grid(row=8, column=1, **pad)

    tk.Label(form, text="暖色", bg="#f6f1ea").grid(row=9, column=0, **pad)
    warmth = tk.Scale(
        form,
        from_=0,
        to=100,
        orient="horizontal",
        variable=warmth_var,
        length=220,
        bg="#f6f1ea",
        highlightthickness=0,
        command=lambda _value: on_preview(brightness_var.get() / 100, warmth_var.get() / 100),
    )
    warmth.grid(row=9, column=1, **pad)

    tk.Label(form, text="提示音 wav", bg="#f6f1ea").grid(row=10, column=0, **pad)
    sound_row = tk.Frame(form, bg="#f6f1ea")
    sound_row.grid(row=10, column=1, sticky="w", padx=12, pady=4)
    tk.Entry(sound_row, textvariable=sound_var, width=24).pack(side="left")

    def browse() -> None:
        chosen = filedialog.askopenfilename(
            parent=dialog,
            title="选择提示音",
            filetypes=[("WAV", "*.wav"), ("全部文件", "*.*")],
        )
        if chosen:
            sound_var.set(chosen)

    tk.Button(sound_row, text="浏览", command=browse).pack(side="left", padx=6)

    tk.Label(form, text="新密码", bg="#f6f1ea").grid(row=11, column=0, **pad)
    pin_entry = tk.Entry(form, textvariable=pin_var, show="*", width=24)
    pin_entry.grid(row=11, column=1, **pad)
    tk.Label(form, text="留空表示不修改。输入 - 清除密码。", bg="#f6f1ea", fg="#6d6258").grid(
        row=12, column=1, sticky="w", padx=12
    )

    checks = tk.Frame(form, bg="#f6f1ea")
    checks.grid(row=13, column=0, columnspan=2, sticky="w", padx=12, pady=8)
    tk.Checkbutton(checks, text="全屏时暂停", variable=fullscreen_var, bg="#f6f1ea").pack(anchor="w")
    tk.Checkbutton(checks, text="悬浮窗置顶", variable=top_var, bg="#f6f1ea").pack(anchor="w")
    tk.Checkbutton(checks, text="登录后自动启动", variable=startup_var, bg="#f6f1ea").pack(anchor="w")
    tk.Checkbutton(checks, text="退出时如果还在休息，下次打开继续", variable=resume_var, bg="#f6f1ea").pack(anchor="w")

    def add_scheme() -> None:
        store_current()
        schemes.append(Scheme(f"方案 {len(schemes) + 1}", 45, 5))
        refresh_names(len(schemes) - 1)

    def delete_scheme() -> None:
        if len(schemes) <= 1:
            messagebox.showinfo("至少保留一个方案", "不能把方案全部删掉。", parent=dialog)
            return
        index = max(0, scheme_box.current())
        del schemes[index]
        refresh_names(min(index, len(schemes) - 1))

    scheme_buttons = tk.Frame(form, bg="#f6f1ea")
    scheme_buttons.grid(row=14, column=1, sticky="w", padx=12)
    tk.Button(scheme_buttons, text="新增方案", command=add_scheme).pack(side="left", padx=(0, 6))
    tk.Button(scheme_buttons, text="删除方案", command=delete_scheme).pack(side="left")

    def save() -> None:
        store_current()
        settings.schemes = schemes
        settings.active_scheme = max(0, scheme_box.current())
        settings.warn_seconds = _safe_int(_read_var(warn_var), settings.warn_seconds)
        settings.idle_pause_seconds = _safe_int(_read_var(idle_var), settings.idle_pause_seconds)
        settings.postpone_minutes = _safe_int(_read_var(postpone_var), settings.postpone_minutes)
        settings.postpone_limit = _safe_int(_read_var(limit_var), settings.postpone_limit)
        settings.brightness = brightness_var.get() / 100
        settings.warmth = warmth_var.get() / 100
        settings.rest_sound = sound_var.get().strip()
        settings.pause_on_fullscreen = fullscreen_var.get()
        settings.always_on_top = top_var.get()
        settings.start_with_windows = startup_var.get()
        settings.resume_unfinished_rest = resume_var.get()
        settings.skin = normalize_skin(skin_var.get())
        settings.slice_size = clamp_size(_read_var(size_var))
        pin = pin_var.get().strip()
        if pin == "-":
            set_pin(settings, "")
        elif pin:
            set_pin(settings, pin)
        settings.clamp()
        on_saved(settings)
        dialog.destroy()

    def cancel() -> None:
        on_preview(original_brightness, original_warmth)
        if on_skin is not None:
            on_skin(original_skin)
        if on_size is not None:
            on_size(original_size)
        dialog.destroy()

    buttons = tk.Frame(dialog, bg="#f6f1ea")
    buttons.pack(pady=(0, 12))
    tk.Button(buttons, text="保存", command=save, width=10).pack(side="left", padx=6)
    tk.Button(buttons, text="取消", command=cancel, width=10).pack(side="left", padx=6)
    dialog.protocol("WM_DELETE_WINDOW", cancel)
    reveal(dialog)
    return dialog


def open_shutdown_dialog(master: tk.Misc) -> tk.Toplevel:
    dialog = tk.Toplevel(master)
    dialog.title("定时关机")
    dialog.resizable(False, False)
    dialog.configure(bg="#f6f1ea")

    tk.Label(
        dialog,
        text="到达时间后，Windows 会关闭这台电脑。",
        bg="#f6f1ea",
        font=("Microsoft YaHei UI", 10),
    ).pack(padx=18, pady=(16, 8))
    row = tk.Frame(dialog, bg="#f6f1ea")
    row.pack()
    tk.Label(row, text="分钟", bg="#f6f1ea").pack(side="right")
    minutes = tk.IntVar(value=30)
    tk.Spinbox(row, from_=1, to=720, textvariable=minutes, width=8).pack(side="left", padx=6)

    status = tk.Label(dialog, text="", bg="#f6f1ea", fg="#6d6258")
    status.pack(pady=8)

    def plan() -> None:
        amount = _safe_int(_read_var(minutes), 30)
        amount = max(1, min(720, amount))
        subprocess.run(
            ["shutdown", "/s", "/t", str(amount * 60), "/c", "护眼计时：到达计划时间，电脑将关闭。"],
            check=False,
        )
        status.configure(text=f"已计划 {amount} 分钟后关机")

    def cancel_plan() -> None:
        subprocess.run(["shutdown", "/a"], check=False)
        status.configure(text="已取消关机计划")

    buttons = tk.Frame(dialog, bg="#f6f1ea")
    buttons.pack(pady=(0, 16))
    tk.Button(buttons, text="开始计时关机", command=plan).pack(side="left", padx=6)
    tk.Button(buttons, text="取消关机", command=cancel_plan).pack(side="left", padx=6)
    reveal(dialog)
    return dialog


def reveal(dialog: tk.Toplevel) -> None:
    """把对话框放到屏幕中间并显示出来。

    主窗口是隐藏的。对隐藏窗口设置 transient 时，Windows 不会把对话框画出来。
    """
    dialog.update_idletasks()
    width = max(dialog.winfo_reqwidth(), 1)
    height = max(dialog.winfo_reqheight(), 1)
    x = max(0, (dialog.winfo_screenwidth() - width) // 2)
    y = max(0, (dialog.winfo_screenheight() - height) // 5)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    parent = dialog.master
    try:
        if parent is not None and bool(parent.winfo_viewable()):
            dialog.transient(parent)
    except tk.TclError:
        pass
    dialog.attributes("-topmost", True)
    dialog.deiconify()
    dialog.lift()
    dialog.focus_force()


def _labeled_entry(form, row: int, label: str, variable) -> None:
    tk.Label(form, text=label, bg="#f6f1ea").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    tk.Entry(form, textvariable=variable, width=24).grid(row=row, column=1, padx=12, pady=4, sticky="w")


def _labeled_spin(form, row: int, label: str, variable, low: int, high: int) -> None:
    tk.Label(form, text=label, bg="#f6f1ea").grid(row=row, column=0, padx=12, pady=4, sticky="w")
    tk.Spinbox(form, from_=low, to=high, textvariable=variable, width=22).grid(
        row=row, column=1, padx=12, pady=4, sticky="w"
    )


def _read_var(variable):
    try:
        return variable.get()
    except (tk.TclError, ValueError):
        return None


def _safe_int(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, tk.TclError):
        return fallback
