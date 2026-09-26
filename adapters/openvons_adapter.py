"""openvons (github.com/genai-craft/openvons) - an inference technique over a stock instruct LLM.

Zero-shot: stock Qwen3-4B-Instruct-2507, no weights trained. openvons renders STATE / QUESTION /
lettered OPTIONS, asks the LLM for exactly one token with top_logprobs, and softmaxes the logprobs of
the option letters. The index served the LLM with vLLM; on a Mac we use mlx_lm.server, which returns
the same OpenAI-style top_logprobs. Start it first (Kev's venv has mlx-lm):

  third_party/kev/.venv/bin/python -m mlx_lm.server --model models/Qwen3-4B-Instruct-2507 --port 8300
  uv run python adapters/openvons_adapter.py > results/raw/openvons.jsonl
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "third_party/openvons"))
from openvons.lm.api.systemone import criteria_to_question  # noqa: E402
from openvons.lm.backends.llm_backend import LLMBackend  # noqa: E402

# "default_model" = whatever mlx_lm.server was started with (Qwen3-4B-Instruct-2507, the index configuration)
be = LLMBackend("http://127.0.0.1:8300/v1", "default_model", mode="logprob")
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]


def ask(t):
    q = criteria_to_question("sentiment", t["question"])
    dec = be.decide(t["text"], [q])[0]
    return dict(zip(q.ids, dec.probs)), dec.latency_ms, dec.info


ask(tweets[0])                                                       # warm-up
for i, t in enumerate(tweets, 1):
    probs, ms, info = ask(t)
    print(json.dumps({"id": t["id"], "pred": max(probs, key=probs.get), "probs": probs, "latency_ms": ms,
                      "raw": info.get("content")}), flush=True)
    if i % 50 == 0:
        print(f"  {i}/{len(tweets)}", file=sys.stderr, flush=True)
