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
        self.http = httpx.Client(base_url=url, timeout=600,
                                 headers={"authorization": f"Bearer {api_key}"} if api_key else {})
        self.model = model

    def ask(self, request, independent=True):
        from jev_client import post_systemone
        t0 = time.perf_counter()
        out = post_systemone(self.http, {"model": self.model, **request})
        return out["answers"], (time.perf_counter() - t0) * 1000, out.get("usage", {}).get("input_tokens", 0)

    def rows(self, request, independent=True):
        return ["(served over HTTP: the model's internal prompt layout is not visible here)"]


def jev_engine(model=None):
    """Hosted Jev (TypeSafe AI), key from JEV_API_KEY. Latency includes the network round trip."""
    from jev_client import JEV_MODEL, JEV_URL, jev_key
    e = HTTPEngine(JEV_URL, model or JEV_MODEL, api_key=jev_key())
    e.name = f"Jev ({e.model}, hosted)"
    return e


class KeywordEngine:
    """No model: scores each option's text by the phrases it contains and answers the same Jev request.

    The judged options are code's facts written as words, so a phrase table reads them back. It can't read a
    board or compare numbers, and it ignores the player's strategy text. Matching is case-insensitive, so
    sorrycc's "EATS THE FOOD" and "DEAD END" also count. Score and noul questions (composed) get neutral answers.
    sample=False: top score (random tie-break); True: sample from softmax(score / temperature)."""
    WEIGHTS = {
        "eats the food": 3.0,
        "moves closer to the food": 3.0,
        "moves away from the food": -1.0,
        "keeps the most room": 2.0,
        "keeps almost as much room": 1.0,
        "leaves much less room": -2.0,
        "dead end": -100.0,
    }
    LESS_ROOM = r"\((\d+) of (\d+) cells\)"

    def __init__(self, sample=False, temperature=1.0, seed=0):
        import random
        self.name = f"keyword scorer ({f'sampled, T={temperature}' if sample else 'top score'})"
        self.sample, self.temperature, self.rng = sample, temperature, random.Random(seed)

    def score(self, text):
        import re
        t = text.lower()
        s = sum(w for phrase, w in self.WEIGHTS.items() if phrase in t)
        if m := re.search(self.LESS_ROOM, t):                       # the less room, the bigger the penalty
            n, best = map(int, m.groups())
            s -= 2.0 * (1 - n / best)
        return s

    def choose(self, criteria):
        import math
        scores = {o: self.score(text) for o, text in criteria.items()}
        top = max(scores.values())
        exp = {o: math.exp((s - top) / self.temperature) for o, s in scores.items()}
        probs = {o: e / sum(exp.values()) for o, e in exp.items()}
        if self.sample:
            choice = self.rng.choices(list(probs), weights=list(probs.values()))[0]
        else:
            choice = self.rng.choice([o for o, s in scores.items() if s == top])
        return {"choice": choice, "probabilities": probs, "confidence": probs[choice], "scores": scores}

    def ask(self, request, independent=True):
        t0 = time.perf_counter()
        out = {}
        for k, q in request["questions"].items():
            if q["type"] == "choice":
                out[k] = self.choose(q["criteria"])
            elif q["type"] == "score":
                out[k] = {"score": 0.0}
            elif q["type"] == "noul":
                out[k] = {"noul": 0.0}
        return out, (time.perf_counter() - t0) * 1000, 0

    def rows(self, request, independent=True):
        return [f"{o}: {self.score(t):+.2f}  {t}" for q in request["questions"].values() if q["type"] == "choice"
                for o, t in q["criteria"].items()]


def engine_tag(spec):
    """Short name for result files: 'decider', 'decider-4b-v2', 'kev-4b', 'clm-latest', 'gliner-decide', ..."""
    if spec.startswith("http:"):
        return spec.split(",")[-1]
    if spec.startswith("jev:"):
        return spec.split(":", 1)[1]
    if spec.startswith("decider:"):
        return spec.rstrip("/").split("/")[-1]
    return spec.replace(":", "-")


def make_engine(spec):
    """'decider' | 'decider:<model dir>' | 'laya' | 'http:<url>[,<model>]' | 'jev[:<model>]' | 'keyword' |
    'keyword-sample[:<T>]'"""
    if spec == "jev" or spec.startswith("jev:"):
        return jev_engine(spec.partition(":")[2] or None)
    if spec == "keyword":
        return KeywordEngine()
    if spec.startswith("keyword-sample"):
        return KeywordEngine(sample=True, temperature=float(spec.partition(":")[2] or 1.0))
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
