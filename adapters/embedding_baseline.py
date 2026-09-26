"""Embedding nearest-neighbour baseline: is a System One model just 'closest description in embedding space'?

Embed each "label: description" string once, embed each tweet, pick the label with the highest cosine
similarity. Zero-shot, no training. Uses nomic-embed-text-v1.5 served by LM Studio; nomic expects a task
prefix, and "classification: " is its prefix for this use.

  uv run python adapters/embedding_baseline.py > results/raw/embed-nomic.jsonl
  uv run python 07_import_predictions.py embed-nomic results/raw/embed-nomic.jsonl
"""
import json
import sys
import time

import numpy as np
from openai import OpenAI

client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
MODEL, PREFIX = "text-embedding-nomic-embed-text-v1.5", "classification: "


def embed(texts):
    r = client.embeddings.create(model=MODEL, input=[PREFIX + t for t in texts])
    v = np.array([d.embedding for d in r.data])
    return v / np.linalg.norm(v, axis=1, keepdims=True)


tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]
crit = tweets[0]["question"]["criteria"]
labels = list(crit)
label_vecs = embed([f"{k}: {v}" for k, v in crit.items()])   # computed once, independent of any tweet
embed(["warm-up"])
for t in tweets:
    t0 = time.perf_counter()
    sims = label_vecs @ embed([t["text"]])[0]                  # cosine similarity to each description
    ms = (time.perf_counter() - t0) * 1000
    p = np.exp(sims / 0.05); p /= p.sum()                      # softmax over similarities (T=0.05), for display only
    print(json.dumps({"id": t["id"], "pred": labels[int(sims.argmax())],
                      "probs": dict(zip(labels, map(float, p))), "latency_ms": ms, "sims": sims.round(4).tolist()}))
print("done", file=sys.stderr)
