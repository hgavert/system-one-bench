"""Position-bias test: the same 300 tweets with the three options in all 6 orders.

Each engine gets exactly the standard question, only the order of `criteria` changes. Writes one line
per (tweet, order): {"id", "order", "pred", "probs"} to results/raw/posbias_<engine>.jsonl.

  uv run python adapters/position_bias.py laya
  uv run python adapters/position_bias.py decider
  uv run python adapters/position_bias.py decider:models/decider-4b-v2 decider-4b-v2
  third_party/openjev/.venv/bin/python adapters/position_bias.py semif      # SemIf's own venv
  uv run python adapters/position_bias.py http:http://127.0.0.1:8009,kev-latest kev-4b   # any /v1/systemone server:
  uv run python adapters/position_bias.py http:http://127.0.0.1:8700,clm-latest clm-8b   #   Kev, CLM, GLiNER (commands
  uv run python adapters/position_bias.py http:http://127.0.0.1:8710,gliner-decide gliner-decide   # in docs/5-snake.md §5.7)
  uv run python 11_position_bias.py                                          # analysis
"""
import itertools
import json
import sys

engine = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else engine                   # -> results/raw/posbias_<name>.jsonl
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]
Q = tweets[0]["question"]
ORDERS = list(itertools.permutations(Q["criteria"]))          # 6 orders of (negative, neutral, positive)


def question(order):
    return {**Q, "criteria": {k: Q["criteria"][k] for k in order}}


if engine == "laya":
    import laya
    agent = laya.load("convaiinnovations/laya")
    ask = lambda text, order: agent.predict(text, {"s": question(order)})["answers"]["s"]["probabilities"]
elif engine.split(":")[0] == "decider":                                # decider or decider:<model dir>
    import torch
    path = engine.partition(":")[2] or "models/decider-2b"
    sys.path.insert(0, path)
    from decider.infer import Decider
    d = Decider(path, device="mps", dtype=torch.bfloat16, use_graphs=False)
    ask = lambda text, order: d.system_one(text, {"s": question(order)})["answers"]["s"]["probabilities"]
elif engine == "semif":
    from semif_phase1 import mlx_backend
    model, tok, meta = mlx_backend.load_model("Qwen/Qwen3.5-4B-Base", "1001bb4d826a52d1f399e183466143f4da7b741b")

    def ask(text, order):
        crit = question(order)["criteria"]
        row = {"id": "x", "state": text, "question": Q["instructions"],
               "options": [{"id": k, "description": f"{k}: {v}"} for k, v in crit.items()]}
        r = mlx_backend.score(model, tok, row, meta)
        return dict(zip(r["option_ids"], r["probabilities"]))
elif engine.startswith("http:"):                                      # http:<base url>,<model>
    import httpx
    url, model = engine.removeprefix("http:").rsplit(",", 1)
    http = httpx.Client(base_url=url, timeout=600)            # the first request can be slow (warm-up)

    def ask(text, order):
        r = http.post("/v1/systemone", json={"model": model, "state": text, "questions": {"s": question(order)}})
        r.raise_for_status()
        return r.json()["answers"]["s"]["probabilities"]
else:
    sys.exit(f"unknown engine {engine}")

with open(f"results/raw/posbias_{name}.jsonl", "w") as out:
    for n, order in enumerate(ORDERS, 1):
        for t in tweets:
            probs = ask(t["text"], order)
            out.write(json.dumps({"id": t["id"], "order": list(order), "pred": max(probs, key=probs.get),
                                  "probs": {k: float(v) for k, v in probs.items()}}) + "\n")
        out.flush()
        print(f"  {name}: order {n}/6 {order} done", file=sys.stderr, flush=True)
