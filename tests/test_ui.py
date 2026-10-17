import unittest

from eyeguard.platform_win import enable_dpi_awareness

enable_dpi_awareness()

import tkinter as tk

from eyeguard.config import Settings
from eyeguard.dialogs import open_settings, open_shutdown_dialog
from eyeguard.float_window import FloatWindow
from eyeguard.lamp import LampOverlay
from eyeguard.rest_overlay import RestOverlay


class UiBuildTest(unittest.TestCase):
    def test_windows_can_be_created_and_closed(self) -> None:
        root = tk.Tk()
        root.withdraw()
        try:
            floating = FloatWindow(root, lambda _name: None)
            floating.render("25:00", "work", True)
            floating.place_initial(80, 80)
            floating.render("00:20", "warn", True)
            floating.set_pause_label(True)

            rest = RestOverlay(root, lambda: None, lambda: None, lambda: None)
            rest.show([(80, 80, 320, 180)])
            rest.render("04:59")
            self.assertTrue(rest.visible)
            rest.close()
            self.assertFalse(rest.visible)

            lamp = LampOverlay(root, lambda: None, lambda: None)
            self.assertTrue(lamp.toggle([(80, 80, 200, 120)]))
            self.assertTrue(lamp.visible)
            lamp.close()

            floating._menu_open = True
            floating.render("00:01", "warn", False)
            floating.set_pause_label(False)
            self.assertEqual(floating._clock, "00:20")
            self.assertTrue(floating._pause_shown)
            self.assertTrue(floating._topmost)
            floating._menu_open = False
            floating._flush_pending()
            self.assertEqual(floating._clock, "00:01")
            self.assertEqual(floating._phase, "warn")
            self.assertFalse(floating._pause_shown)
            self.assertFalse(floating._topmost)

            calls: list[str] = []
            floating._on_command = calls.append
            floating.menu.invoke(0)
            floating.menu.invoke(1)
            self.assertEqual(calls, [])
            root.update()
            self.assertEqual(calls, ["rest_now", "postpone"])
            root.update()
            self.assertEqual(calls, ["rest_now", "postpone"])
            floating.set_size(200)
            self.assertEqual(floating.size, 200)

            floating.set_skin("orange")
            floating.render("24:58", "paused", True)
            self.assertTrue(floating.canvas.find_withtag("slice"))

            settings = Settings()
            shutdown = open_shutdown_dialog(root)
            dialog = open_settings(root, settings, lambda *_args: None, lambda _settings: None)
            root.update()
            self.assertIsNotNone(dialog)
            self.assertTrue(shutdown.winfo_viewable())
            self.assertTrue(dialog.winfo_viewable())
            self.assertGreater(dialog.winfo_width(), 240)
            self.assertGreater(dialog.winfo_rootx(), -20)
            self.assertGreater(dialog.winfo_rooty(), -20)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
