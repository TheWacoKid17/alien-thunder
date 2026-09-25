"""Software keyboard effects, drawn by the daemon at up to 20 fps.

Each effect is a pure function: (base, t, params) -> {led: (r, g, b)}.
`base` is the profile's per-key colors, brightness already applied.
"""
from __future__ import annotations

import colorsys
import math
import random

from . import layout
from .i18n import N_

Rgb = tuple[int, int, int]

SW_EFFECTS = {
    "breathing_sw": N_("Breathing (keeps the per-key colors)"),
    "rainbow_wave": N_("Rainbow wave"),
    "spectrum_sw": N_("Spectrum cycle"),
    "color_wave": N_("Color wave over the per-key colors"),
    "twinkle": N_("Twinkle (stars)"),
}

_X = {led: layout.rel_x(led) for led in layout.ALL_LEDS}


def _hsv(h: float, s: float = 1.0, v: float = 1.0) -> Rgb:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _scale(c: Rgb, f: float) -> Rgb:
    return tuple(max(0, min(255, int(x * f))) for x in c)  # type: ignore[return-value]


def _mix(a: Rgb, b: Rgb, f: float) -> Rgb:
    return tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))  # type: ignore[return-value]


class SoftwareEffect:
    """A running effect, for the ones that need to remember something between frames."""

    def __init__(self, name: str, base: dict[int, Rgb], params: dict, brightness: float):
        if name not in SW_EFFECTS:
            raise ValueError(f"unknown software effect: {name}")
        self.name = name
        self.params = params
        self.bright = brightness
        self.speed = max(0.1, min(5.0, float(params.get("speed", 1.0))))
        self.c1 = _scale(params.get("color1_rgb", (255, 0, 0)), brightness)
        leds = sorted(set(base) | set(layout.AWCC_IDS)) if base else list(layout.AWCC_IDS)
        # keys the profile leaves uncolored start black
        self.base = {led: base.get(led, (0, 0, 0)) for led in leds}
        self.leds = leds
        self._stars: dict[int, float] = {}
        self._last_t = None
        self._rng = random.Random(1234)

    def frame(self, t: float) -> dict[int, Rgb]:
        return getattr(self, "_" + self.name)(t)

    def _breathing_sw(self, t):
        period = 4.0 / self.speed
        f = 0.08 + 0.92 * (0.5 + 0.5 * math.cos(2 * math.pi * t / period))
        return {led: _scale(c, f) for led, c in self.base.items()}

    def _rainbow_wave(self, t):
        shift = t * 0.25 * self.speed
        v = self.bright
        return {led: _hsv(_X[led] * 0.9 - shift, 1.0, v) for led in self.leds}

    def _spectrum_sw(self, t):
        c = _hsv(t * 0.08 * self.speed, 1.0, self.bright)
        return {led: c for led in self.leds}

    def _color_wave(self, t):
        pos = (t * 0.35 * self.speed) % 1.4 - 0.2
        out = {}
        for led, c in self.base.items():
            d = abs(_X[led] - pos)
            f = max(0.0, 1.0 - d / 0.12)
            out[led] = _mix(_scale(c, 0.35), self.c1, f)
        return out

    def _twinkle(self, t):
        dt = 0.05 if self._last_t is None else max(0.0, min(0.5, t - self._last_t))
        self._last_t = t
        decay = 1.6 * self.speed
        for led in list(self._stars):
            self._stars[led] -= decay * dt
            if self._stars[led] <= 0:
                del self._stars[led]
        # about 3 new stars per second, times the speed
        n = self._rng.random() < min(1.0, 3.0 * self.speed * dt) and 1 or 0
        for _ in range(n + (self._rng.random() < 0.5 * self.speed * dt)):
            self._stars[self._rng.choice(self.leds)] = 1.0
        out = {}
        for led, c in self.base.items():
            f = self._stars.get(led, 0.0)
            out[led] = _mix(_scale(c, 0.4), self.c1, f) if f else _scale(c, 0.4)
        return out
