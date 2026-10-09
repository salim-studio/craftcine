"""CraftCine jobs — background render jobs with progress (thread-based).

Local studio runs renders in a worker thread so the UI stays responsive.
Serverless deployments must not start jobs (no background execution there).
"""
from __future__ import annotations
import os
import threading
import time
import uuid

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def is_serverless() -> bool:
    return os.environ.get("VERCEL") == "1"


def start(project_id: str, sb: dict, out_mp4: str, cache_dir: str,
          assets_dir: str = "", jobs: int = 0, preview: bool = False) -> dict:
    from . import renderer as R
    from . import subs as SUBS
    from . import studio as ST
    jid = uuid.uuid4().hex[:8]
    job: dict = {"id": jid, "project": project_id, "status": "queued",
                 "done": 0, "total": 1, "cached": 0, "rendered": 0,
                 "output": out_mp4, "error": "", "started": time.time(),
                 "finished": 0.0}
    with _LOCK:
        JOBS[jid] = job

    def _work():
        try:
            job["status"] = "running"

            def _cb(d: int, t: int):
                job["done"] = d
                job["total"] = t

            if preview:
                R.render(sb, out_mp4, preview=True, jobs=jobs, progress=False,
                         assets_dir=assets_dir, )
            else:
                info = R.render_incremental(sb, out_mp4, cache_dir, assets_dir,
                                            jobs=jobs, progress=False, on_progress=_cb)
                job["cached"] = info["cached"]
                job["rendered"] = info["rendered"]
            base = os.path.dirname(os.path.abspath(out_mp4))
            with open(os.path.join(base, "promo.srt"), "w", encoding="utf-8") as f:
                f.write(SUBS.to_srt(sb))
            ST.export_edit_draft_to(sb, os.path.join(base, "edit_draft.json"))
            job["status"] = "done"
        except Exception as e:  # surface failures to the UI, never crash the thread silently
            job["status"] = "error"
            job["error"] = f"{type(e).__name__}: {e}"
        finally:
            job["finished"] = time.time()

    threading.Thread(target=_work, daemon=True).start()
    return job


def get(jid: str) -> dict | None:
    with _LOCK:
        job = JOBS.get(jid)
        return dict(job) if job else None


def latest_for(project_id: str) -> dict | None:
    with _LOCK:
        mine = [j for j in JOBS.values() if j["project"] == project_id]
    if not mine:
        return None
    return dict(sorted(mine, key=lambda j: j["started"])[-1])
