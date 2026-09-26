"""Step 5 - Cascade: let Laya answer when it is confident, send the rest to the LLM.

This is what calibrated probabilities are for. Computed from saved runs, no new inference:

  uv run python 05_cascade.py --fast semif                     # SemIf (zero-shot) -> Gemma 26B
  uv run python 05_cascade.py --fast kev-9b --slow llm-google_gemma-4-26b-a4b-qat
"""
import argparse
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--fast", default="semif")
ap.add_argument("--slow", default="llm-google_gemma-4-26b-a4b-qat")
args = ap.parse_args()

load = lambda n: json.loads(Path(f"results/runs/{n}.json").read_text())["predictions"]
fast, slow = load(args.fast), load(args.slow)
assert [f["id"] for f in fast] == [s["id"] for s in slow], "runs must use the same tweets"

rows = []
for th in [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]:
    correct = ms = llm_calls = 0
    for f, s in zip(fast, slow):
        if th <= 1:                             # "LLM only" row skips Laya entirely
            ms += f["latency_ms"]
        if max(f["probs"].values()) >= th:
            correct += f["pred"] == f["gold"]
        else:                                   # not confident enough -> escalate
            llm_calls += 1
            ms += s["latency_ms"]
            correct += s["pred"] == s["gold"]
    n = len(fast)
    rows.append({"threshold": th, "accuracy": correct / n, "llm_share": llm_calls / n,
                 "avg_ms": ms / n})

print(f"cascade: {args.fast} -> {args.slow} when {args.fast} confidence < threshold\n")
print(f"{'threshold':>9} {'accuracy':>9} {'sent to LLM':>12} {'avg ms/msg':>11}")
for r in rows:
    label = "LLM only" if r["threshold"] > 1 else f"{r['threshold']:.1f}"
    print(f"{label:>9} {r['accuracy']:>9.3f} {r['llm_share']:>12.0%} {r['avg_ms']:>11.0f}")
out = Path(f"results/cascades/{args.fast}.json")
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({**vars(args), "rows": rows}, indent=1))
print(f"saved {out}")
