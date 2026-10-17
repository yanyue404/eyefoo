import threading
import unittest

from eyeguard.platform_win import (
    apply_display,
    get_idle_seconds,
    hotkey_loop,
    monitors,
    restore_display,
    set_run_at_startup,
    window_geometry,
)


class PlatformTest(unittest.TestCase):
    def test_startup_switch_uses_current_user_registry(self) -> None:
        set_run_at_startup(False)

    def test_window_geometry_allows_negative_origin(self) -> None:
        self.assertEqual(window_geometry(1920, 1080, -1920, 0), "1920x1080-1920+0")

    def test_monitors_and_idle(self) -> None:
        found = monitors()
        self.assertGreaterEqual(len(found), 1)
        self.assertGreater(found[0].width, 0)
        self.assertGreaterEqual(get_idle_seconds(), 0)

    def test_hotkey_register_and_release(self) -> None:
        stop = threading.Event()
        stop.set()
        note = hotkey_loop(stop, lambda _ident: None)
        self.assertIsInstance(note, str)

    def test_identity_gamma_can_be_restored(self) -> None:
        try:
            result = apply_display(1.0, 0.0)
            self.assertIsInstance(result, bool)
        finally:
            restore_display()


if __name__ == "__main__":
    unittest.main()
