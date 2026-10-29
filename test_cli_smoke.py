"""Optional real-Codex integration tests against a loopback-only fake provider.

No real API key or system credential entry is used. Model requests stay on
localhost. Codex may independently refresh public plugin metadata. Skips when
Codex is unavailable. Requires permission to bind a localhost port.
"""
from __future__ import annotations

import http.server
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("deepseek_launcher", ROOT / "setup.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
CODEX = launcher.find_codex()


class Provider(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = json.loads(raw)
        self.server.requests.append({
            "path": self.path, "model": body.get("model"),
            "reasoning": body.get("reasoning", {}).get("effort"),
            "fake_auth": self.headers.get("Authorization") == "Bearer local-test-only",
            "has_prompt": "LOCAL_SMOKE_OK" in raw.decode("utf-8"),
        })
        text = "LOCAL_SMOKE_OK"
        part = {"type": "output_text", "text": text, "annotations": []}
        item = {"id": "msg_test", "type": "message", "role": "assistant",
                "status": "completed", "content": [part]}
        response = {"id": "resp_test", "object": "response", "created_at": 1,
                    "status": "completed", "model": body.get("model"), "output": [item],
                    "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}
        events = [
            {"type": "response.created", "response": dict(response, status="in_progress", output=[])},
            {"type": "response.output_item.added", "output_index": 0, "item": dict(item, status="in_progress", content=[])},
            {"type": "response.content_part.added", "item_id": "msg_test", "output_index": 0, "content_index": 0, "part": dict(part, text="")},
            {"type": "response.output_text.delta", "item_id": "msg_test", "output_index": 0, "content_index": 0, "delta": text},
            {"type": "response.output_text.done", "item_id": "msg_test", "output_index": 0, "content_index": 0, "text": text},
            {"type": "response.content_part.done", "item_id": "msg_test", "output_index": 0, "content_index": 0, "part": part},
            {"type": "response.output_item.done", "output_index": 0, "item": item},
            {"type": "response.completed", "response": response},
        ]
        payload = "".join("data: " + json.dumps(dict(event, sequence_number=i)) + "\n\n"
                          for i, event in enumerate(events)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@unittest.skipUnless(CODEX, "Real Codex CLI is not installed")
class RealCliTests(unittest.TestCase):
    def test_all_models_and_reasoning_reach_the_wire(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Provider)
        server.requests = []
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with tempfile.TemporaryDirectory(prefix="deepseek-cli-test-") as temporary:
                home = Path(temporary) / "isolated home 中文"
                launcher.init_home(home)
                bootstrap = (
                    'import json,pathlib,sys;sys.path.insert(0,sys.argv[1]);import setup;'
                    'setup.prompt_key=lambda:"local-test-only";'
                    'sys.exit(setup.run(pathlib.Path(sys.argv[2]),sys.argv[3],'
                    'json.loads(sys.argv[5]),codex=sys.argv[6],reasoning=sys.argv[4]))'
                )
                for model in ("flash", "pro"):
                    for effort in ("high", "max"):
                        with self.subTest(model=model, effort=effort):
                            args = ["exec", "--ephemeral", "--skip-git-repo-check",
                                    "--sandbox", "read-only", "--color", "never", "-c",
                                    "model_providers.deepseek.base_url=" + json.dumps(
                                        f"http://127.0.0.1:{server.server_port}"), "-"]
                            result = subprocess.run(
                                [sys.executable, "-B", "-c", bootstrap, str(ROOT),
                                 str(home), model, effort, json.dumps(args), CODEX],
                                cwd=temporary, text=True, encoding="utf-8", errors="replace",
                                input="Reply only LOCAL_SMOKE_OK. Do not use tools.",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45,
                            )
                            self.assertEqual(result.returncode, 0, result.stderr[-2500:])
                            self.assertEqual(result.stdout.strip(), "LOCAL_SMOKE_OK")
                            self.assertTrue(server.requests, "CLI did not contact the fake provider")
                            self.assertEqual(server.requests[-1], {
                                "path": "/responses", "model": launcher.MODELS[model],
                                "reasoning": effort, "fake_auth": True, "has_prompt": True,
                            }, result.stderr[-3500:])
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
