"""CraftCine studio — Flask web app (local full mode, serverless browse mode).

Local:  dashboard + visual editor + still previews + background renders.
Hosted (VERCEL=1): browsing, gallery and APIs; full renders stay local.
"""
from __future__ import annotations
import hashlib
import json
import os

from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, url_for

from . import jobs as JOBS
from . import projects as P
from . import renderer as R
from . import shots as S
from . import studio as ST
from . import subs as SUBS
from . import themes as T

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
COPYRIGHT = "© 2026 salim-slimani · CraftCine"
CLIP_EXTS = {".mp4", ".webm", ".mov", ".m4v"}
MAX_UPLOAD_MB = 25 if os.environ.get("VERCEL") == "1" else 100


def _clips(root: str, pid: str) -> list[dict]:
    adir = os.path.join(root, pid, "assets")
    out = []
    if os.path.isdir(adir):
        for fn in sorted(os.listdir(adir)):
            p = os.path.join(adir, fn)
            if os.path.isfile(p):
                out.append({"name": fn, "mb": round(os.path.getsize(p) / 1048576, 2)})
    return out


def create_app(data_dir: str | None = None) -> Flask:
    root = P.data_dir(data_dir)
    app = Flask(__name__, template_folder=os.path.join(WEB_DIR, "templates"),
                static_folder=os.path.join(WEB_DIR, "static"))
    app.config["DATA_DIR"] = root
    app.config["MAX_CONTENT_LENGTH"] = (MAX_UPLOAD_MB + 10) * 1024 * 1024

    @app.errorhandler(413)
    def too_large(e):
        import re as _re
        m = _re.search(r"/studio/p/([^/]+)", request.path)
        if m:
            return redirect(url_for("project", pid=m.group(1),
                                    err=f"File too large — limit here is {MAX_UPLOAD_MB} MB. "
                                        "Use the local studio for bigger files."))
        return "File too large", 413

    # ---------- public demo routes (also served on Vercel) ----------
    @app.get("/")
    def landing():
        return render_template("landing.html", copyright=COPYRIGHT)

    @app.get("/logo.svg")
    def logo():
        return send_file(os.path.join(P.REPO_ROOT, "assets", "brand", "logo.svg"),
                         mimetype="image/svg+xml")

    @app.get("/gallery")
    def gallery():
        theme = request.args.get("theme", "ink_press")
        tmp = "/tmp/craftcine-gallery.html" if JOBS.is_serverless() else os.path.join(
            root, ".gallery.html")
        os.makedirs(os.path.dirname(tmp) or ".", exist_ok=True)
        ST.build_gallery(tmp, theme=theme)
        return send_file(tmp, mimetype="text/html")

    @app.get("/api/shots")
    def api_shots():
        return jsonify(S.search(cat=request.args.get("cat", "")))

    @app.get("/api/themes")
    def api_themes():
        return jsonify({"default": T.DEFAULT_THEME, "themes": T.names()})

    @app.get("/api/storyboard")
    def api_storyboard():
        return send_file(os.path.join(P.REPO_ROOT, "template", "promo.json"),
                         mimetype="application/json")

    @app.get("/api/version")
    def api_version():
        """Deployment diagnostic: confirms which code is actually live."""
        import subprocess
        from . import __version__
        sha = os.environ.get("VERCEL_GIT_COMMIT_SHA", "")
        if not sha:
            try:
                sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                     capture_output=True, text=True, cwd=P.REPO_ROOT,
                                     timeout=5).stdout.strip()
            except Exception:
                sha = "unknown"
        return jsonify({"app": "craftcine", "version": __version__,
                        "commit": sha, "shots": len(S.SHOTS)})

    @app.get("/api/render-demo")
    def api_render_demo():
        from . import timeline as TL
        sb = TL.normalize({
            "width": 480, "height": 270, "fps": 12, "theme": "ink_press", "seed": 7,
            "shots": [
                {"shot": "fade-in", "duration": 1.5, "title": "CraftCine",
                 "subtitle": "Cut. Craft. Cinema."},
                {"shot": "spotlight-hero", "duration": 2.0, "title": "Hero Shot",
                 "subtitle": "Under the spotlight"},
                {"shot": "logo-hold", "duration": 1.5, "title": "CRAFTCINE",
                 "subtitle": "Rendered by an API"},
            ]})
        out = os.path.join("/tmp" if JOBS.is_serverless() else root, "craftcine-demo.mp4")
        R.render(sb, out, jobs=1, progress=False)
        return send_file(out, mimetype="video/mp4")

    # ---------- studio ----------
    @app.get("/studio")
    def dashboard():
        return render_template("dashboard.html", projects=P.list_projects(root),
                               copyright=COPYRIGHT)

    @app.post("/studio/new")
    def new_project():
        meta = P.create(root, request.form.get("title", "Untitled"),
                        request.form.get("theme", "ink_press"))
        return redirect(url_for("project", pid=meta["id"]))

    def _get(pid: str):
        try:
            return P.load(root, pid)
        except (OSError, ValueError, KeyError):
            abort(404)

    @app.get("/studio/p/<pid>")
    def project(pid: str):
        meta, sb = _get(pid)
        grouped: dict[str, list[dict]] = {}
        for row in S.search():
            grouped.setdefault(row["cat"], []).append(row)
        job = JOBS.latest_for(pid)
        return render_template("project.html", meta=meta, sb=sb, grouped=grouped,
                               themes=T.names(), job=job, clips=_clips(root, pid),
                               max_mb=MAX_UPLOAD_MB, copyright=COPYRIGHT)

    @app.post("/studio/p/<pid>/delete")
    def delete_project(pid: str):
        P.delete(root, pid)
        return redirect(url_for("dashboard"))

    @app.post("/studio/p/<pid>/save")
    def save_board(pid: str):
        sb = request.get_json(force=True)
        meta = P.save(root, pid, sb)
        _drop_stills(root, pid)
        return jsonify(meta)

    @app.post("/studio/p/<pid>/shots/add")
    def add_shot(pid: str):
        meta, sb = _get(pid)
        name = request.form.get("shot", "fade-in")
        info = S.get(name)
        sb["shots"].append({"shot": name, "duration": info["dur"],
                            "title": request.form.get("title", ""),
                            "subtitle": request.form.get("subtitle", "")})
        P.save(root, pid, sb)
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/shots/<int:i>/delete")
    def delete_shot(pid: str, i: int):
        meta, sb = _get(pid)
        if 0 <= i < len(sb["shots"]):
            sb["shots"].pop(i)
            P.save(root, pid, sb)
            _drop_stills(root, pid)
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/shots/<int:i>/move")
    def move_shot(pid: str, i: int):
        meta, sb = _get(pid)
        j = i + (-1 if request.form.get("dir") == "up" else 1)
        if 0 <= i < len(sb["shots"]) and 0 <= j < len(sb["shots"]):
            sb["shots"][i], sb["shots"][j] = sb["shots"][j], sb["shots"][i]
            P.save(root, pid, sb)
            _drop_stills(root, pid)
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/clips/upload")
    def upload_clip(pid: str):
        _get(pid)
        f = request.files.get("clip")
        if not f or not f.filename:
            return redirect(url_for("project", pid=pid, err="No file selected."))
        from werkzeug.utils import secure_filename
        fn = secure_filename(f.filename)
        ext = os.path.splitext(fn)[1].lower()
        if ext not in CLIP_EXTS:
            return redirect(url_for("project", pid=pid,
                                    err=f"Only video files ({', '.join(sorted(CLIP_EXTS))})."))
        adir = os.path.join(root, pid, "assets")
        os.makedirs(adir, exist_ok=True)
        dest = os.path.join(adir, fn)
        f.save(dest)
        if os.path.getsize(dest) > MAX_UPLOAD_MB * 1048576:
            os.remove(dest)
            return redirect(url_for("project", pid=pid,
                                    err=f"File too large (max {MAX_UPLOAD_MB} MB)."))
        try:
            from . import compositor as C
            C.validate_clip(dest)
        except Exception:
            os.remove(dest)
            return redirect(url_for("project", pid=pid, err="Could not read that video."))
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/clips/delete")
    def delete_clip(pid: str):
        meta, sb = _get(pid)
        fn = os.path.basename(request.form.get("name", ""))
        target = os.path.join(root, pid, "assets", fn)
        if os.path.isfile(target) and fn:
            try:
                from . import compositor as C
                C.release_clip(target)
            except Exception:
                pass
            os.remove(target)
            for s in sb["shots"]:
                if s.get("clip") == f"assets/{fn}":
                    s.pop("clip", None)
            P.save(root, pid, sb)
            _drop_stills(root, pid)
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/shots/<int:i>/clip")
    def attach_clip(pid: str, i: int):
        meta, sb = _get(pid)
        if 0 <= i < len(sb["shots"]):
            fn = os.path.basename(request.form.get("clip", ""))
            if fn and os.path.isfile(os.path.join(root, pid, "assets", fn)):
                sb["shots"][i]["clip"] = f"assets/{fn}"
            else:
                sb["shots"][i].pop("clip", None)
            P.save(root, pid, sb)
            _drop_stills(root, pid)
        return redirect(url_for("project", pid=pid))

    @app.post("/studio/p/<pid>/theme")
    def set_theme(pid: str):
        meta, sb = _get(pid)
        sb["theme"] = request.form.get("theme", sb.get("theme", "ink_press"))
        P.save(root, pid, sb)
        _drop_stills(root, pid)
        return redirect(url_for("project", pid=pid))

    @app.get("/studio/p/<pid>/still/<int:i>")
    def still(pid: str, i: int):
        meta, sb = _get(pid)
        if not (0 <= i < len(sb["shots"])):
            abort(404)
        s = sb["shots"][i]
        key = hashlib.sha1(json.dumps(
            [s, sb.get("theme"), sb.get("seed")]).encode()).hexdigest()[:10]
        path = os.path.join(root, pid, ".stills", f"{i}_{key}.png")
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            mid = int(sum(float(x.get("duration", 2.5)) for x in sb["shots"][:i])
                      * sb["fps"] + float(s.get("duration", 2.5)) * sb["fps"] / 2)
            R.still(sb, mid, path, assets_dir=os.path.join(root, pid))
        return send_file(path, mimetype="image/png")

    @app.post("/studio/p/<pid>/render")
    def start_render(pid: str):
        meta, sb = _get(pid)
        pdir = os.path.join(root, pid)
        out = os.path.join(pdir, "out", "promo.mp4")
        if JOBS.is_serverless():
            # No background execution on serverless: render synchronously in a
            # capped preview profile (640x360@15fps, max 90s) and hand back the file.
            try:
                info = R.render_stream(sb, out, 640, 360, 15, assets_dir=pdir)
                base = os.path.dirname(os.path.abspath(out))
                with open(os.path.join(base, "promo.srt"), "w", encoding="utf-8") as f:
                    f.write(SUBS.to_srt(sb))
                ST.export_edit_draft_to(sb, os.path.join(base, "edit_draft.json"))
                if info["capped"]:
                    return redirect(url_for("project", pid=pid,
                                            err="Hosted renders are capped at 90s — run locally for the full film."))
                return redirect(url_for("download", pid=pid))
            except Exception as e:
                return redirect(url_for("project", pid=pid, err=f"Hosted render failed: {e}"))
        job = JOBS.start(pid, sb, out, os.path.join(pdir, ".cache"),
                         assets_dir=pdir, jobs=0,
                         preview=request.form.get("preview") == "1")
        return redirect(url_for("project", pid=pid))

    @app.get("/studio/api/jobs/<jid>")
    def job_status(jid: str):
        job = JOBS.get(jid)
        if not job:
            abort(404)
        return jsonify(job)

    @app.get("/studio/p/<pid>/download")
    def download(pid: str):
        path = os.path.join(root, pid, "out", "promo.mp4")
        if not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="video/mp4", as_attachment=True,
                         download_name=f"{pid}.mp4")

    @app.get("/studio/p/<pid>/subs.srt")
    def subs(pid: str):
        meta, sb = _get(pid)
        body = SUBS.to_srt(sb).encode("utf-8")
        return body, 200, {"Content-Type": "text/plain; charset=utf-8",
                           "Content-Disposition": f"attachment; filename={pid}.srt"}

    @app.get("/studio/p/<pid>/draft.json")
    def draft(pid: str):
        meta, sb = _get(pid)
        tmp = os.path.join(root, pid, "out", "edit_draft.json")
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        ST.export_edit_draft_to(sb, tmp)
        return send_file(tmp, mimetype="application/json", as_attachment=True,
                         download_name=f"{pid}-draft.json")

    return app


def _drop_stills(root: str, pid: str) -> None:
    import shutil
    shutil.rmtree(os.path.join(root, pid, ".stills"), ignore_errors=True)


app = create_app()
