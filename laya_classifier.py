"""Sentiment classification with Laya.

Two entry points:
  * classify(text)          - the public one-message API (agent.predict)
  * classify_batch(texts)   - many messages in ONE forward pass, for throughput
"""
import time
from dataclasses import dataclass

import laya
import numpy as np
import torch
from laya.common import QTYPES, build_sequence, collate_items, temp_bucket

from data import LABELS

SENTIMENT_QUESTION = {
    "type": "choice",
    "instructions": "What is the overall sentiment of this message?",
    "criteria": {
        "negative": "unhappy, angry, disappointed or critical",
        "neutral": "factual or mixed, no clear feeling",
        "positive": "happy, grateful, excited or praising",
    },
}


@dataclass
class Prediction:
    label: str
    probs: dict[str, float]  # label -> probability, sums to 1
    latency_s: float


class LayaSentiment:
    def __init__(self, model_id: str = "convaiinnovations/laya", subfolder: str | None = None,
                 device: str | None = None):
        self.agent = laya.load(model_id, device=device, subfolder=subfolder)

    def classify(self, text: str) -> Prediction:
        t0 = time.perf_counter()
        ans = self.agent.predict(text, {"sentiment": SENTIMENT_QUESTION})["answers"]["sentiment"]
        return Prediction(ans["choice"], ans["probabilities"], time.perf_counter() - t0)

    @torch.no_grad()
    def classify_batch(self, texts: list[str]) -> list[Prediction]:
        """Score many messages in one forward pass.

        agent.predict() batches over *questions* for a single state. Here we flip it:
        one question, many states. We reuse Laya's own sequence builder and collator so
        the model sees exactly the same input layout as in agent.predict().
        """
        a = self.agent
        t0 = time.perf_counter()
        q = a._to_internal(SENTIMENT_QUESTION)
        max_len, head_max_len = a.cfg.get("max_len", 512), a.cfg.get("head_max_len", 192)
        items = []
        for text in texts:
            ids, markers = build_sequence(a.tok, text, q, max_len, head_max_len)
            items.append({"ids": ids, "markers": markers, "qtype": QTYPES["choice"]})
        b = collate_items([items], a.tok.pad_token_id)
        logits, _act = a.model(*(b[k].to(a.device) for k in
                                 ("input_ids", "attention_mask", "marker_pos", "marker_mask", "qtype")))
        logits = logits.float().cpu().numpy()[:, : len(LABELS)]

        # Same calibration step as agent.predict(): divide by the fitted temperature, softmax.
        t = a.temperature_by_options.get(temp_bucket(QTYPES["choice"], len(LABELS)),
                                         a.temperature[QTYPES["choice"]])
        z = logits / t
        p = np.exp(z - z.max(axis=1, keepdims=True))
        p /= p.sum(axis=1, keepdims=True)
        per_item = (time.perf_counter() - t0) / len(texts)
        keys = list(SENTIMENT_QUESTION["criteria"])
        return [Prediction(keys[int(row.argmax())], dict(zip(keys, map(float, row))), per_item)
                for row in p]
