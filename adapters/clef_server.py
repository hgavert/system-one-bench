"""Clef-flash (huggingface.co/Cloudflare/clef-flash) behind TypeSafe's /v1/systemone API, on this Mac.

Cloudflare's release ships the weights plus joint_schema_model.py, whose systemone() turns a
/v1/systemone request body into a response body. This wraps it in a tiny HTTP server (stdlib only), so
every test calls Clef like Kev or CLM:

  third_party/clef-env/.venv/bin/python adapters/clef_server.py --port 8720        # Clef-flash, bf16, MPS
  uv run python 02_benchmark.py s1:clef-flash --url http://127.0.0.1:8720 --name clef-flash      # sentiment
  uv run python 09_snake_benchmark.py --engine http:http://127.0.0.1:8720,clef-flash           # Snake
  uv run python 12_finnish_benchmark.py --engine http:http://127.0.0.1:8720,clef-flash         # Finnish

Zero-shot: the released checkpoint as-is, at a pinned revision. The model is post-trained from Qwen3.5-9B; a
"joint schema head" reads the backbone's final hidden states and scores the options of all questions jointly.
Probabilities are the softmax of the head's scores (the release applies no temperature). Clef (27B, 55 GB
bf16) does not fit a 32 GB Mac; the same server would serve it with --repo Cloudflare/clef.
"""
import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from huggingface_hub import snapshot_download

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default="Cloudflare/clef-flash")
ap.add_argument("--revision", default="17f0b0ad64efb65d273590632833508766b2aae6")   # benchmarked revision
ap.add_argument("--name", default="clef-flash", help="model name reported in responses")
ap.add_argument("--port", type=int, default=8720)
ap.add_argument("--device", default="mps" if torch.backends.mps.is_available() else "cpu")
args = ap.parse_args()

path = snapshot_download(args.repo, revision=args.revision)
sys.path.insert(0, path)
from joint_schema_model import load_release_model, systemone  # noqa: E402  (ships with the weights)

t0 = time.time()
model, processor = load_release_model(path, device=args.device, dtype=torch.bfloat16)
print(f"[clef] {args.repo}@{args.revision[:8]} on {args.device} in {time.time() - t0:.0f}s", flush=True)
lock = threading.Lock()                     # one forward pass at a time on the GPU


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/v1/models":
            self._send(200, {"models": [{"name": args.name, "repo": args.repo, "revision": args.revision,
                                         "device": args.device, "dtype": "bfloat16"}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/systemone":
            return self._send(404, {"error": "not found"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            req.setdefault("model", args.name)
            t = time.perf_counter()
            with lock:
                out = systemone(model, processor, req)
                if args.device == "mps":
                    torch.mps.synchronize()
            out["latency_ms"] = round((time.perf_counter() - t) * 1000, 1)
            self._send(200, out)
        except ValueError as e:
            self._send(422, {"error": str(e)})
        except Exception as e:                   # surface model errors to the client instead of hanging
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *a):
        pass


print(f"[clef] serving /v1/systemone on http://127.0.0.1:{args.port}", flush=True)
ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
