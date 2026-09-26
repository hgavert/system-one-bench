"""Step 7 - Import predictions from an engine that ran in its own environment.

Some Jev reproductions pin their own torch / MLX versions, so they run in their own venv via a
small adapter (adapters/*.py) that reads data/test_tweets.jsonl and writes one JSON line per tweet:
    {"id": "t000", "pred": "positive", "probs": {"negative": .., "neutral": .., "positive": ..}, "latency_ms": 41.2}
This script scores that file exactly like 02_benchmark.py and writes results/runs/<name>.json.

  uv run python 07_import_predictions.py semif results/raw/semif.jsonl
"""
import importlib
import json
import sys
from pathlib import Path

from laya_classifier import Prediction

bench = importlib.import_module("02_benchmark")

name, path = sys.argv[1], Path(sys.argv[2])
tweets = [json.loads(l) for l in Path("data/test_tweets.jsonl").read_text().splitlines()]
raw = {r["id"]: r for r in map(json.loads, path.read_text().splitlines())}
missing = [t["id"] for t in tweets if t["id"] not in raw]
assert not missing, f"{len(missing)} tweets have no prediction, e.g. {missing[:3]}"

preds = [Prediction(raw[t["id"]]["pred"], raw[t["id"]]["probs"], raw[t["id"]]["latency_ms"] / 1000) for t in tweets]
gold = [t["gold"] for t in tweets]
wall_s = sum(p.latency_s for p in preds)          # sequential, one tweet per call
summary = bench.summarize(gold, preds, wall_s)
s = summary
print(f"{name}: accuracy {s['accuracy']:.3f}  macro-F1 {s['macro_f1']:.3f}  p50 {s['latency_ms_p50']:.0f} ms  "
      f"ECE {s['ece']:.3f}")
for lab, row in zip(["negative", "neutral", "positive"], s["confusion_matrix"]):
    print(f"  {lab:>8} {row}")
out = bench.RUNS / f"{name}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({
    "name": name, "system": f"import:{path}", "summary": summary,
    "predictions": [{"id": t["id"], "row": t["row"], "gold": t["gold"], "pred": p.label, "probs": p.probs,
                     "latency_ms": round(p.latency_s * 1000, 1)} for t, p in zip(tweets, preds)],
}, indent=1))
print(f"saved {out}")
