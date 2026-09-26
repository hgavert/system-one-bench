"""SemIf (github.com/TheoLeeCJ/openjev) on MLX - run with SemIf's own venv:

  third_party/openjev/.venv/bin/python adapters/semif_adapter.py [4b|9b] > results/raw/semif.jsonl

Zero-shot: stock Qwen3.5-4B-Base, no weights trained. SemIf renders the state, question and lettered
option descriptions as JSON in a chat prompt and reads the next-token logits of the answer letters.
We put "label: description" in each option description, the same text Laya and Kev see.
"""
import json
import sys

from semif_phase1 import mlx_backend

# The Decision Index ran SemIf on the base checkpoint (its README example uses the post-trained Qwen3.5-4B).
BASES = {"4b": ("Qwen/Qwen3.5-4B-Base", "1001bb4d826a52d1f399e183466143f4da7b741b"),
         "9b": ("Qwen/Qwen3.5-9B-Base", None)}   # 9b: not an index configuration, a variant (revision filled below)
size = sys.argv[1] if len(sys.argv) > 1 else "4b"
MODEL, REVISION = BASES[size]
if REVISION is None:
    from huggingface_hub import snapshot_download
    MODEL = snapshot_download(MODEL, local_files_only=True, allow_patterns=["*.json", "*.safetensors", "*.txt"])
    REVISION = MODEL.rstrip("/").split("/")[-1]                                      # local dir + commit label

model, tok, meta = mlx_backend.load_model(MODEL, REVISION)
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]


def row(t):
    q = t["question"]
    return {"id": t["id"], "state": t["text"], "question": q["instructions"],
            "options": [{"id": k, "description": f"{k}: {v}"} for k, v in q["criteria"].items()]}


mlx_backend.score(model, tok, row(tweets[0]), meta)                  # warm-up
for i, t in enumerate(tweets, 1):
    r = mlx_backend.score(model, tok, row(t), meta)
    probs = dict(zip(r["option_ids"], r["probabilities"]))
    print(json.dumps({"id": t["id"], "pred": max(probs, key=probs.get), "probs": probs,
                      "latency_ms": r["total_seconds"] * 1000}), flush=True)
    if i % 50 == 0:
        print(f"  {i}/{len(tweets)}", file=sys.stderr, flush=True)
