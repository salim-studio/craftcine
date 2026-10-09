"""CraftCine timeline — JSON storyboard -> frame map. Beat-sync lite."""
from __future__ import annotations
import json
from . import shots as S


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        sb = json.load(f)
    return normalize(sb)


def normalize(sb: dict) -> dict:
    sb = dict(sb)
    sb.setdefault("width", 1280)
    sb.setdefault("height", 720)
    sb.setdefault("fps", 30)
    sb.setdefault("theme", "ink_press")
    sb.setdefault("seed", 7)
    assert sb.get("shots"), "storyboard.shots is empty"
    total = 0.0
    for s in sb["shots"]:
        S.get(s.get("shot", "fade-in"))  # validate name early
        s.setdefault("duration", S.get(s["shot"])["dur"])
        s.setdefault("title", "")
        s.setdefault("subtitle", "")
        total += float(s["duration"])
    sb["total_sec"] = total
    sb["total_frames"] = int(round(total * sb["fps"]))
    return sb


def frame_to_shot(sb: dict, frame: int) -> tuple[int, float, dict]:
    """Return (shot_index, local_t 0..1, shot_dict)."""
    fps = sb["fps"]
    t_sec = frame / fps
    acc = 0.0
    for i, s in enumerate(sb["shots"]):
        d = float(s["duration"])
        if t_sec < acc + d or i == len(sb["shots"]) - 1:
            return i, max(0.0, min(1.0, (t_sec - acc) / d)), s
        acc += d
    return len(sb["shots"]) - 1, 1.0, sb["shots"][-1]


def beat_grid(bpm: float, fps: int, total_frames: int, offset: float = 0.0) -> list[int]:
    """Beat-synced cut suggestion: frames where beats land."""
    if bpm <= 0:
        return []
    spb = 60.0 / bpm
    out, b = [], offset
    while (f := int(round(b * fps))) < total_frames:
        out.append(f)
        b += spb
    return out


def snap_to_beats(sb: dict, bpm: float) -> dict:
    """Adjust shot durations so cuts land on beats (lite beat-sync, no librosa needed)."""
    if bpm <= 0:
        return sb
    import copy
    sb = copy.deepcopy(sb)
    fps, spb = sb["fps"], 60.0 / bpm
    acc = 0.0
    for s in sb["shots"]:
        d = float(s["duration"])
        beats = max(1, round((d) / spb))
        s["duration"] = round(beats * spb, 3)
        acc += s["duration"]
    return normalize(sb)
