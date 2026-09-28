"""Hosted Jev (TypeSafe AI): endpoint, API key and a POST /v1/systemone that retries as TypeSafe asks.

The key is JEV_API_KEY in .env (or the shell environment). Every System One HTTP client in the repo goes through
post_systemone(), so local servers (Kev, CLM, GLiNER) get the same retry; they just never answer 429/529.

  from jev_client import JEV_URL, jev_client, post_systemone
  http = jev_client()
  out = post_systemone(http, {"model": "jev-latest", "state": "...", "questions": {...}})

Jev returns probabilities rounded to 2 decimals, so two options can tie: read the answer from `choice`, not max().
"""
import os
import random
import time

import httpx

JEV_URL = "https://api.typesafe.ai"
JEV_MODEL = "jev-latest"
RETRY = {429, 529, 500, 502, 503, 504}        # rate limit, overloaded, transient server errors


def jev_key() -> str:
    from dotenv import load_dotenv
    load_dotenv()
    if not (key := os.environ.get("JEV_API_KEY")):
        raise SystemExit("JEV_API_KEY is not set (.env or the shell environment)")
    return key


def jev_client(timeout: float = 120) -> httpx.Client:
    return httpx.Client(base_url=JEV_URL, timeout=timeout, headers={"authorization": f"Bearer {jev_key()}"})


def post_systemone(http: httpx.Client, body: dict, tries: int = 8) -> dict:
    """POST /v1/systemone, retrying 429/529/5xx and network errors with exponential backoff and jitter."""
    for attempt in range(tries):
        last = attempt == tries - 1
        try:
            r = http.post("/v1/systemone", json=body)
        except httpx.TransportError:
            if last:
                raise
            retry_after = 0.0
        else:
            if r.status_code not in RETRY or last:
                r.raise_for_status()
                return r.json()
            try:
                retry_after = float(r.headers.get("retry-after", 0) or 0)
            except ValueError:                        # an HTTP date instead of seconds: use the backoff
                retry_after = 0.0
        time.sleep(max(retry_after, min(60, 2 ** attempt)) * random.uniform(0.8, 1.2))
