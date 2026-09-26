"""Write the 300 benchmark tweets to data/test_tweets.jsonl for engines that run in their own environment.

Each line: {"id", "row", "text", "gold", "question"}; question is the same SENTIMENT_QUESTION every system gets;
row = the tweet's row in the TweetEval test split. data/ is git-ignored (tweet text is not redistributed).
Run:  uv run python adapters/export_test_tweets.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data import load_sample  # noqa: E402
from laya_classifier import SENTIMENT_QUESTION  # noqa: E402

out = Path("data/test_tweets.jsonl")
out.parent.mkdir(exist_ok=True)
with out.open("w") as f:
    for i, ex in enumerate(load_sample(n_per_class=100)):
        f.write(json.dumps({"id": f"t{i:03d}", "row": ex.row, "text": ex.text, "gold": ex.label,
                            "question": SENTIMENT_QUESTION}, ensure_ascii=False) + "\n")
print(f"wrote {out}")
