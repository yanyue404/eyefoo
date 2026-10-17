"""青柠和橙片两套柠檬片皮肤。悬浮窗按这个调色来画。"""

from __future__ import annotations

import math
from dataclasses import dataclass

import tkinter as tk


@dataclass(frozen=True)
class CitrusSkin:
    name: str
    rind_deep: str
    rind: str
    zest: str
    pith: str
    pulp: str
    pulp_deep: str
    membrane: str
    core: str
    ink: str
    muted: str
    seed: str
    leaf: str
    vein: str


SKINS: dict[str, CitrusSkin] = {
    "green": CitrusSkin(
        name="青柠",
        rind_deep="#3D6B12",
        rind="#7CB342",
        zest="#C5E17A",
        pith="#F4F8E6",
        pulp="#D4EC7A",
        pulp_deep="#C0E05A",
        membrane="#FBFDF3",
        core="#F7FBEA",
        ink="#2C4A12",
        muted="#4F6E28",
        seed="#F3E7B4",
        leaf="#2E7D32",
        vein="#1B5E20",
    ),
    "orange": CitrusSkin(
        name="橙片",
        rind_deep="#E65100",
        rind="#FB8C00",
        zest="#FFD180",
        pith="#FFF4E5",
        pulp="#FFB74D",
        pulp_deep="#FF9800",
        membrane="#FFF9F1",
        core="#FFF8F0",
        ink="#BF360C",
        muted="#E65100",
        seed="#FFF3D6",
        leaf="#689F38",
        vein="#33691E",
    ),
}

SLICE_SIZE = 240
MIN_SLICE_SIZE = 160
MAX_SLICE_SIZE = 360


def normalize_skin(value: str | None) -> str:
    if value in SKINS:
        return str(value)
    return "green"


def skin_of(value: str | None) -> CitrusSkin:
    return SKINS[normalize_skin(value)]


def clamp_size(value: object) -> int:
    try:
        size = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        size = SLICE_SIZE
    return max(MIN_SLICE_SIZE, min(MAX_SLICE_SIZE, size))


def draw_slice(
    canvas: tk.Canvas,
    skin_id: str,
    clock: str,
    phase: str,
    phase_label: str,
    size: int = SLICE_SIZE,
) -> None:
    """把一整片柠檬画到画布上。size 是窗口边长，图形按 240 像素那一版等比缩放。"""
    skin = skin_of(skin_id)
    size = clamp_size(size)
    scale = size / SLICE_SIZE
    canvas.delete("slice")
    center = size / 2

    def unit(length: float) -> float:
        return length * scale
    segments = 10
    extent = 360 / segments

    def disc(radius: float, **options) -> None:
        box = (center - radius, center - radius, center + radius, center + radius)
        canvas.create_oval(*box, tags="slice", **options)

    disc(unit(112), fill=skin.rind_deep, outline="")
    disc(unit(104), fill=skin.rind, outline="")
    disc(unit(96), fill=skin.pith, outline="")
    disc(unit(88), fill=skin.pulp, outline="")

    pulp = unit(88)
    pulp_box = (center - pulp, center - pulp, center + pulp, center + pulp)
    for index in range(segments):
        color = skin.pulp if index % 2 == 0 else skin.pulp_deep
        canvas.create_arc(
            *pulp_box,
            start=index * extent - 90,
            extent=extent - 0.8,
            fill=color,
            outline="",
            tags="slice",
        )

    for index in range(segments):
        angle = math.radians(index * extent - 90)
        canvas.create_line(
            center + math.cos(angle) * unit(46),
            center + math.sin(angle) * unit(46),
            center + math.cos(angle) * unit(90),
            center + math.sin(angle) * unit(90),
            fill=skin.membrane,
            width=max(1, round(unit(3))),
            capstyle="round",
            tags="slice",
        )

    for degree in (28, 150, 236, 318):
        angle = math.radians(degree)
        seed_x = center + math.cos(angle) * unit(66)
        seed_y = center + math.sin(angle) * unit(66)
        canvas.create_oval(
            seed_x - unit(5),
            seed_y - unit(3),
            seed_x + unit(5),
            seed_y + unit(3),
            fill=skin.seed,
            outline="",
            tags="slice",
        )

    gloss = unit(100)
    canvas.create_arc(
        center - gloss,
        center - gloss,
        center + gloss,
        center + gloss,
        start=48,
        extent=78,
        style="arc",
        outline=skin.zest,
        width=max(1, round(unit(5))),
        tags="slice",
    )
    _leaf(canvas, center, skin, scale)

    if phase == "warn":
        disc(unit(114), outline="#E65100", width=max(1, round(unit(4))))
    disc(unit(48), fill=skin.core, outline=skin.pith, width=max(1, round(unit(4))))

    clock_size = max(8, round(unit(16 if len(clock) <= 5 else 12)))
    canvas.create_text(
        center,
        center - unit(8),
        text=clock,
        fill=skin.ink,
        font=("Microsoft YaHei UI", clock_size, "bold"),
        tags="slice",
    )
    canvas.create_text(
        center,
        center + unit(16),
        text=phase_label,
        fill=skin.muted,
        font=("Microsoft YaHei UI", max(8, round(unit(9)))),
        tags="slice",
    )


def _leaf(canvas: tk.Canvas, center: float, skin: CitrusSkin, scale: float) -> None:
    offsets = ((18, -86), (58, -112), (92, -96), (48, -72))
    points: list[float] = []
    for dx, dy in offsets:
        points.extend((center + dx * scale, center + dy * scale))
    canvas.create_polygon(
        *points,
        smooth=True,
        splinesteps=24,
        fill=skin.leaf,
        outline="",
        tags="slice",
    )
    canvas.create_line(
        center + 30 * scale,
        center - 86 * scale,
        center + 74 * scale,
        center - 102 * scale,
        fill=skin.vein,
        width=max(1, round(2 * scale)),
        capstyle="round",
        tags="slice",
    )
