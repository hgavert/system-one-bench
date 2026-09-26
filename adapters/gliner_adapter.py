"""GLiNER2.5-Decide (huggingface.co/fastino/GLiNER2.5-Decide) - run with the gliner2 venv:

  third_party/gliner2-env/.venv/bin/python adapters/gliner_adapter.py fastino/GLiNER2.5-Decide > results/raw/gliner-decide.jsonl
  third_party/gliner2-env/.venv/bin/python adapters/gliner_adapter.py fastino/GLiNER2.5-Decide-1B > results/raw/gliner-decide-1b.jsonl

Zero-shot: the released checkpoint as-is. GLiNER2 is a schema-driven encoder (DeBERTa-v3-large for the
340M model): the task name, the question ("prompt") and every label with its description are packed in
front of the text - "sentiment: <question> [DESC] negative: <desc> [DESC] ..." - and one pass scores all
labels. So it receives the same field name, question and label descriptions as every other engine.
"""
import contextlib
import json
import sys
import time

import torch
from gliner2 import AutoExtractor

MODEL = sys.argv[1] if len(sys.argv) > 1 else "fastino/GLiNER2.5-Decide"
device = "mps" if torch.backends.mps.is_available() else "cpu"
with contextlib.redirect_stdout(sys.stderr):      # gliner2 prints a banner on load; keep stdout pure JSONL
    model = AutoExtractor.from_pretrained(MODEL)
try:
    model = model.to(device)
except Exception:                     # fall back to CPU if the extractor can't move
    device = "cpu"
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]
Q = tweets[0]["question"]
TASK = {"sentiment": {"labels": dict(Q["criteria"]), "prompt": Q["instructions"]}}


def ask(text):
    r = model.classify_text(text, TASK, include_confidence=True)["sentiment"]
    return r


print(f"device={device} sample={json.dumps(ask(tweets[0]['text']))}", file=sys.stderr, flush=True)   # warm-up + shape
for i, t in enumerate(tweets, 1):
    t0 = time.perf_counter()
    r = ask(t["text"])
    if device == "mps":
        torch.mps.synchronize()
    ms = (time.perf_counter() - t0) * 1000
    # gliner2 returns only the winning label and its confidence ({"label", "confidence"}); the other labels
    # share the remainder evenly so probs sum to 1. Accuracy, ECE and the cascade use only the top probability.
    label, conf = (r["label"], float(r["confidence"])) if isinstance(r, dict) else (r, 1.0)
    others = [k for k in Q["criteria"] if k != label]
    probs = {label: conf, **{k: (1 - conf) / len(others) for k in others}}
    print(json.dumps({"id": t["id"], "pred": label, "probs": probs, "latency_ms": ms, "raw": r}), flush=True)
    if i % 50 == 0:
        print(f"  {i}/{len(tweets)}", file=sys.stderr, flush=True)
