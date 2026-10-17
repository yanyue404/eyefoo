"""配置读写。时长、色温、密码哈希都放在 data/config.json，方便直接改。"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from eyeguard.skins import clamp_size, normalize_skin

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_PATH = DATA_DIR / "eyeguard.log"


@dataclass
class Scheme:
    name: str
    work_minutes: int
    rest_minutes: int

    def clamp(self) -> None:
        self.work_minutes = _clamp_int(self.work_minutes, 1, 180)
        self.rest_minutes = _clamp_int(self.rest_minutes, 1, 60)
        self.name = (self.name or "未命名").strip()[:40]


def default_schemes() -> list[Scheme]:
    return [
        Scheme("标准 45/5", 45, 5),
        Scheme("短时 25/5", 25, 5),
        Scheme("长时 60/10", 60, 10),
    ]


@dataclass
class Settings:
    schemes: list[Scheme] = field(default_factory=default_schemes)
    active_scheme: int = 0
    warn_seconds: int = 20
    idle_pause_seconds: int = 180
    pause_on_fullscreen: bool = True
    postpone_minutes: int = 5
    postpone_limit: int = 3
    brightness: float = 1.0
    warmth: float = 0.0
    rest_sound: str = ""
    pin_hash: str = ""
    pin_salt: str = ""
    start_with_windows: bool = False
    always_on_top: bool = True
    skin: str = "green"
    slice_size: int = 240
    resume_unfinished_rest: bool = False
    rest_ends_at: float = 0.0
    float_x: int | None = None
    float_y: int | None = None

    def scheme(self) -> Scheme:
        if not self.schemes:
            self.schemes = default_schemes()
        self.active_scheme = _clamp_int(self.active_scheme, 0, len(self.schemes) - 1)
        return self.schemes[self.active_scheme]

    def clamp(self) -> None:
        if not self.schemes:
            self.schemes = default_schemes()
        for scheme in self.schemes:
            scheme.clamp()
        self.active_scheme = _clamp_int(self.active_scheme, 0, len(self.schemes) - 1)
        self.warn_seconds = _clamp_int(self.warn_seconds, 0, 180)
        self.idle_pause_seconds = _clamp_int(self.idle_pause_seconds, 0, 3600)
        self.postpone_minutes = _clamp_int(self.postpone_minutes, 1, 60)
        self.postpone_limit = _clamp_int(self.postpone_limit, 0, 20)
        self.brightness = min(1.0, max(0.3, float(self.brightness)))
        self.warmth = min(1.0, max(0.0, float(self.warmth)))
        self.skin = normalize_skin(self.skin)
        self.slice_size = clamp_size(self.slice_size)
        self.rest_sound = str(self.rest_sound or "")
        self.rest_ends_at = float(self.rest_ends_at or 0)


def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        settings = Settings()
        save_settings(settings)
        return settings
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    schemes = []
    for item in raw.get("schemes") or []:
        if not isinstance(item, dict):
            continue
        schemes.append(
            Scheme(
                str(item.get("name") or "未命名"),
                int(item.get("work_minutes") or 45),
                int(item.get("rest_minutes") or 5),
            )
        )
    settings = Settings(
        schemes=schemes or default_schemes(),
        active_scheme=int(raw.get("active_scheme") or 0),
        warn_seconds=int(raw.get("warn_seconds") or 0),
        idle_pause_seconds=int(raw.get("idle_pause_seconds") or 0),
        pause_on_fullscreen=bool(raw.get("pause_on_fullscreen", True)),
        postpone_minutes=int(raw.get("postpone_minutes") or 5),
        postpone_limit=int(raw.get("postpone_limit") if raw.get("postpone_limit") is not None else 3),
        brightness=float(raw.get("brightness") if raw.get("brightness") is not None else 1),
        warmth=float(raw.get("warmth") or 0),
        rest_sound=str(raw.get("rest_sound") or ""),
        pin_hash=str(raw.get("pin_hash") or ""),
        pin_salt=str(raw.get("pin_salt") or ""),
        start_with_windows=bool(raw.get("start_with_windows", False)),
        always_on_top=bool(raw.get("always_on_top", True)),
        skin=str(raw.get("skin") or "green"),
        slice_size=int(raw.get("slice_size") or 240),
        resume_unfinished_rest=bool(raw.get("resume_unfinished_rest", False)),
        rest_ends_at=float(raw.get("rest_ends_at") or 0),
        float_x=_optional_int(raw.get("float_x")),
        float_y=_optional_int(raw.get("float_y")),
    )
    settings.clamp()
    return settings


def save_settings(settings: Settings) -> None:
    settings.clamp()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def set_pin(settings: Settings, pin: str) -> None:
    pin = pin.strip()
    if not pin:
        settings.pin_hash = ""
        settings.pin_salt = ""
        return
    salt = os.urandom(16)
    settings.pin_salt = salt.hex()
    settings.pin_hash = _hash_pin(pin, salt)


def verify_pin(settings: Settings, pin: str) -> bool:
    if not settings.pin_hash:
        return True
    try:
        salt = bytes.fromhex(settings.pin_salt)
    except ValueError:
        return False
    digest = _hash_pin(pin.strip(), salt)
    return hmac.compare_digest(digest, settings.pin_hash)


def _hash_pin(pin: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 120_000)
    return digest.hex()


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
