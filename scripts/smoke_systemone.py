"""Smoke-test any /v1/systemone server on real requests from all three tests, and estimate full-run times.

  uv run python scripts/smoke_systemone.py --url http://127.0.0.1:8720 --model clef-flash

Sends a small sample of each test's own requests (built by the tests' code, not hand-written):
  sentiment  10 tweets with the standard question
  snake      5 probe positions x 6 formulations (snake/probe_states.py, snake/formulations.py)
  finnish    3 items x every dataset and condition (finnish_questions.request)
and prints, per group: correct / sent, median and p90 latency, input tokens. The estimate multiplies those
latencies by each full run's request count (sentiment 300; Finnish 3,300; Snake per formulation: 10 games,
from the calls Decider 2B made up to the 5,000-call ceiling).
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finnish_questions import conditions_for, request as finnish_request  # noqa: E402
from snake.formulations import FORMULATIONS  # noqa: E402
from snake.probe_states import sample_states  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:8720")
ap.add_argument("--model", default="clef-flash")
args = ap.parse_args()
http = httpx.Client(base_url=args.url, timeout=600)


def ask(req):
    t = time.perf_counter()
    r = http.post("/v1/systemone", json={"model": args.model, **req})
    r.raise_for_status()
    return r.json(), (time.perf_counter() - t) * 1000


groups = {}            # name -> list of (ok or None, ms, input tokens)


def record(group, ok, ms, out):
    groups.setdefault(group, []).append((ok, ms, out.get("usage", {}).get("input_tokens")))


# warm-up (first request pays for kernel compilation)
first, ms = ask({"state": "warm-up", "questions": {"q": {"type": "noul", "instructions": "Is this a test?"}}})
print(f"warm-up: {ms:.0f} ms")

# --- sentiment ---
tweets = [json.loads(l) for l in open("data/test_tweets.jsonl")][:10]
for t in tweets:
    out, ms = ask({"state": t["text"], "questions": {"sentiment": t["question"]}})
    record("sentiment", out["answers"]["sentiment"]["choice"] == t["gold"], ms, out)

# --- snake: probe positions, every formulation ---
states = sample_states(n=5)
for fname, f in FORMULATIONS.items():
    for g, good in states:
        req, code_move, _ = f.request(g)
        if req is None:                              # code decided this tick (e.g. one legal move)
            continue
        out, ms = ask(req)
        try:
            move, _ = f.pick(g, out["answers"], None)
            ok = move in good
        except Exception:
            ok = None                                # formulation-specific pick needs game context
        record(f"snake · {fname}", ok, ms, out)

# --- finnish: 3 items per dataset and condition ---
for ds in ("sib", "belebele", "massive", "scandisent"):
    items = [json.loads(l) for l in open(f"data/finnish/{ds}.jsonl")][:3]
    for item in items:
        for cond in conditions_for(item):
            req, back = finnish_request(ds, item, cond)
            out, ms = ask(req)
            record(f"finnish · {ds} · {cond}", back.get(out["answers"]["q"]["choice"]) == item["gold"], ms, out)

# --- report ---
print(f"\n{'group':<34}{'correct':>9}{'p50 ms':>9}{'p90 ms':>9}{'tokens':>8}")
for g, rows in groups.items():
    oks = [o for o, _, _ in rows if o is not None]
    lat = sorted(ms for _, ms, _ in rows)
    toks = [t for _, _, t in rows if t]
    corr = f"{sum(oks)}/{len(oks)}" if oks else "-"
    print(f"{g:<34}{corr:>9}{statistics.median(lat):>9.0f}{lat[int(0.9 * (len(lat) - 1))]:>9.0f}"
          f"{(statistics.median(toks) if toks else 0):>8.0f}")


def med(prefix):
    return statistics.median(ms for g, rows in groups.items() if g.startswith(prefix) for _, ms, _ in rows)


# full-run request counts (see the docstring)
SNAKE_CALLS = {"grid": 70, "relative": 1446, "facts": 1603, "judged": 4419, "judged-plain": 4247, "composed": 4535}
sent_s = 300 * med("sentiment") / 1000
fin_s = 3300 * med("finnish") / 1000
snake_s = sum(n * statistics.median(ms for _, ms, _ in groups[f"snake · {k}"]) for k, n in SNAKE_CALLS.items()
              if f"snake · {k}" in groups) / 1000
snake_max = sum(5000 * statistics.median(ms for _, ms, _ in groups[f"snake · {k}"]) for k in SNAKE_CALLS
                if f"snake · {k}" in groups) / 1000
print(f"\nestimated full runs (model time only, one request at a time):")
print(f"  sentiment  300 requests          ~{sent_s / 60:.0f} min")
print(f"  finnish    3,300 requests        ~{fin_s / 60:.0f} min")
print(f"  snake      60 games              ~{snake_s / 60:.0f} min if it plays like Decider 2B, "
      f"up to ~{snake_max / 60:.0f} min if every game runs 500 steps")
