"""CraftCine easing + deterministic random. Pure python, no deps."""
from __future__ import annotations
import math


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def linear(t: float) -> float:
    return clamp(t)


def ease_in_cubic(t: float) -> float:
    t = clamp(t)
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    t = clamp(t)
    if t < 0.5:
        return 4 * t * t * t
    return 1 - ((-2 * t + 2) ** 3) / 2


def ease_out_expo(t: float) -> float:
    t = clamp(t)
    if t >= 1.0:
        return 1.0
    return 1 - 2 ** (-10 * t)


def ease_out_back(t: float, s: float = 1.70158) -> float:
    t = clamp(t)
    return 1 + (s + 1) * ((t - 1) ** 3) + s * ((t - 1) ** 2)


def ease_out_elastic(t: float) -> float:
    t = clamp(t)
    if t == 0 or t == 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


def damped_settle(t: float, stiffness: float = 18.0, damping: float = 9.0) -> float:
    """Cheap spring converging to 1 (for pop/scale). Deterministic."""
    t = clamp(t)
    # critically-damped-ish analytic approximation
    env = 1 - math.exp(-damping * t * 0.6)
    osc = math.sin(t * stiffness) * math.exp(-damping * t * 0.5) * (1 - t) * 0.25
    return clamp(env + osc * 0.3 + t * 0.0)


def handheld(t: float, seed: int = 7, amp: float = 6.0) -> float:
    """Subtle camera shake offset in px, deterministic from seed."""
    r = mulberry32(seed + int(t * 1000))()
    return (r - 0.5) * 2 * amp * (0.3 + 0.7 * math.sin(t * math.pi))


def lagged(t: float, i: int, n: int, overlap: float = 0.6) -> float:
    """Stagger helper: item i of n starts later. Returns local 0..1 eased progress."""
    if n <= 1:
        return ease_out_cubic(t)
    span = 1.0 - overlap
    start = (i / n) * span
    local = (t - start) / (1 - start)
    return ease_out_cubic(clamp(local))


class mulberry32:
    """Deterministic PRNG (no Math.random/Date.now allowed in renders)."""

    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF or 1

    def __call__(self) -> float:
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        z = self.s
        z = (z ^ (z >> 15)) * (z | 1) & 0xFFFFFFFF
        z ^= z + ((z ^ (z >> 7)) * (z | 61) & 0xFFFFFFFF) ^ z
        return ((z ^ (z >> 14)) & 0xFFFFFFFF) / 4294967296


EASE = {
    "linear": linear,
    "in": ease_in_cubic,
    "out": ease_out_cubic,
    "inout": ease_in_out_cubic,
    "expo": ease_out_expo,
    "back": ease_out_back,
    "elastic": ease_out_elastic,
    "spring": damped_settle,
}


def apply(name: str, t: float) -> float:
    return EASE.get(name, ease_out_cubic)(t)
