"""Sentiment classification against any TypeSafe System One-compatible HTTP server.

Kev (github.com/jaredpalmer/kev) serves this API locally; so does TypeSafe's hosted Jev.
Same question definition as the Laya classifier - the request body is plain JSON.
"""
import time

import httpx

from laya_classifier import SENTIMENT_QUESTION, Prediction


class SystemOneSentiment:
    def __init__(self, base_url: str = "http://127.0.0.1:8009", model: str = "kev-latest",
                 api_key: str | None = None):
        headers = {"authorization": f"Bearer {api_key}"} if api_key else {}
        self.http = httpx.Client(base_url=base_url, headers=headers, timeout=120)
        self.model = model

    def classify(self, text: str) -> Prediction:
        t0 = time.perf_counter()
        r = self.http.post("/v1/systemone", json={
            "model": self.model,
            "state": text,
            "questions": {"sentiment": SENTIMENT_QUESTION},
        })
        r.raise_for_status()
        ans = r.json()["answers"]["sentiment"]
        return Prediction(ans["choice"], ans["probabilities"], time.perf_counter() - t0)
