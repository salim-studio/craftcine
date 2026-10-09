"""Video-import tests: clip engine + studio upload/attach flow."""
import io
import os

import imageio.v2 as imageio
import numpy as np
import pytest

from craftcine import compositor as C
from craftcine import projects, renderer, timeline


@pytest.fixture()
def clip_file(tmp_path):
    p = str(tmp_path / "clip.mp4")
    w = imageio.get_writer(p, fps=10, codec="libx264", macro_block_size=1)
    for i in range(20):
        color = (255, 0, 0) if i % 2 == 0 else (0, 0, 255)
        w.append_data(np.full((90, 160, 3), color, np.uint8))
    w.close()
    return p


def test_clip_info_and_loop(clip_file):
    fps, n, dur = C.clip_info(clip_file)
    assert (fps, n, dur) == (10.0, 20, 2.0)
    assert abs(C.probe_duration(clip_file) - 2.0) < 0.15
    assert C.validate_clip(clip_file) > 0
    with pytest.raises(ValueError):
        C.validate_clip(str(clip_file) + ".missing")
    a = C.get_clip_frame(clip_file, 0.05)
    b = C.get_clip_frame(clip_file, 0.15)
    assert a.shape == (90, 160, 3) and not np.array_equal(a, b)
    # looping: t beyond duration wraps to the same frame
    c = C.get_clip_frame(clip_file, 0.05 + dur)
    assert np.array_equal(a, c)


def test_clip_beats_plain_and_missing(tmp_path, clip_file):
    plain = C.render_frame("zoom-push", 0.5, 320, 180, "ink_press", "T", "S", 7)
    frame = C.get_clip_frame(clip_file, 0.05)
    with_clip = C.render_frame("zoom-push", 0.5, 320, 180, "ink_press", "T", "S", 7,
                               clip=frame)
    assert list(plain.tobytes()) != list(with_clip.tobytes())


def test_render_and_still_with_clip(tmp_path, clip_file):
    sb = timeline.normalize({
        "width": 160, "height": 90, "fps": 10, "theme": "ink_press", "seed": 7,
        "shots": [{"shot": "spotlight-hero", "duration": 0.5, "title": "V",
                   "clip": clip_file, "clip_offset": 0.3}]})
    out = str(tmp_path / "v.mp4")
    info = renderer.render_incremental(sb, out, str(tmp_path / "cache"), jobs=1)
    assert info["rendered"] == 1 and os.path.getsize(out) > 0
    # cache key tracks the clip: touching the clip file re-renders
    os.utime(clip_file, (0, 0))
    info2 = renderer.render_incremental(sb, out, str(tmp_path / "cache"), jobs=1)
    assert info2["rendered"] == 1
    still = str(tmp_path / "s.png")
    renderer.still(sb, 2, still)
    assert os.path.getsize(still) > 0


