"""休息提示音。指定 wav 时播放文件，否则用系统提示音。"""

from __future__ import annotations

import winsound
from pathlib import Path


def play_alert(path: str) -> None:
    file_path = Path(path) if path else None
    if file_path and file_path.is_file():
        winsound.PlaySound(str(file_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    winsound.MessageBeep(winsound.MB_ICONASTERISK)
