"""Decider 2B (models/decider-2b) behind a lock, plus the exact text it reads.

Decider answers a Jev-shaped request in one forward pass: every question becomes its own row
("Context: <state> / Question: ... / Options: (A) ... (B) ... / Answer: (") and the answer is the softmax over the
option-letter logits at the final "(" (temperature 1.3 from decider_config.json). Score questions are split into one
yes/no row per level ("isolated levels"). `rows()` rebuilds those rows the same way system_one() does, so the demo
can show exactly what the model saw.
"""
import sys
import threading
import time

import torch

PATH = "models/decider-2b"          # default; models/decider-4b-v2 via make_engine("decider:models/decider-4b-v2")


def _import_decider(path):
    """Each checkpoint ships its own `decider` package, so only one Decider version can be imported per process."""
    global Decider, Example, Q, MAX_OPTIONS, build, plan_rows, render_question, render_state
    sys.path.insert(0, path)
    from decider.infer import Decider, Example, Q
    from decider.prompt import MAX_OPTIONS, build
    from decider.systemone import plan_rows, render_question, render_state


def pick_device():
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


class _Keep:                     # system_one keeps option order as given; so do we
    def shuffle(self, x): pass
    def sample(self, xs, k): return xs[:k]


class DeciderEngine:
    def __init__(self, device=None, path=PATH):
        import json, os
        _import_decider(path)
        cfg = json.load(open(os.path.join(path, "decider_config.json")))
        size = "4B" if "4b" in path else "2B"
        self.name = f"Decider {size} ({cfg.get('version', '?')}, zero-shot)"
        device = device or pick_device()
        self.d = Decider(path, device=device, dtype=torch.bfloat16 if device != "cpu" else torch.float32,
                         use_graphs=False)
        self.lock = threading.Lock()
        self.device = device

    def ask(self, request, independent=True):
        """independent=True: one row per question (answers can't influence each other, N forward rows).
        independent=False: all questions behind one copy of the state, one row, one pass (faster on MPS)."""
        with self.lock:
            t0 = time.perf_counter()
            out = self.d.system_one(request["state"], request["questions"], independent=independent)
            if self.device == "mps":
                torch.mps.synchronize()
            elif self.device == "cuda":
                torch.cuda.synchronize()
            ms = (time.perf_counter() - t0) * 1000
        return out["answers"], ms, out["usage"]["input_tokens"]

    def rows(self, request, independent=True):
        """The decoded token sequence of every scoring row, as the model reads it."""
        if hasattr(self.d, "_system_one_items"):         # newer checkpoints (4B v2) expose system_one's own rows
            _, _, items = self.d._system_one_items(request["state"], request["questions"], independent)
            return [self.d.m.tok.decode(it["ids"]) for it in items]
        ctx = render_state(request["state"])
        rqs = {k: render_question(v) for k, v in request["questions"].items()}
        flat, _ = plan_rows(rqs, self.d.isolated_levels and independent)
        out = []
        for row in ([r] for r in flat) if independent else [flat]:
            it = build(Example(ctx, [Q(r["question"], list(r["options"]), 0) for r in row]), self.d.m.tok, _Keep(),
                       max_options=MAX_OPTIONS, max_ctx_tokens=32768)
            out.append(self.d.m.tok.decode(it["ids"]))
        return out


class LayaEngine:
    """Laya (encoder + head, 421M): same request dict, answered by laya's Agent.predict."""
    name = "Laya (zero-shot)"

    def __init__(self, device=None):
        import laya
        self.a = laya.load("convaiinnovations/laya", device=device or pick_device())
        self.lock = threading.Lock()

    def ask(self, request, independent=True):
        with self.lock:
            t0 = time.perf_counter()
            out = self.a.predict(request["state"], request["questions"])
            ms = (time.perf_counter() - t0) * 1000
        return out["answers"], ms, out.get("usage", {}).get("input_tokens", 0)

    def rows(self, request, independent=True):
        return ["(Laya lays the request out as one [MASK]-marked token sequence; see docs/2-typed-questions.md)"]


class HTTPEngine:
    """Any TypeSafe-compatible POST /v1/systemone server: Kev (./run_kev.sh), or hosted Jev with an API key."""

    def __init__(self, url="http://127.0.0.1:8009", model="kev-latest", api_key=None):
        import httpx
        self.name = f"{model} over HTTP"
        self.http = httpx.Client(base_url=url, timeout=60,
                                 headers={"authorization": f"Bearer {api_key}"} if api_key else {})
        self.model = model

    def ask(self, request, independent=True):
        t0 = time.perf_counter()
        r = self.http.post("/v1/systemone", json={"model": self.model, **request})
        r.raise_for_status()
        out = r.json()
        return out["answers"], (time.perf_counter() - t0) * 1000, out.get("usage", {}).get("input_tokens", 0)

    def rows(self, request, independent=True):
        return ["(served over HTTP: the model's internal prompt layout is not visible here)"]


def engine_tag(spec):
    """Short name for result files: 'decider', 'decider-4b-v2', 'kev-4b', 'clm-latest', 'gliner-decide', ..."""
    if spec.startswith("http:"):
        return spec.split(",")[-1]
    if spec.startswith("decider:"):
        return spec.rstrip("/").split("/")[-1]
    return spec


def make_engine(spec):
    """'decider' | 'decider:<model dir>' | 'laya' | 'http:<url>[,<model>]'"""
    if spec == "decider":
        return DeciderEngine()
    if spec.startswith("decider:"):
        return DeciderEngine(path=spec.split(":", 1)[1])
    if spec == "laya":
        return LayaEngine()
    if spec.startswith("http:"):
        url, _, model = spec[5:].partition(",")
        return HTTPEngine(url, model or "kev-latest")
    raise ValueError(spec)
