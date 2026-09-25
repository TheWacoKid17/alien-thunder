"""Lighting effects, drawn by the daemon at up to 20 fps.

Every effect only changes how bright each light is. The colors are always the ones the
profile picked: a key set to purple breathes in purple, and a key left unset stays off.
"""
from __future__ import annotations

import math
import random

from . import layout
from .i18n import N_

Rgb = tuple[int, int, int]

KEYBOARD_EFFECTS = {
    "static": N_("Static"),
    "breathing": N_("Breathing"),
    "pulse": N_("Pulse"),
    "wave": N_("Wave"),
    "twinkle": N_("Twinkle"),
}
ZONE_EFFECTS = {
    "static": N_("Static"),
    "breathing": N_("Breathing"),
    "pulse": N_("Pulse"),
    "off": N_("Off"),
}

_X = {led: layout.rel_x(led) for led in layout.ALL_LEDS}


def _scale(c: Rgb, f: float) -> Rgb:
    return tuple(max(0, min(255, int(round(x * f)))) for x in c)  # type: ignore[return-value]


def breathing(t: float, speed: float) -> float:
    return 0.06 + 0.94 * (0.5 + 0.5 * math.cos(2 * math.pi * t * speed / 4.0))


def pulse(t: float, speed: float) -> float:
    phase = (t * speed / 1.2) % 1.0
    return 0.12 + 0.88 * math.exp(-6.0 * phase)


class Animation:
    """A running effect over a set of lights: {id: color} in, {id: dimmed color} out."""

    def __init__(self, effect: str, base: dict[int, Rgb], speed: float):
        if effect not in KEYBOARD_EFFECTS or effect == "static":
            raise ValueError(f"not an animated effect: {effect}")
        self.name = effect
        self.base = dict(base)
        self.speed = max(0.1, min(5.0, float(speed)))
        self._sparks: dict[int, float] = {}
        self._last_t: float | None = None
        self._rng = random.Random(1234)

    def frame(self, t: float) -> dict[int, Rgb]:
        if self.name == "breathing":
            f = breathing(t, self.speed)
            return {led: _scale(c, f) for led, c in self.base.items()}
        if self.name == "pulse":
            f = pulse(t, self.speed)
            return {led: _scale(c, f) for led, c in self.base.items()}
        if self.name == "wave":
            pos = (t * 0.35 * self.speed) % 1.4 - 0.2
            return {led: _scale(c, 0.2 + 0.8 * max(0.0, 1.0 - abs(_X.get(led, 0.5) - pos) / 0.18))
                    for led, c in self.base.items()}
        return self._twinkle(t)

    def _twinkle(self, t: float) -> dict[int, Rgb]:
        dt = 0.05 if self._last_t is None else max(0.0, min(0.5, t - self._last_t))
        self._last_t = t
        for led in list(self._sparks):
            self._sparks[led] -= 1.6 * self.speed * dt
            if self._sparks[led] <= 0:
                del self._sparks[led]
        lit = [led for led, c in self.base.items() if any(c)]
        # about four new sparks a second, times the speed
        if lit and self._rng.random() < min(1.0, 4.0 * self.speed * dt):
            self._sparks[self._rng.choice(lit)] = 1.0
        return {led: _scale(c, 0.3 + 0.7 * self._sparks.get(led, 0.0)) for led, c in self.base.items()}
