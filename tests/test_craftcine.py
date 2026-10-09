"""Deterministic + smoke tests (fast, no network)."""
from craftcine import easing, shots, themes, timeline
from craftcine.compositor import render_frame


def test_easing_bounds():
    for name, fn in easing.EASE.items():
        assert 0.0 <= fn(0.0) <= 1.0, name
        assert 0.0 <= fn(0.5) <= 1.25, name
        assert fn(1.0) == 1.0 or abs(fn(1.0) - 1.0) < 0.05, name


def test_mulberry_deterministic():
    a = [easing.mulberry32(7)() for _ in range(5)]
    b = [easing.mulberry32(7)() for _ in range(5)]
    assert a == b


def test_shots_valid():
    assert len(shots.SHOTS) == 24
    for name in shots.SHOTS:
        assert shots.get(name)["name"] == name


def test_themes_valid():
    assert len(themes.THEMES) == 9
    for t in themes.names():
        th = themes.get(t)
        assert th["bg"].startswith("#") and th["accent"].startswith("#")


def test_timeline_map():
    sb = timeline.normalize({"shots": [
        {"shot": "fade-in", "duration": 2.0},
        {"shot": "spotlight-hero", "duration": 4.0}]})
    assert sb["total_frames"] == 180
    i, t, _ = timeline.frame_to_shot(sb, 0)
    assert i == 0 and t == 0.0
    i, t, _ = timeline.frame_to_shot(sb, 60)
    assert i == 1


def test_all_shots_render_deterministic():
    f1 = render_frame("spotlight-hero", 0.5, 320, 180, "ink_press", "T", "S", 7)
    f2 = render_frame("spotlight-hero", 0.5, 320, 180, "ink_press", "T", "S", 7)
    assert list(f1.getdata()) == list(f2.getdata())
    for name in shots.SHOTS:  # smoke: no shot crashes
        img = render_frame(name, 0.5, 320, 180, "midnight", "Title", "Sub", 7, value=99)
        assert img.size == (320, 180)
