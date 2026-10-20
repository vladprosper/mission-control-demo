"""Portable CLI + HTTP smoke check, temporary DB and OS-assigned loopback port."""
import json
import hashlib
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mission_control.server import make_server
from mission_control.store import timestamp

AS_OF = "2026-10-19T12:00:00Z"
# Do not inherit proxy settings for the local smoke test.
http = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def main():
    with tempfile.TemporaryDirectory(prefix="mission-control-smoke-") as tmp:
        db = str(Path(tmp) / "fictional.sqlite3")
        command = [sys.executable, "-m", "mission_control", "--db", db, "--fictional", "--as-of", AS_OF]
        def run(*args, success=True):
            result = subprocess.run(command + list(args), cwd=ROOT, capture_output=True, text=True)
            assert (result.returncode == 0) == success, result.stderr
            return json.loads(result.stdout) if success else result
        assert run("import", "examples/synthetic.json")["inserted"] == 12
        assert run("import", "examples/synthetic.csv")["duplicates"] == 12
        run("import", "examples/invalid-batch.json", success=False)
        report = run("report")
        assert len(report["records"]) == 12 and len(report["imports"]) == 2
        with make_server(db, port=0, as_of=timestamp(AS_OF)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            def get(path):
                return http.open(base + path, timeout=5)
            try:
                assert json.load(get("/health"))["fictional"] is True
                response = get("/api/report")
                assert response.headers["X-Content-Type-Options"] == "nosniff"
                assert "default-src 'self'" in response.headers["Content-Security-Policy"]
                assert json.load(response) == report
                assert b"FICTIONAL DATA" in get("/").read()
                assert b"One article, one review" in get("/").read()
                assert b"function scene" in get("/static/story.js").read()
                assert b".architecture-flow" in get("/static/story.css").read()
                assert json.load(get("/api/story"))["interactive"] is False
                assert b"FICTIONAL DATA" in get("/technical/").read()
                assert b"renderRows" in get("/static/app.js").read()
                assert b"--ink" in get("/static/style.css").read()
                for path in ("/../examples/synthetic.json", "/examples/synthetic.json", "/missing"):
                    try:
                        get(path)
                    except urllib.error.HTTPError as exc:
                        assert exc.code == 404
                    else:
                        raise AssertionError("Unexpected file access")
                try:
                    http.open(urllib.request.Request(base + "/api/report", data=b"{}", method="POST"), timeout=5)
                except urllib.error.HTTPError as exc:
                    assert exc.code == 501
                else:
                    raise AssertionError("Unexpected write endpoint")
                print(f"PASS: CLI import, JSON/CSV deduplication, rejected batch rollback, report, HTTP assets/API/404/write rejection; loopback port {server.server_port}")
            finally:
                server.shutdown()
                thread.join(timeout=5)
        baseline_hash = hashlib.sha256(Path(db).read_bytes()).hexdigest()
        with make_server(db, port=0, as_of=timestamp(AS_OF), workbench=True) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            def post(action, body, origin=True, content_type="application/json", expected=200, prefix="/api/workbench/"):
                headers={"Content-Type":content_type}
                if origin: headers["Origin"]=base if origin is True else origin
                request=urllib.request.Request(base+prefix+action,data=json.dumps(body).encode(),headers=headers,method="POST")
                try:
                    response=http.open(request,timeout=5)
                except urllib.error.HTTPError as exc:
                    assert exc.code==expected,(exc.code,expected)
                    return json.load(exc)
                assert response.status==expected
                return json.load(response)
            try:
                assert json.load(http.open(base+"/api/context",timeout=5))["fictional"]
                post("preview",{"scenario":"draft"},origin=False,expected=403)
                post("preview",{"scenario":"draft"},origin="https://example.invalid",expected=403)
                post("preview",{"scenario":"draft"},content_type="text/plain",expected=415)
                post("preview",{"scenario":"draft","unexpected":"field"},expected=400)
                post("preview",{"scenario":"not-a-scenario"},expected=409)
                rejected=post("preview",{"scenario":"rollback"})
                assert not rejected["accepted"] and rejected["unchanged"]
                assert any(e["outcome"]=="rolled_back" for e in rejected["events"])
                preview=post("preview",{"scenario":"draft"})
                state=json.load(http.open(base+"/api/workbench",timeout=5))
                assert state["report"]["statuses"]["drafted"]==3
                applied=post("apply",{"scenario":"draft","preview_token":preview["preview_token"]})
                assert applied["report"]["statuses"]["drafted"]==4
                post("apply",{"scenario":"draft","preview_token":preview["preview_token"]},expected=409)
                baseline=json.load(http.open(base+"/api/report",timeout=5))
                assert baseline["statuses"]["drafted"]==3
                reset=post("reset",{})
                assert reset["report"]["statuses"]["drafted"]==3 and not reset["history"]
                assert hashlib.sha256(Path(db).read_bytes()).hexdigest()==baseline_hash
                print(f"PASS: workbench same-origin/JSON/action guards, preview isolation, real rollback trace, preview/apply token, token replay rejection, reset, unchanged baseline DB; loopback port {server.server_port}")
                def story_post(body, **kwargs):
                    return post("advance", body, prefix="/api/story/", **kwargs)
                view=json.load(http.open(base+"/api/story", timeout=5))
                assert view["interactive"] is True and view["step"]==0
                story_post({"action":"open_review","revision":0},origin=False,expected=403)
                story_post({"action":"open_review","revision":0},origin="https://example.invalid",expected=403)
                story_post({"action":"open_review","revision":0},content_type="text/plain",expected=415)
                story_post({"action":"open_review","revision":True},expected=400)
                story_post({"action":"open_review","revision":0,"extra":"x"},expected=400)
                story_post({"action":"record_decision","revision":0},expected=409)
                for step in range(1,7):
                    old=view
                    view=story_post({"action":view["guide"]["action"],"revision":view["revision"]})
                    assert view["step"]==step
                    story_post({"action":old["guide"]["action"],"revision":old["revision"]},expected=409)
                    if step==1: assert view["state"]["run"] is None
                    if step==2:
                        assert view["state"]["decision"] is None and view["state"]["article"]["draft_version"]==3
                        assert view["state"]["run"]["sources_read"]==3
                    if step==4: assert view["state"]["article"]["draft_version"]==4
                assert view["state"]["next_question"]["routine_id"]==view["state"]["routine"]["id"]
                assert view["state"]["publication"]["subscriber_impact"] is None
                reset=story_post({"action":"reset","revision":view["revision"]})
                assert reset["step"]==0 and reset["revision"]==7
                assert hashlib.sha256(Path(db).read_bytes()).hexdigest()==baseline_hash
                print(f"PASS: six-click article/review story, scheduled-vs-run distinction, source gap, owner decision, v3-to-v4, dated separate metrics, same recurring review, exact-origin/JSON/revision guards, reset, unchanged baseline DB; loopback port {server.server_port}")
            finally:
                server.shutdown()
                thread.join(timeout=5)


if __name__ == "__main__":
    main()
