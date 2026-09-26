"""Step 2 - Benchmark sentiment classifiers on the same 300 TweetEval tweets.

Each run writes results/runs/<name>.json; 04_report.py combines them into one table.

  uv run python 02_benchmark.py laya                          # Laya English base (default)
  uv run python 02_benchmark.py laya-multilingual             # Laya mmBERT variant
  uv run python 02_benchmark.py laya-finetuned                # after 03_finetune_laya.py
  uv run python 02_benchmark.py kev-4b --url http://127.0.0.1:8009   # a running Kev server
  uv run python 02_benchmark.py s1:clm-latest --url http://127.0.0.1:8700 --name clm-8b   # CLM
  uv run python 02_benchmark.py llm:google/gemma-4-26b-a4b-qat       # a model in LM Studio
  uv run python 02_benchmark.py llm:google/gemma-4-26b-a4b-qat --prompt simple --name llm-gemma-26b-simple

Add --n-per-class 20 for a quick run.
"""
import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
from laya import ece_score
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from data import LABELS, load_sample
from laya_classifier import LayaSentiment, Prediction

RUNS = Path("results/runs")

LAYA_MODELS = {  # name -> (model id or path, subfolder)
    "laya": ("convaiinnovations/laya", None),
    "laya-multilingual": ("convaiinnovations/laya", "multilingual"),
    "laya-finetuned": ("./models/laya-tweet-sentiment", None),
}


def make_classifier(system: str, args):
    """Map a system name to an object with .classify(text) -> Prediction."""
    if system in LAYA_MODELS:
        return LayaSentiment(*LAYA_MODELS[system])
    if system.startswith("llm:"):
        from llm_classifier import LLMSentiment
        return LLMSentiment(system.removeprefix("llm:"), base_url=args.lmstudio_url,
                            reasoning_effort=None if args.reasoning == "default" else args.reasoning,
                            prompt=args.prompt)
    if system.startswith("kev"):
        from systemone_classifier import SystemOneSentiment
        return SystemOneSentiment(args.url)
    if system.startswith("s1:"):          # any TypeSafe System One server, by model name (e.g. CLM)
        from systemone_classifier import SystemOneSentiment
        return SystemOneSentiment(args.url, model=system.removeprefix("s1:"))
    raise SystemExit(f"unknown system {system!r}")


def summarize(gold: list[str], preds: list[Prediction], wall_s: float) -> dict:
    y_pred = [p.label for p in preds]
    lat_ms = sorted(p.latency_s * 1000 for p in preds)
    conf = np.array([max(p.probs.values()) for p in preds])
    correct = np.array([g == p for g, p in zip(gold, y_pred)], dtype=float)
    return {
        "n": len(gold),
        "accuracy": accuracy_score(gold, y_pred),
        "macro_f1": f1_score(gold, y_pred, labels=LABELS, average="macro"),
        "latency_ms_p50": statistics.median(lat_ms),
        "latency_ms_p95": lat_ms[int(0.95 * (len(lat_ms) - 1))],
        "throughput_msgs_per_s": len(gold) / wall_s,
        "ece": ece_score(conf, correct),  # 0 = the confidence numbers can be taken literally
        "confusion_matrix": confusion_matrix(gold, y_pred, labels=LABELS).tolist(),
        "selective_accuracy": selective_accuracy(gold, preds),
    }


def selective_accuracy(gold, preds, thresholds=(0.0, 0.5, 0.6, 0.7, 0.8, 0.9)) -> list[dict]:
    """If we only auto-accept answers above a confidence threshold, how good are they?"""
    rows = []
    for th in thresholds:
        kept = [(g, p) for g, p in zip(gold, preds) if max(p.probs.values()) >= th]
        acc = sum(g == p.label for g, p in kept) / len(kept) if kept else None
        rows.append({"threshold": th, "coverage": len(kept) / len(gold), "accuracy": acc})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("system", nargs="?", default="laya")
    ap.add_argument("--n-per-class", type=int, default=100)
    ap.add_argument("--batch-size", type=int, default=32, help="Laya batched-throughput pass")
    ap.add_argument("--url", default="http://127.0.0.1:8009", help="System One server (Kev)")
    ap.add_argument("--lmstudio-url", default="http://localhost:1234/v1")
    ap.add_argument("--reasoning", default="none", help="LLM reasoning_effort, or 'default'")
    ap.add_argument("--prompt", default="described", choices=["described", "simple"],
                    help="LLM prompt: class descriptions in a system prompt, or the bare instruction")
    ap.add_argument("--name", help="result name (default: derived from system)")
    args = ap.parse_args()
    name = args.name or args.system.replace("llm:", "llm-").replace("s1:", "").replace("/", "_")

    data = load_sample(n_per_class=args.n_per_class)
    texts, gold = [e.text for e in data], [e.label for e in data]
    print(f"{name}: {len(data)} tweets, balanced over {LABELS}")

    clf = make_classifier(args.system, args)
    clf.classify("warm-up call so model loading is not timed")

    t0 = time.perf_counter()
    preds = []
    for i, t in enumerate(texts, 1):
        preds.append(clf.classify(t))
        if i % 50 == 0:
            print(f"  {i}/{len(texts)}", flush=True)
    summary = summarize(gold, preds, time.perf_counter() - t0)

    if isinstance(clf, LayaSentiment):  # Laya can also score many messages per forward pass
        clf.classify_batch(texts[: args.batch_size])
        t0 = time.perf_counter()
        batched = []
        for i in range(0, len(texts), args.batch_size):
            batched.extend(clf.classify_batch(texts[i:i + args.batch_size]))
        summary["batched_throughput_msgs_per_s"] = len(texts) / (time.perf_counter() - t0)
        summary["batched_agrees_with_single"] = sum(
            a.label == b.label for a, b in zip(preds, batched)) / len(preds)

    s = summary
    print(f"\naccuracy {s['accuracy']:.3f}  macro-F1 {s['macro_f1']:.3f}  "
          f"p50 {s['latency_ms_p50']:.0f} ms  p95 {s['latency_ms_p95']:.0f} ms  "
          f"{s['throughput_msgs_per_s']:.1f} msg/s  ECE {s['ece']:.3f}")
    if "batched_throughput_msgs_per_s" in s:
        print(f"batched: {s['batched_throughput_msgs_per_s']:.1f} msg/s "
              f"(same label as single-call for {s['batched_agrees_with_single']:.0%})")
    print(f"confusion (rows = truth, cols = predicted {LABELS}):")
    for lab, row in zip(LABELS, s["confusion_matrix"]):
        print(f"  {lab:>8} {row}")

    RUNS.mkdir(parents=True, exist_ok=True)
    out = RUNS / f"{name}.json"
    out.write_text(json.dumps({
        "name": name, "system": args.system, "summary": summary,
        # tweets are referenced by position (t000...) and TweetEval test row, never stored as text
        "predictions": [{"id": f"t{i:03d}", "row": e.row, "gold": g, "pred": p.label, "probs": p.probs,
                         "latency_ms": round(p.latency_s * 1000, 1)}
                        for i, (e, g, p) in enumerate(zip(data, gold, preds))],
    }, indent=1))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