def _client(tmp_path, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    from craftcine.server import create_app
    app = create_app(data_dir=str(tmp_path / "webdata"))
    app.config["TESTING"] = True
    return app.test_client()


def _upload(c, pid, clip_file):
    with open(clip_file, "rb") as f:
        data = f.read()
    return c.post(f"/studio/p/{pid}/clips/upload", data={
        "clip": (io.BytesIO(data), "demo.mp4")}, content_type="multipart/form-data")


def test_upload_attach_delete_flow(tmp_path, monkeypatch, clip_file):
    c = _client(tmp_path, monkeypatch)
    root = c.application.config["DATA_DIR"]
    pid = projects.create(root, "Clip Film")["id"]
    # reject non-video (redirect carries a visible error)
    r = c.post(f"/studio/p/{pid}/clips/upload",
               data={"clip": (io.BytesIO(b"nope"), "x.txt")},
               content_type="multipart/form-data")
    assert r.status_code in (302, 303)
    assert "err=" in r.headers["Location"]
    # accept video
    assert _upload(c, pid, clip_file).status_code in (302, 303)
    assert os.path.isfile(os.path.join(root, pid, "assets", "demo.mp4"))
    page = c.get(f"/studio/p/{pid}").data
    assert b"Import video" in page
    assert b"clips/upload" in page
    assert b"demo.mp4" in page
    # attach to shot 0, still preview works with the clip
    r = c.post(f"/studio/p/{pid}/shots/0/clip", data={"clip": "demo.mp4"})
    assert r.status_code in (302, 303)
    _, sb = projects.load(root, pid)
    assert sb["shots"][0]["clip"] == "assets/demo.mp4"
    assert c.get(f"/studio/p/{pid}/still/0").status_code == 200
    # detach
    c.post(f"/studio/p/{pid}/shots/0/clip", data={"clip": ""})
    _, sb = projects.load(root, pid)
    assert "clip" not in sb["shots"][0]
    # delete clip
    c.post(f"/studio/p/{pid}/clips/delete", data={"name": "demo.mp4"})
    assert not os.path.exists(os.path.join(root, pid, "assets", "demo.mp4"))


def test_oversize_upload_redirects_with_error(tmp_path, monkeypatch, clip_file):
    c = _client(tmp_path, monkeypatch)
    c.application.config["MAX_CONTENT_LENGTH"] = 10  # force 413
    root = c.application.config["DATA_DIR"]
    pid = projects.create(root, "Big Film")["id"]
    with open(clip_file, "rb") as f:
        data = f.read()
    assert len(data) > 10
    r = c.post(f"/studio/p/{pid}/clips/upload", data={
        "clip": (io.BytesIO(data), "big.mp4")}, content_type="multipart/form-data")
    assert r.status_code in (302, 303)
    assert "err=" in r.headers["Location"]
    page = c.get(f"/studio/p/{pid}?err=File+too+large").data
    assert b"File too large" in page


def test_chunked_upload_flow(tmp_path, monkeypatch, clip_file):
    import math
    import craftcine.server as SV
    monkeypatch.setattr(SV, "CHUNK_BYTES", 1024)
    c = _client(tmp_path, monkeypatch)
    root = c.application.config["DATA_DIR"]
    pid = projects.create(root, "Chunk Film")["id"]
    with open(clip_file, "rb") as f:
        data = f.read()
    total = math.ceil(len(data) / 1024)
    assert total >= 3
    uid = "ab" * 16
    messy = "2.8M views Best ng Zone.mp4"
    last = None
    for i in range(total):
        piece = data[i * 1024:(i + 1) * 1024]
        last = c.post(f"/studio/p/{pid}/clips/chunk", data={
            "upload_id": uid, "index": str(i), "total": str(total),
            "filename": messy,
            "chunk": (io.BytesIO(piece), "chunk")},
            content_type="multipart/form-data")
        assert last.status_code == 200, last.get_json()
    assert last.get_json()["done"] is True
    landed = os.listdir(os.path.join(root, pid, "assets"))
    assert len(landed) == 1 and landed[0].endswith(".mp4") and " " not in landed[0]
    # scattered mid-stream chunk asks for a restart, not a crash
    r = c.post(f"/studio/p/{pid}/clips/chunk", data={
        "upload_id": "cd" * 16, "index": "1", "total": "3",
        "filename": "x.mp4", "chunk": (io.BytesIO(b"0"), "chunk")},
        content_type="multipart/form-data")
    assert r.status_code == 409
    assert r.get_json()["restart"] is True
    # oversize assembly is rejected with JSON, not a platform dead-end
    monkeypatch.setattr(SV, "MAX_UPLOAD_MB", 0)
    uid2 = "ef" * 16
    r = c.post(f"/studio/p/{pid}/clips/chunk", data={
        "upload_id": uid2, "index": "0", "total": "1",
        "filename": "big.mp4", "chunk": (io.BytesIO(data), "chunk")},
        content_type="multipart/form-data")
    assert r.status_code == 413
    assert "max 0 MB" in r.get_json()["error"]
