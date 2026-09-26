"""Step 8: a System One model plays Snake. Board on the left, every decision on the right.

  uv run python 08_snake_server.py            # then open http://127.0.0.1:8765
  uv run python 08_snake_server.py --engine http:http://127.0.0.1:8009,kev-4b    # Kev 4B via ./run_kev.sh's server
  uv run python 08_snake_server.py --engine http:http://127.0.0.1:8700,clm-latest  # CLM 8B, see docs/5-snake.md 5.6

Decider 2B (zero-shot, PyTorch MPS) picks every move by default. The page lets you switch between six request
formulations, four of them from published Jev snake demos (snake/formulations.py), and shows, for each tick, the Jev-shaped
request, the exact text the model read, the probabilities it returned and how code turned them into a move.
Stdlib HTTP server only; the game state lives here, the browser just draws it.
"""
import argparse
import itertools
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from snake.agent import play_step
from snake.engine import make_engine
from snake.formulations import DEFAULT_STRATEGY, FORMULATIONS
from snake.game import Game

STATIC = Path(__file__).parent / "snake" / "static"
games: dict[int, Game] = {}
ids = itertools.count(1)
lock = threading.Lock()
engine = None


def meta():
    return {"model": engine.name, "default_strategy": DEFAULT_STRATEGY,
            "formulations": [{"name": f.name, "title": f.title, "origin": f.origin, "blurb": f.blurb}
                             for f in FORMULATIONS.values()]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/meta":
            return self._send(200, meta())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        if self.path == "/api/new":
            size = max(6, min(20, int(body.get("size", 12))))
            g = Game(size=size, seed=int(body.get("seed", 0)))
            with lock:
                gid = next(ids)
                games[gid] = g
                for old in [k for k in games if k < gid - 20]:     # keep memory bounded
                    del games[old]
            return self._send(200, {"id": gid, "frame": g.frame()})
        if self.path == "/api/step":
            g = games.get(int(body.get("id", 0)))
            if g is None:
                return self._send(404, {"error": "unknown game"})
            form = body.get("formulation", "judged")
            if form not in FORMULATIONS:
                return self._send(400, {"error": f"unknown formulation {form!r}"})
            trace = play_step(engine, form, g, str(body.get("strategy", ""))[:600], rows=True)
            return self._send(200, {"frame": g.frame(), "decision": trace})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--engine", default="decider", help="decider | laya | http:<url>,<model>")
    a = ap.parse_args()
    print(f"loading {a.engine} ...", flush=True)
    engine = make_engine(a.engine)
    try:
        for f in FORMULATIONS:                                  # first MPS calls compile kernels; do it before serving
            play_step(engine, f, Game())
    except Exception as e:                                      # e.g. httpx.ConnectError: the HTTP model server isn't up
        if not a.engine.startswith("http:"):
            raise
        raise SystemExit(f"no model server answering at {a.engine[5:].partition(',')[0]} ({e}). Start it first: "
                         "Kev with run_kev.sh's command, CLM as in docs/4-zero-shot-reproductions.md section 4.6.")
    print(f"ready: http://127.0.0.1:{a.port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
