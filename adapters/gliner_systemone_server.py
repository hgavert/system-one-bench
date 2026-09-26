"""GLiNER2.5-Decide behind TypeSafe's POST /v1/systemone, so the Snake scripts can use it like Kev or CLM.

  third_party/gliner2-env/.venv/bin/python adapters/gliner_systemone_server.py --port 8710
  third_party/gliner2-env/.venv/bin/python adapters/gliner_systemone_server.py --model fastino/GLiNER2.5-Decide-1B --port 8711
  uv run python 09_snake_benchmark.py --engine http:http://127.0.0.1:8710,gliner-decide --only judged

Zero-shot, the released checkpoint. Uses gliner2's Classifier API, which returns a probability for every label
(adapters/gliner_adapter.py used classify_text, which only returns the winner). One Jev question -> one GLiNER task:
  choice -> single-label task, labels = criteria (name: description), instruction = instructions
  noul   -> single-label task with labels "true" / "false"
  score  -> ordinal task with labels "0".."n-1"; score = expected level
A dict state is sent as compact JSON, like Decider's render_state. '(' and ')' in labels and instructions become
'{' and '}' (see safe()). Stdlib HTTP server only.
"""
import argparse
import contextlib
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from gliner2 import AutoExtractor
from gliner2.classification import ClassificationSchema, Classifier


def text_of(v):
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def safe(v):
    """gliner2 rejects '(' and ')' in labels and instructions (it splices them into its prompt next to its own markers),
    e.g. the raw-board option 'move one row up (row - 1)'. Braces keep the meaning and can't form a reserved marker."""
    return text_of(v).replace("(", "{").replace(")", "}")


def to_schema(questions):
    s = ClassificationSchema()
    for qid, q in questions.items():
        t, ins, crit = q.get("type", "choice"), safe(q.get("instructions", "")), q.get("criteria")
        if t == "choice":
            labels = {k: (safe(v) if v not in (None, "") else None) for k, v in
                      (crit.items() if isinstance(crit, dict) else ((c, None) for c in crit))}
            s.single(qid, labels, instruction=ins)
        elif t == "noul":
            c = crit or {}
            s.single(qid, {"true": safe(c.get("true") or "yes"), "false": safe(c.get("false") or "no")},
                     instruction=ins)
        elif t == "score":
            levels = [crit[k] for k in sorted(crit, key=float)] if isinstance(crit, dict) else list(crit)
            s.ordinal(qid, {str(i): safe(d) for i, d in enumerate(levels)}, instruction=ins)
        else:
            raise ValueError(f"unknown question type {t!r}")
    return s


def answers(questions, result):
    out = {}
    for qid, q in questions.items():
        p = dict(result.probabilities(qid))
        t = q.get("type", "choice")
        if t == "noul":
            tot = p["true"] + p["false"] or 1.0
            out[qid] = {"type": "noul", "noul": p["true"] / tot}
            continue
        tot = sum(p.values()) or 1.0                   # softmax for single tasks already; normalise to be safe
        p = {k: v / tot for k, v in p.items()}
        top = max(p, key=p.get)
        if t == "score":
            out[qid] = {"type": "score", "score": sum(int(k) * v for k, v in p.items()), "confidence": p[top],
                        "probabilities": p}
        else:
            out[qid] = {"type": "choice", "choice": top, "confidence": p[top], "probabilities": p}
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            return self._send(200, {"data": [{"id": NAME}]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/systemone":
            return self._send(404, {"error": "not found"})
        body = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))) or b"{}")
        try:
            qs = body["questions"]
            with LOCK:
                t0 = time.perf_counter()
                r = CLF.classify(text_of(body["state"]), to_schema(qs))
                if DEV == "mps":
                    torch.mps.synchronize()
                ms = (time.perf_counter() - t0) * 1000
            self._send(200, {"model": NAME, "answers": answers(qs, r), "latency_ms": ms,
                             "usage": {"input_tokens": 0, "output_tokens": 0}})
        except Exception as e:                          # bad request shape, or a label gliner2 rejects
            self._send(400, {"error": f"{type(e).__name__}: {e}"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="fastino/GLiNER2.5-Decide")
    ap.add_argument("--port", type=int, default=8710)
    a = ap.parse_args()
    DEV = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    with contextlib.redirect_stdout(sys.stderr):        # gliner2 prints a banner on load
        m = AutoExtractor.from_pretrained(a.model).to(DEV)
    CLF, LOCK = Classifier(m, device=DEV), threading.Lock()
    NAME = a.model.split("/")[-1]
    print(f"{NAME} on {DEV}: http://127.0.0.1:{a.port}/v1/systemone", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
