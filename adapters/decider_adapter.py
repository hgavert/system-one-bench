"""Decider 2B (huggingface.co/Mapika/decider-2b) on PyTorch MPS - runs in this repo's venv:

  uv run python adapters/decider_adapter.py > results/raw/decider-2b.jsonl
  uv run python adapters/decider_adapter.py models/decider-4b-v2 > results/raw/decider-4b-v2.jsonl

Zero-shot: the released v10 checkpoint, used as-is. Decider is a full fine-tune of Qwen3.5-2B that
reads the answer from option-letter logits in one pass. Its `decider/` package ships inside the
model repo; the CUDA-graph server is skipped (use_graphs=False) so the plain model runs on MPS.
The checkpoint's own temperature (1.3) is applied by Decider.system_one.
"""
import json
import sys
import time

import torch
# models/decider-2b = Mapika/decider-2b @ fa996cea58e1c1d8d1ab4d7124154f303b017f95 (code, config, tokenizer from the
# model repo; fetch both with: uv run python scripts/download_models.py --only decider-2b)
# models/decider-4b-v2 = Mapika/decider-4b @ tag v2 (scripts/download_models.py --only decider-4b-v2)
path = sys.argv[1] if len(sys.argv) > 1 else "models/decider-2b"
sys.path.insert(0, path)
from decider.infer import Decider  # noqa: E402

d = Decider(path, device="mps", dtype=torch.bfloat16, use_graphs=False)
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]


def ask(t):
    return d.system_one(t["text"], {"sentiment": t["question"]})["answers"]["sentiment"]


ask(tweets[0])                                                       # warm-up
for i, t in enumerate(tweets, 1):
    t0 = time.perf_counter()
    a = ask(t)
    torch.mps.synchronize()
    ms = (time.perf_counter() - t0) * 1000
    print(json.dumps({"id": t["id"], "pred": a["choice"], "probs": a["probabilities"], "latency_ms": ms}), flush=True)
    if i % 50 == 0:
        print(f"  {i}/{len(tweets)}", file=sys.stderr, flush=True)
