"""CraftCine renderer — parallel Pillow frames -> mp4 via bundled ffmpeg.

Why it is fast:
- no browser, no UI framework: raw Pillow (~5-15 ms/frame at 720p)
- ProcessPoolExecutor across all CPU cores
- preview mode 640x360@15fps for instant iteration, then final 1080p/720p@30fps
- deterministic: same (storyboard, seed) -> same mp4
"""
from __future__ import annotations
import os
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from . import timeline as TL
from . import compositor as C


def _render_one(args) -> tuple[int, object]:
    frame, shot_name, t, W, H, theme, title, subtitle, seed, value = args
    img = C.render_frame(shot_name, t, W, H, theme, title, subtitle, seed, value)
    return frame, np.asarray(img)


def render(sb: dict, out_mp4: str, preview: bool = False, jobs: int = 0,
           progress: bool = True) -> str:
    import imageio.v2 as imageio
    W, H, fps = sb["width"], sb["height"], sb["fps"]
    if preview:
        W, H, fps = 640, 360, 15
    total = int(round(sb["total_sec"] * fps))
    # map global frame -> local t at target fps (recompute, fps-independent)
    tasks = []
    acc_boundaries = []
    acc = 0.0
    for s in sb["shots"]:
        acc_boundaries.append((acc, acc + float(s["duration"]), s))
        acc += float(s["duration"])
    for f in range(total):
        t_sec = f / fps
        for (a, b, s) in acc_boundaries:
            if t_sec < b or s is acc_boundaries[-1][2]:
                lt = max(0.0, min(1.0, (t_sec - a) / (b - a)))
                tasks.append((f, s["shot"], lt, W, H, sb.get("theme", "ink_press"),
                              s.get("title", ""), s.get("subtitle", ""),
                              sb.get("seed", 7), s.get("value", 0)))
                break
    jobs = jobs or (os.cpu_count() or 4)
    jobs = max(1, min(jobs, 16))
    frames = [None] * total
    if jobs == 1 or total < 8:
        for a in tasks:
            f, arr = _render_one(a)
            frames[f] = arr
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            for f, arr in ex.map(_render_one, tasks, chunksize=max(1, total // (jobs * 4))):
                frames[f] = arr
                if progress and (f + 1) % max(1, total // 10) == 0:
                    print(f"  [{f + 1}/{total}] frames", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_mp4)), exist_ok=True)
    w = imageio.get_writer(out_mp4, fps=fps, codec="libx264", quality=8, macro_block_size=1,
                           ffmpeg_params=["-pix_fmt", "yuv420p", "-preset", "veryfast"])
    for arr in frames:
        w.append_data(arr)
    w.close()
    # mux BGM if storyboard points to an audio file
    bgm = sb.get("bgm")
    if bgm and os.path.exists(str(bgm)):
        _mux_audio(out_mp4, str(bgm))
    return out_mp4


def _mux_audio(video: str, audio: str) -> None:
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        tmp = video + ".tmp.mp4"
        import subprocess
        subprocess.run([exe, "-y", "-i", video, "-i", audio, "-c:v", "copy",
                        "-c:a", "aac", "-shortest", tmp],
                       capture_output=True, check=False)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, video)
    except Exception as e:
        print(f"[craftcine] audio mux skipped: {e}")


def still(sb: dict, frame: int, out_png: str, W: int = 0, H: int = 0) -> str:
    """QA still — dump one frame for review."""
    i, t, s = TL.frame_to_shot(sb, frame)
    img = C.render_frame(s["shot"], t, W or sb["width"], H or sb["height"],
                         sb.get("theme", "ink_press"), s.get("title", ""),
                         s.get("subtitle", ""), sb.get("seed", 7), s.get("value", 0))
    img.save(out_png)
    return out_png
