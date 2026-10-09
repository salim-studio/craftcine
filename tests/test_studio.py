"""Studio-system tests: shots count, images, SRT, projects, incremental cache, Flask routes."""
import json
import os

import pytest

from craftcine import compositor, jobs, projects, renderer, shots, subs, timeline


@pytest.fixture()
def tiny_sb():
    return timeline.normalize({
        "width": 160, "height": 90, "fps": 10, "theme": "ink_press", "seed": 7,
        "shots": [
            {"shot": "fade-in", "duration": 0.5, "title": "A", "subtitle": "a"},
            {"shot": "quote-card", "duration": 0.5, "title": "Q", "subtitle": "Author"},
        ]})


def test_thirty_shots():
    assert len(shots.SHOTS) == 30
    for name in ("rise-in", "zoom-out", "slide-right", "card-flip", "stat-trio", "quote-card"):
        assert shots.get(name)["desc"]


def test_new_shots_render():
    for name in ("rise-in", "zoom-out", "slide-right", "card-flip", "stat-trio", "quote-card"):
        img = compositor.render_frame(name, 0.5, 320, 180, "iris", "T", "S", 7,
                                      values=[10, 20, 30])
        assert img.size == (320, 180)


def test_image_asset_changes_frame(tmp_path):
    from PIL import Image
    pic = tmp_path / "shot.png"
    Image.new("RGB", (400, 300), (200, 30, 30)).save(pic)
    a = compositor.render_frame("spotlight-hero", 0.5, 320, 180, "ink_press", "T", "S", 7)
    b = compositor.render_frame("spotlight-hero", 0.5, 320, 180, "ink_press", "T", "S", 7,
                                image=str(pic))
    assert list(a.tobytes()) != list(b.tobytes())
    # missing image must not crash
    c = compositor.render_frame("spotlight-hero", 0.5, 320, 180, "ink_press", "T", "S", 7,
                                image=str(tmp_path / "nope.png"))
    assert c.size == (320, 180)


def test_srt(tiny_sb):
    srt = subs.to_srt(tiny_sb)
    assert "00:00:00,000 --> 00:00:00,500" in srt
    assert "00:00:00,500 --> 00:00:01,000" in srt
    assert "Author" in srt


def test_projects_crud(tmp_path):
    root = str(tmp_path / "projects")
    meta = projects.create(root, "Hello Film", theme="midnight")
    assert meta["theme"] == "midnight"
    listed = projects.list_projects(root)
    assert any(p["id"] == meta["id"] for p in listed)
    m2, sb = projects.load(root, meta["id"])
    assert sb["shots"]
    sb["shots"].append({"shot": "fade-in", "duration": 1.0, "title": "X"})
    projects.save(root, meta["id"], sb)
    _, sb2 = projects.load(root, meta["id"])
    assert sb2["shots"][-1]["title"] == "X"
    projects.delete(root, meta["id"])
    assert all(p["id"] != meta["id"] for p in projects.list_projects(root))


def test_incremental_cache_reuse(tmp_path, tiny_sb):
    cache = str(tmp_path / "cache")
    out = str(tmp_path / "promo.mp4")
    r1 = renderer.render_incremental(tiny_sb, out, cache, jobs=1)
    assert r1["rendered"] == 2 and r1["cached"] == 0
    mtimes = {f: os.path.getmtime(os.path.join(cache, f)) for f in os.listdir(cache)
              if f.startswith("seg_")}
    r2 = renderer.render_incremental(tiny_sb, out, cache, jobs=1)
    assert r2["rendered"] == 0 and r2["cached"] == 2
    for f, m in mtimes.items():
        assert os.path.getmtime(os.path.join(cache, f)) == m
    assert os.path.getsize(out) > 0
    # editing one shot re-renders only that segment
    tiny_sb["shots"][0]["title"] = "CHANGED"
    r3 = renderer.render_incremental(tiny_sb, out, cache, jobs=1)
    assert r3["rendered"] == 1 and r3["cached"] == 1


def _client(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    from craftcine.server import create_app
    app = create_app(data_dir=str(tmp_path / "webdata"))
    app.config["TESTING"] = True
    return app.test_client()


def test_studio_flow(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.get("/").status_code == 200
    assert c.get("/api/shots").status_code == 200
    assert len(c.get("/api/shots").get_json()) == 30
    v = c.get("/api/version").get_json()
    assert v["app"] == "craftcine" and v["shots"] == 30
    assert c.get("/gallery").status_code == 200
    assert c.get("/studio").status_code == 200
    # create + edit
    pid = projects.create(c.application.config["DATA_DIR"], "Web Film")["id"]
    assert c.get(f"/studio/p/{pid}").status_code == 200
    assert c.get(f"/studio/p/{pid}/still/0").status_code == 200
    r = c.post(f"/studio/p/{pid}/shots/add",
               data={"shot": "quote-card", "title": "Q", "subtitle": "A"})
    assert r.status_code in (302, 303)
    # background render job (tiny project for speed)
    _, sb = projects.load(c.application.config["DATA_DIR"], pid)
    sb.update({"width": 160, "height": 90, "fps": 10})
    sb["shots"] = sb["shots"][:2]
    for s in sb["shots"]:
        s["duration"] = 0.5
    projects.save(c.application.config["DATA_DIR"], pid, sb)
    r = c.post(f"/studio/p/{pid}/render", data={})
    assert r.status_code in (302, 303)
    import time
    job = None
    for _ in range(120):
        job = jobs.latest_for(pid)
        if job and job["status"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert job and job["status"] == "done", job
    assert c.get(f"/studio/api/jobs/{job['id']}").status_code == 200
    assert c.get(f"/studio/p/{pid}/download").status_code == 200
    assert b"WebVTT" not in c.get(f"/studio/p/{pid}/subs.srt").data
    assert c.get(f"/studio/p/{pid}/subs.srt").status_code == 200
    assert c.get(f"/studio/p/{pid}/draft.json").status_code == 200


def test_serverless_render_sync(tmp_path, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    from craftcine.server import create_app
    app = create_app(data_dir=str(tmp_path / "srv"))
    app.config["TESTING"] = True
    c = app.test_client()
    pid = projects.create(str(tmp_path / "srv"), "Srv")["id"]
    _, sb = projects.load(str(tmp_path / "srv"), pid)
    sb.update({"width": 160, "height": 90, "fps": 10})
    sb["shots"] = sb["shots"][:2]
    for s in sb["shots"]:
        s["duration"] = 0.5
    projects.save(str(tmp_path / "srv"), pid, sb)
    # hosted render runs synchronously and hands back the file (or project page w/ note)
    r = c.post(f"/studio/p/{pid}/render", data={})
    assert r.status_code in (302, 303)
    assert c.get(f"/studio/p/{pid}/download").status_code == 200
    assert c.get("/api/render-demo").status_code == 200
