"""CraftCine subtitles — storyboard -> SRT (one entry per titled shot)."""
from __future__ import annotations


def _stamp(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(sb: dict) -> str:
    """Build SubRip subtitles from shot titles/subtitles."""
    out: list[str] = []
    t = 0.0
    n = 0
    for s in sb.get("shots", []):
        d = float(s.get("duration", 2.5))
        title = (s.get("title") or "").strip()
        sub = (s.get("subtitle") or "").strip()
        text = "\n".join(x for x in (title, sub) if x)
        if text:
            n += 1
            out.append(f"{n}\n{_stamp(t)} --> {_stamp(t + d)}\n{text}\n")
        t += d
    return "\n".join(out)
