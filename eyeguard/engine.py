"""休息计时状态机。

只依赖传入的时间戳，不读系统时钟，方便单测，也避免把界面和计时缠在一起。
调用方每 200ms 左右调用一次 tick，并根据返回的事件切界面。
"""

from __future__ import annotations

WORK = "work"
REST = "rest"
PAUSED = "paused"


class Engine:
    def __init__(
        self,
        work_seconds: float,
        rest_seconds: float,
        warn_seconds: float,
        postpone_seconds: float,
    ) -> None:
        self.work_seconds = float(work_seconds)
        self.rest_seconds = float(rest_seconds)
        self.warn_seconds = float(warn_seconds)
        self.postpone_seconds = float(postpone_seconds)
        self.phase = WORK
        self.deadline = 0.0
        self._paused_left = 0.0
        self._warned = False

    def start_work(self, now: float, seconds: float | None = None) -> None:
        self.phase = WORK
        self.deadline = now + (self.work_seconds if seconds is None else float(seconds))
        self._paused_left = 0.0
        self._warned = False

    def start_rest(self, now: float, seconds: float | None = None) -> None:
        self.phase = REST
        self.deadline = now + (self.rest_seconds if seconds is None else float(seconds))
        self._paused_left = 0.0
        self._warned = False

    def remaining(self, now: float) -> float:
        if self.phase == PAUSED:
            return max(0.0, self._paused_left)
        return max(0.0, self.deadline - now)

    def tick(self, now: float, activity_paused: bool) -> list[str]:
        """推进状态。activity_paused 只在工作阶段生效，休息不会被空闲检测打断。"""
        events: list[str] = []
        if self.phase == WORK:
            if activity_paused:
                self._paused_left = max(0.0, self.deadline - now)
                self.phase = PAUSED
                events.append("paused")
                return events
            left = self.deadline - now
            if self.warn_seconds > 0 and left <= self.warn_seconds and left > 0 and not self._warned:
                self._warned = True
                events.append("warn")
            if now >= self.deadline:
                self.start_rest(now)
                events.append("rest_start")
            return events

        if self.phase == PAUSED:
            if not activity_paused:
                self.deadline = now + self._paused_left
                self.phase = WORK
                events.append("resumed")
            return events

        if now >= self.deadline:
            self.start_work(now)
            events.append("rest_end")
        return events

    def postpone(self, now: float) -> str:
        """推迟休息。

        工作或暂停中：把本轮剩余时间延长 postpone_seconds。
        休息中：结束本轮休息，只给一段推迟时长，到点再次休息。
        """
        if self.phase == REST:
            self.start_work(now, self.postpone_seconds)
            return "postponed_rest"
        if self.phase == PAUSED:
            self._paused_left += self.postpone_seconds
            self._warned = False
            return "postponed"
        self.deadline += self.postpone_seconds
        self._warned = False
        return "postponed"

    def finish_rest_early(self, now: float) -> bool:
        if self.phase != REST:
            return False
        self.start_work(now)
        return True

    def apply_durations(
        self,
        work_seconds: float,
        rest_seconds: float,
        warn_seconds: float,
        postpone_seconds: float,
        now: float,
    ) -> None:
        self.work_seconds = float(work_seconds)
        self.rest_seconds = float(rest_seconds)
        self.warn_seconds = float(warn_seconds)
        self.postpone_seconds = float(postpone_seconds)
        if self.phase == WORK:
            self.start_work(now)
        elif self.phase == REST:
            self.start_rest(now)
        else:
            self._paused_left = self.work_seconds
            self._warned = False


def format_clock(seconds: float) -> str:
    whole = max(0, int(seconds + 0.999))
    minutes, secs = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
