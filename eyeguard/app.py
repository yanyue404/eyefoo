"""把计时器、悬浮窗、休息遮罩和系统能力接在一起。

界面只负责显示和收集操作。计时规则在 engine.py，屏幕和热键在 platform_win.py。
"""

from __future__ import annotations

import argparse
import logging
import queue
import threading
import time

from eyeguard.platform import enable_dpi_awareness

enable_dpi_awareness()

import tkinter as tk

from eyeguard.config import LOG_PATH, Settings, load_settings, save_settings
from eyeguard.dialogs import ask_pin, open_settings, open_shutdown_dialog
from eyeguard.engine import REST, WORK, Engine, format_clock
from eyeguard.float_window import FloatWindow
from eyeguard.lamp import LampOverlay
from eyeguard.rest_overlay import RestOverlay
from eyeguard.skins import normalize_skin, skin_of
from eyeguard.sound import play_alert
from eyeguard import platform as platform_win


class App:
    def __init__(self, smoke: bool = False) -> None:
        self.smoke = smoke
        self.settings = load_settings()
        _configure_log()
        scheme = self.settings.scheme()
        self.engine = Engine(
            scheme.work_minutes * 60,
            scheme.rest_minutes * 60,
            self.settings.warn_seconds,
            self.settings.postpone_minutes * 60,
        )
        self._resume_or_start(time.monotonic())
        self.manual_pause = False
        self._postpones = 0
        self._busy = False
        self.hotkeys: queue.Queue[int] = queue.Queue()
        self._stop_hotkey = threading.Event()
        self._icon = None
        self._quitting = False

        self.root = tk.Tk()
        self.root.withdraw()
        self._settings_win: tk.Toplevel | None = None
        self.float = FloatWindow(self.root, self._on_command, self.settings.skin, self.settings.slice_size)
        self.float.place_initial(self.settings.float_x, self.settings.float_y)
        self.rest = RestOverlay(
            self.root,
            self.postpone,
            self.end_rest_early,
            platform_win.turn_off_display,
        )
        self.lamp = LampOverlay(self.root, lambda: self.lamp.close(), platform_win.turn_off_display)
        self._apply_display()
        if not smoke:
            self._start_hotkeys()
            self._start_tray()
        if self.engine.phase == REST:
            self.root.after(50, self._begin_rest_session)
        self._sync_float(time.monotonic())
        self.root.after(200, self._tick)
        if smoke:
            self.root.after(500, self.quit)

    def run(self) -> None:
        self.root.mainloop()

    def _resume_or_start(self, now: float) -> None:
        remaining = self.settings.rest_ends_at - time.time()
        if self.settings.resume_unfinished_rest and remaining > 1:
            self.engine.start_rest(now, remaining)
            return
        self.settings.rest_ends_at = 0.0
        self.engine.start_work(now)

    def _tick(self) -> None:
        if self._quitting:
            return
        self._drain_hotkeys()
        now = time.monotonic()
        events = self.engine.tick(now, self._should_pause())
        for event in events:
            self._handle_event(event)
        self._sync_float(now)
        if self.rest.visible:
            self.rest.render(format_clock(self.engine.remaining(now)))
            self._raise_dialogs()
        self.root.after(200, self._tick)

    def _should_pause(self) -> bool:
        if self.engine.phase not in (WORK, "paused"):
            return False
        if self.manual_pause:
            return True
        if self.settings.idle_pause_seconds > 0:
            try:
                if platform_win.get_idle_seconds() >= self.settings.idle_pause_seconds:
                    return True
            except OSError:
                logging.exception("读取空闲时间失败")
        if self.settings.pause_on_fullscreen:
            try:
                if platform_win.is_foreground_fullscreen():
                    return True
            except OSError:
                logging.exception("检测全屏窗口失败")
        return False

    def _handle_event(self, event: str) -> None:
        if event == "warn":
            play_alert(self.settings.rest_sound)
        elif event == "rest_start":
            self._postpones = 0
            self._begin_rest_session()
        elif event == "rest_end":
            self._postpones = 0
            self._finish_rest_session(play_twice=True)
        elif event == "paused":
            logging.info("计时暂停")
        elif event == "resumed":
            logging.info("计时继续")

    def _begin_rest_session(self) -> None:
        self.lamp.close()
        self.settings.rest_ends_at = time.time() + self.engine.remaining(time.monotonic())
        save_settings(self.settings)
        self.rest.show(self._areas())
        play_alert(self.settings.rest_sound)
        logging.info("开始休息")

    def _finish_rest_session(self, play_twice: bool) -> None:
        self.rest.close()
        self.settings.rest_ends_at = 0.0
        save_settings(self.settings)
        play_alert(self.settings.rest_sound)
        if play_twice:
            self.root.after(700, lambda: play_alert(self.settings.rest_sound))
        logging.info("休息结束")

    def _sync_float(self, now: float) -> None:
        remaining = self.engine.remaining(now)
        phase = self.engine.phase
        if phase == WORK and self.settings.warn_seconds and remaining <= self.settings.warn_seconds:
            shown = "warn"
        else:
            shown = phase
        clock = format_clock(remaining)
        self.float.render(clock, shown, self.settings.always_on_top)
        self.float.set_pause_label(self.manual_pause)
        if self._icon is not None:
            self._icon.title = f"护眼计时 {clock}"

    def _on_command(self, name: str) -> None:
        logging.info("执行操作 %s", name)
        actions = {
            "rest_now": self.rest_now,
            "postpone": self.postpone,
            "toggle_pause": self.toggle_pause,
            "lamp": self.toggle_lamp,
            "settings": self.show_settings,
            "shutdown": self.show_shutdown,
            "hide": self.float.withdraw,
            "show": self._show_float,
            "quit": self.quit,
            "moved": self._save_position,
            "skin": self._apply_menu_skin,
            "zoom_in": lambda: self._zoom(20),
            "zoom_out": lambda: self._zoom(-20),
            "resized": self._remember_size,
        }
        action = actions.get(name)
        if action is not None:
            action()

    def rest_now(self) -> None:
        if self.engine.phase == REST:
            return
        self.manual_pause = False
        self.engine.start_rest(time.monotonic())
        self._begin_rest_session()

    def postpone(self) -> None:
        if self._busy:
            return
        limit = self.settings.postpone_limit
        if limit and self._postpones >= limit:
            self._busy = True
            try:
                allowed = ask_pin(self.root, self.settings, "推迟休息")
            finally:
                self._busy = False
            if not allowed:
                return
        event = self.engine.postpone(time.monotonic())
        self._postpones += 1
        if event == "postponed_rest":
            self._finish_rest_session(play_twice=False)
        logging.info("推迟休息：%s", event)

    def end_rest_early(self) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            allowed = ask_pin(self.root, self.settings, "结束休息")
        finally:
            self._busy = False
        if not allowed:
            return
        if self.engine.finish_rest_early(time.monotonic()):
            self._postpones = 0
            self._finish_rest_session(play_twice=False)

    def toggle_pause(self) -> None:
        if self.engine.phase == REST:
            return
        self.manual_pause = not self.manual_pause

    def toggle_lamp(self) -> None:
        if self.rest.visible:
            return
        self.lamp.toggle(self._areas())

    def show_settings(self) -> None:
        existing = self._settings_win
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                self._settings_win = None
        if self._busy:
            return
        self._busy = True
        try:
            self._settings_win = open_settings(
                self.root,
                self.settings,
                self._preview_display,
                self._on_settings_saved,
                self.float.set_skin,
                self.float.set_size,
            )
            logging.info("打开设置")
        except Exception:
            logging.exception("打开设置失败")
        finally:
            self._busy = False

    def show_shutdown(self) -> None:
        try:
            open_shutdown_dialog(self.root)
        except Exception:
            logging.exception("打开定时关机失败")

    def _apply_menu_skin(self) -> None:
        self.settings.skin = normalize_skin(self.float.skin_var.get())
        self.float.set_skin(self.settings.skin)
        save_settings(self.settings)
        self._refresh_tray_icon()

    def _zoom(self, delta: int) -> None:
        self.float.set_size(self.float.size + delta)
        self._remember_size()

    def _remember_size(self) -> None:
        self.settings.slice_size = self.float.size
        save_settings(self.settings)

    def _preview_display(self, brightness: float, warmth: float) -> None:
        if self.smoke:
            return
        try:
            platform_win.apply_display(brightness, warmth)
        except OSError:
            logging.exception("预览亮度失败")

    def _on_settings_saved(self, settings: Settings) -> None:
        self.settings = settings
        save_settings(settings)
        try:
            platform_win.set_run_at_startup(settings.start_with_windows)
        except Exception:
            logging.exception("写入开机启动项失败")
        scheme = settings.scheme()
        self.engine.apply_durations(
            scheme.work_minutes * 60,
            scheme.rest_minutes * 60,
            settings.warn_seconds,
            settings.postpone_minutes * 60,
            time.monotonic(),
        )
        self._postpones = 0
        self.float.set_skin(settings.skin)
        self.float.set_size(settings.slice_size)
        self._refresh_tray_icon()
        if self.engine.phase == REST:
            self._begin_rest_session()
        else:
            self.rest.close()
            self.settings.rest_ends_at = 0.0
            save_settings(self.settings)
        self._apply_display()

    def _apply_display(self) -> None:
        if self.smoke:
            return
        try:
            if self.settings.brightness >= 0.999 and self.settings.warmth <= 0.001:
                platform_win.restore_display()
                return
            if not platform_win.apply_display(self.settings.brightness, self.settings.warmth):
                logging.warning("显卡没有接受伽马表，亮度或暖色可能没有变化")
        except OSError:
            logging.exception("调整屏幕失败")

    def _save_position(self) -> None:
        self.settings.float_x = self.float.winfo_x()
        self.settings.float_y = self.float.winfo_y()
        save_settings(self.settings)

    def _areas(self) -> list[tuple[int, int, int, int]]:
        return [
            (monitor.left, monitor.top, monitor.width, monitor.height)
            for monitor in platform_win.monitors()
        ]

    def _raise_dialogs(self) -> None:
        covered = set(self.rest._windows)
        for child in self.root.winfo_children():
            if child is self.float or child in covered:
                continue
            if not isinstance(child, tk.Toplevel):
                continue
            try:
                if child.winfo_exists() and child.winfo_viewable():
                    child.attributes("-topmost", True)
                    child.lift()
            except tk.TclError:
                continue

    def _drain_hotkeys(self) -> None:
        while True:
            try:
                ident = self.hotkeys.get_nowait()
            except queue.Empty:
                return
            if ident == platform_win.HOTKEY_POSTPONE:
                self.postpone()
            elif ident == platform_win.HOTKEY_LAMP:
                self.toggle_lamp()

    def _start_hotkeys(self) -> None:
        def runner() -> None:
            note = platform_win.hotkey_loop(self._stop_hotkey, self.hotkeys.put)
            if note:
                logging.warning(note)

        threading.Thread(target=runner, name="eyeguard-hotkey", daemon=True).start()

    def _start_tray(self) -> None:
        try:
            import pystray
        except ImportError:
            logging.warning("没有安装 pystray 和 pillow，托盘图标不可用。可执行 pip install -r requirements.txt")
            return
        try:
            image = _tray_image(self.settings.skin)
        except Exception:
            logging.exception("托盘图标绘制失败")
            return

        def item(label: str, command: str):
            def activate(_icon, _item):
                self.root.after(0, lambda: self._on_command(command))

            return pystray.MenuItem(label, activate)

        self._icon = pystray.Icon(
            "eyeguard",
            image,
            "护眼计时",
            pystray.Menu(
                item("显示悬浮窗", "show"),
                item("立即休息", "rest_now"),
                item("推迟休息", "postpone"),
                item("关灯", "lamp"),
                item("设置", "settings"),
                item("退出", "quit"),
            ),
        )
        threading.Thread(target=self._icon.run, name="eyeguard-tray", daemon=True).start()

    def _refresh_tray_icon(self) -> None:
        if self._icon is None:
            return
        try:
            self._icon.icon = _tray_image(self.settings.skin)
        except Exception:
            logging.exception("更新托盘图标失败")

    def _show_float(self) -> None:
        self.float.deiconify()
        self.float.lift()
        self.float.attributes("-topmost", self.settings.always_on_top)

    def quit(self) -> None:
        if self._quitting:
            return
        if not self.smoke:
            if self._busy:
                return
            self._busy = True
            try:
                allowed = ask_pin(self.root, self.settings, "退出护眼计时")
            finally:
                self._busy = False
            if not allowed:
                return
        self._quitting = True
        self._stop_hotkey.set()
        self.rest.close()
        self.lamp.close()
        if not self.smoke:
            try:
                platform_win.restore_display()
            except OSError:
                logging.exception("恢复屏幕失败")
        if self.engine.phase == REST and self.settings.resume_unfinished_rest:
            self.settings.rest_ends_at = time.time() + self.engine.remaining(time.monotonic())
        else:
            self.settings.rest_ends_at = 0.0
        save_settings(self.settings)
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                logging.exception("关闭托盘失败")
        self.root.after(50, self._destroy)

    def _destroy(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            return


def _tray_image(skin: str):
    from PIL import Image, ImageDraw

    palette = skin_of(skin)
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    rind = _hex_rgb(palette.rind)
    pulp = _hex_rgb(palette.pulp)
    core = _hex_rgb(palette.core)
    draw.ellipse((2, 2, 62, 62), fill=rind + (255,))
    draw.ellipse((10, 10, 54, 54), fill=pulp + (255,))
    draw.ellipse((24, 24, 40, 40), fill=core + (255,))
    return image


def _hex_rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _configure_log() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
        force=True,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="护眼计时")
    parser.add_argument("--smoke", action="store_true", help="打开界面后立即退出，供自检使用")
    args = parser.parse_args(argv)
    App(smoke=args.smoke).run()


if __name__ == "__main__":
    main()
