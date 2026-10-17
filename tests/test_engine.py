import unittest

from eyeguard.engine import PAUSED, REST, WORK, Engine, format_clock


class EngineTest(unittest.TestCase):
    def test_work_warns_then_rests_then_returns(self) -> None:
        engine = Engine(10, 5, 3, 60)
        engine.start_work(0)
        self.assertEqual(engine.tick(6, False), [])
        self.assertEqual(engine.tick(7, False), ["warn"])
        self.assertEqual(engine.tick(9, False), [])
        self.assertEqual(engine.tick(10, False), ["rest_start"])
        self.assertEqual(engine.phase, REST)
        self.assertEqual(engine.tick(15, False), ["rest_end"])
        self.assertEqual(engine.phase, WORK)
        self.assertAlmostEqual(engine.remaining(15), 10)

    def test_pause_freezes_remaining(self) -> None:
        engine = Engine(10, 5, 3, 60)
        engine.start_work(0)
        self.assertEqual(engine.tick(4, True), ["paused"])
        self.assertEqual(engine.phase, PAUSED)
        self.assertAlmostEqual(engine.remaining(100), 6)
        self.assertEqual(engine.tick(100, True), [])
        self.assertEqual(engine.tick(100, False), ["resumed"])
        self.assertAlmostEqual(engine.remaining(100), 6)
        self.assertEqual(engine.tick(106, False), ["rest_start"])

    def test_postpone_extends_work_and_interrupts_rest(self) -> None:
        engine = Engine(10, 5, 3, 60)
        engine.start_work(0)
        engine.tick(8, False)
        self.assertEqual(engine.postpone(8), "postponed")
        self.assertAlmostEqual(engine.remaining(8), 62)

        engine.start_rest(0)
        self.assertEqual(engine.postpone(1), "postponed_rest")
        self.assertEqual(engine.phase, WORK)
        self.assertAlmostEqual(engine.remaining(1), 60)

    def test_idle_does_not_pause_rest(self) -> None:
        engine = Engine(10, 5, 3, 60)
        engine.start_rest(0)
        self.assertEqual(engine.tick(1, True), [])
        self.assertEqual(engine.phase, REST)

    def test_format_clock_rounds_up_whole_seconds(self) -> None:
        self.assertEqual(format_clock(2700), "45:00")
        self.assertEqual(format_clock(0.2), "00:01")
        self.assertEqual(format_clock(0), "00:00")
        self.assertEqual(format_clock(3661), "1:01:01")


if __name__ == "__main__":
    unittest.main()
