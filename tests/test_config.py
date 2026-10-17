import tempfile
import unittest
from pathlib import Path

import eyeguard.config as config
from eyeguard.config import Settings, set_pin, verify_pin


class ConfigTest(unittest.TestCase):
    def test_pin_and_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old_dir, old_path = config.DATA_DIR, config.CONFIG_PATH
            config.DATA_DIR = root
            config.CONFIG_PATH = root / "config.json"
            try:
                settings = Settings()
                settings.schemes[0].name = "办公"
                settings.brightness = 0.8
                settings.warmth = 0.4
                settings.skin = "orange"
                set_pin(settings, "2468")
                config.save_settings(settings)
                loaded = config.load_settings()
                self.assertEqual(loaded.schemes[0].name, "办公")
                self.assertAlmostEqual(loaded.brightness, 0.8)
                self.assertAlmostEqual(loaded.warmth, 0.4)
                self.assertEqual(loaded.skin, "orange")
                self.assertTrue(verify_pin(loaded, "2468"))
                self.assertFalse(verify_pin(loaded, "0000"))
                set_pin(loaded, "")
                self.assertTrue(verify_pin(loaded, "随便"))
            finally:
                config.DATA_DIR = old_dir
                config.CONFIG_PATH = old_path

    def test_clamp_rejects_zero_minutes(self) -> None:
        settings = Settings()
        settings.schemes[0].work_minutes = 0
        settings.schemes[0].rest_minutes = 999
        settings.brightness = 0.01
        settings.skin = "nope"
        settings.clamp()
        self.assertEqual(settings.schemes[0].work_minutes, 1)
        self.assertEqual(settings.schemes[0].rest_minutes, 60)
        self.assertAlmostEqual(settings.brightness, 0.3)
        self.assertEqual(settings.skin, "green")
        settings.slice_size = 80
        settings.clamp()
        self.assertEqual(settings.slice_size, 160)


if __name__ == "__main__":
    unittest.main()
