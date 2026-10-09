"""CraftCine renderer — parallel Pillow frames -> mp4 via bundled ffmpeg.

Why it is fast:
- no browser, no UI framework: raw Pillow (~5-15 ms/frame at 720p)
- ProcessPoolExecutor across all CPU cores
- preview mode 640x360@15fps for instant iteration, then final 1080p/720p@30fps
- incremental mode: unchanged shots are re-used from cache, only edits re-render
- deterministic: same (storyboard, seed) -> same mp4
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import timeline as TL
from . import compositor as C


def _render_one(args) -> tuple[int, object]:
    frame, shot_name, t, W, H, theme, title, subtitle, seed, value, image, values = args
    img = C.render_frame(shot_name, t, W, H, theme, title, subtitle, seed, value,
                         image=image, values=values)
    return frame, np.asarray(img)


def _resolve_image(path: str, assets_dir: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path) and os.path.exists(path):
        return path
    cand = os.path.join(assets_dir, path) if assets_dir else path
    return cand if os.path.exists(cand) else ""


def _tasks(sb: dict, W: int, H: int, fps: int, assets_dir: str = "") -> list:
    bounds = []
    acc = 0.0
    for s in sb["shots"]:
        bounds.append((acc, acc + float(s["duration"]), s))
        acc += float(s["duration"])
    total = int(round(acc * fps))
    tasks = []
    for f in range(total):
        t_sec = f / fps
        for (a, b, s) in bounds:
            if t_sec < b or s is bounds[-1][2]:
                lt = max(0.0, min(1.0, (t_sec - a) / (b - a)))
                tasks.append((f, s["shot"], lt, W, H, sb.get("theme", "ink_press"),
                              s.get("title", ""), s.get("subtitle", ""),
                              sb.get("seed", 7), s.get("value", 0),
                              _resolve_image(s.get("image", ""), assets_dir),
                              s.get("values") or None))
                break
    return tasks


def _run_tasks(tasks: list, jobs: int, progress: bool, on_progress=None) -> list:
    total = len(tasks)
    frames: list = [None] * total
    jobs = jobs or (os.cpu_count() or 4)
    jobs = max(1, min(jobs, 16))
    if jobs == 1 or total < 8:
        for a in tasks:
            f, arr = _render_one(a)
            frames[f] = arr
            if on_progress:
                on_progress(f + 1, total)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for f, arr in ex.map(_render_one, tasks, chunksize=max(1, total // (jobs * 4))):
                frames[f] = arr
                if progress and (f + 1) % max(1, total // 10) == 0:
                    print(f"  [{f + 1}/{total}] frames", flush=True)
                if on_progress:
                    on_progress(f + 1, total)
    return frames


def _write_mp4(frames: list, out_mp4: str, fps: int) -> None:
    import imageio.v2 as imageio
    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    w = imageio.get_writer(out_mp4, fps=fps, codec="libx264", quality=8, macro_block_size=1,
                           ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "veryfast"])
    for arr in frames:
        w.append_data(arr)
    w.close()


def render(sb: dict, out_mp4: str, preview: bool = False, jobs: int = 0,
           progress: bool = True, assets_dir: str = "") -> str:
    W, H, fps = sb["width"], sb["height"], sb["fps"]
    if preview:
        W, H, fps = 640, 360, 15
    tasks = _tasks(sb, W, H, fps, assets_dir)
    frames = _run_tasks(tasks, jobs, progress)
    _write_mp4(frames, out_mp4, fps)
    bgm = sb.get("bgm")
    if bgm and os.path.exists(str(bgm)):
        _mux_audio(out_mp4, str(bgm))
    return out_mp4


def shot_hash(shot: dict, W: int, H: int, fps: int, theme: str, seed: int,
              assets_dir: str = "") -> str:
    """Stable cache key for one shot segment (image content changes the key)."""
    payload = {"shot": shot.get("shot"), "duration": shot.get("duration"),
               "title": shot.get("title", ""), "subtitle": shot.get("subtitle", ""),
               "value": shot.get("value", 0), "values": shot.get("values"),
               "W": W, "H": H, "fps": fps, "theme": theme, "seed": seed}
    img = _resolve_image(shot.get("image", ""), assets_dir)
    if img:
        st = os.stat(img)
        payload["image"] = [img, st.st_mtime_ns, st.st_size]
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]


def render_incremental(sb: dict, out_mp4: str, cache_dir: str, assets_dir: str = "",
                       jobs: int = 0, progress: bool = True, on_progress=None) -> dict:
    """Render per-shot segments, re-using cached ones, then concat.

    Returns {"segments": N, "rendered": M, "cached": K, "output": path}.
    """
    import imageio_ffmpeg
    W, H, fps = sb["width"], sb["height"], sb["fps"]
    theme, seed = sb.get("theme", "ink_press"), sb.get("seed", 7)
    os.makedirs(cache_dir, exist_ok=True)
    # fresh segment files for this run; drop stale ones afterwards
    wanted: set[str] = set()
    seg_paths: list[str] = []
    missing: list[tuple[int, dict, str]] = []
    acc = 0.0
    for i, s in enumerate(sb["shots"]):
        key = shot_hash(s, W, H, fps, theme, seed, assets_dir)
        name = f"seg_{i:02d}_{key}.mp4"
        wanted.add(name)
        path = os.path.join(cache_dir, name)
        seg_paths.append(path)
        if not os.path.exists(path):
            missing.append((i, s, path))
        acc += float(s["duration"])
    total_frames = int(round(acc * fps))
    done_base = total_frames - sum(int(round(float(s["duration"]) * fps)) for _, s, _ in missing)
    if missing:
        bounds = []
        a = 0.0
        for s in sb["shots"]:
            bounds.append((a, a + float(s["duration"])))
            a += float(s["duration"])
        for i, s, path in missing:
            a0, b0 = bounds[i]
            f0, f1 = int(round(a0 * fps)), int(round(b0 * fps))
            tasks = []
            for k, f in enumerate(range(f0, f1)):
                lt = (f / fps - a0) / max(1e-6, (b0 - a0))
                tasks.append((k, s["shot"], max(0.0, min(1.0, lt)), W, H, theme,
                              s.get("title", ""), s.get("subtitle", ""),
                              seed, s.get("value", 0),
                              _resolve_image(s.get("image", ""), assets_dir),
                              s.get("values") or None))
            frames = _run_tasks(tasks, jobs, progress,
                                on_progress and (lambda d, t, _b=done_base: on_progress(_b + d, total_frames)))
            _write_mp4(frames, path, fps)
            done_base += len(tasks)
    for stale in os.listdir(cache_dir):
        if stale.startswith("seg_") and stale.endswith(".mp4") and stale not in wanted:
            try:
                os.remove(os.path.join(cache_dir, stale))
            except OSError:
                pass
    # concat with identical codec params -> stream copy (fast, lossless)
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    lst = os.path.join(cache_dir, "concat.txt")
    with open(lst, "w") as f:
        for p in seg_paths:
            f.write(f"file '{p}'\n")
    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    subprocess.run([exe, "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", out_mp4], capture_output=True, check=True)
    bgm = sb.get("bgm")
    if bgm and os.path.exists(str(bgm)):
        _mux_audio(out_mp4, str(bgm))
    if on_progress:
        on_progress(total_frames, total_frames)
    return {"segments": len(seg_paths), "rendered": len(missing),
            "cached": len(seg_paths) - len(missing), "output": out_mp4}


def _mux_audio(video: str, audio: str) -> None:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = video + ".tmp.mp4"
        subprocess.run([exe, "-y", "-i", video, "-i", audio, "-c:v", "copy",
                        "-c:a", "aac", "-shortest", tmp],
                       capture_output=True, check=False)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, video)
    except Exception as e:
        print(f"[craftcine] audio mux skipped: {e}")


def still(sb: dict, frame: int, out_png: str, W: int = 0, H: int = 0,
          assets_dir: str = "") -> str:
    """QA still — dump one frame for review."""
    i, t, s = TL.frame_to_shot(sb, frame)
    img = C.render_frame(s["shot"], t, W or sb["width"], H or sb["height"],
                         sb.get("theme", "ink_press"), s.get("title", ""),
                         s.get("subtitle", ""), sb.get("seed", 7), s.get("value", 0),
                         image=_resolve_image(s.get("image", ""), assets_dir),
                         values=s.get("values") or None)
    img.save(out_png)
    return out_png
