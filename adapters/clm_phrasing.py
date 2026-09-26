"""CLM sensitivity to how the options are phrased (still zero-shot, no training).

CLM embeds each option's text on its own (the description, or the key when there is none) and
compares it with the embedded tweet + question. Its heads were trained on question -> answer
pairs and agent actions, so the wording of an option may matter more than for cross-encoders.
Needs clm-serve on :8700 (see docs/4-zero-shot-reproductions.md).

  uv run python adapters/clm_phrasing.py
"""
import json
from collections import Counter

import requests

from data import load_sample

Q = "What is the overall sentiment of this message?"
VARIANTS = {
    "descriptions (standard)": {"negative": "unhappy, angry, disappointed or critical",
                                "neutral": "factual or mixed, no clear feeling",
                                "positive": "happy, grateful, excited or praising"},
    "label words only": {"negative": None, "neutral": None, "positive": None},
    "label + description": {"negative": "negative: unhappy, angry, disappointed or critical",
                            "neutral": "neutral: factual or mixed, no clear feeling",
                            "positive": "positive: happy, grateful, excited or praising"},
    "answer sentences": {"negative": "The sentiment of this message is negative.",
                         "neutral": "The sentiment of this message is neutral.",
                         "positive": "The sentiment of this message is positive."},
}

data = load_sample(100)
out = {}
for name, crit in VARIANTS.items():
    preds = []
    for e in data:
        r = requests.post("http://127.0.0.1:8700/v1/systemone", json={
            "model": "clm-latest", "state": e.text,
            "questions": {"s": {"type": "choice", "instructions": Q, "criteria": crit}}}).json()
        preds.append(r["answers"]["s"]["choice"])
    acc = sum(p == e.label for p, e in zip(preds, data)) / len(data)
    per = {c: sum(p == e.label for p, e in zip(preds, data) if e.label == c) for c in ("negative", "neutral", "positive")}
    out[name] = {"accuracy": acc, "correct_per_class": per, "predicted": dict(Counter(preds))}
    print(f"{name:<26} accuracy {acc:.3f}  correct/100 {per}  predicted {dict(Counter(preds))}", flush=True)
json.dump(out, open("results/raw/clm_phrasing.json", "w"), indent=1)
