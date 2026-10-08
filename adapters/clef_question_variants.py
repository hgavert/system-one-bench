"""Does Clef-flash's sentiment accuracy depend on the question ID or the label descriptions? (zero-shot)

Clef renders each question as "FIELD 1 / ID: <question id> / TYPE: choice / INSTRUCTION: ..." and sorts the
options alphabetically, so the question ID is part of the model input. This sends the same 300 tweets with
four variants of the standard question to the Clef server (adapters/clef_server.py on :8720):

  uv run python adapters/clef_question_variants.py      # -> results/raw/clef_question_variants.json
"""
import json
from collections import Counter

import httpx

tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")]
Q = tweets[0]["question"]
labels_only = {**Q, "criteria": {k: None for k in Q["criteria"]}}
VARIANTS = {                                    # name -> (question id, question)
    'id "sentiment", descriptions (main run)': ("sentiment", Q),
    'id "s", descriptions (option-order run)': ("s", Q),
    'id "q", descriptions': ("q", Q),
    'id "sentiment", label words only': ("sentiment", labels_only),
}
http = httpx.Client(base_url="http://127.0.0.1:8720", timeout=600)
out = {}
for name, (qid, q) in VARIANTS.items():
    preds = []
    for t in tweets:
        r = http.post("/v1/systemone", json={"model": "clef-flash", "state": t["text"], "questions": {qid: q}})
        r.raise_for_status()
        preds.append(r.json()["answers"][qid]["choice"])
    acc = sum(p == t["gold"] for p, t in zip(preds, tweets)) / len(tweets)
    per = {c: sum(p == t["gold"] for p, t in zip(preds, tweets) if t["gold"] == c) for c in Q["criteria"]}
    out[name] = {"accuracy": acc, "correct_per_class": per, "predicted": dict(Counter(preds)), "preds": preds}
    print(f"{name:<44} accuracy {acc:.3f}  correct/100 {per}  predicted {dict(Counter(preds))}", flush=True)
json.dump(out, open("results/raw/clef_question_variants.json", "w"), indent=1)
