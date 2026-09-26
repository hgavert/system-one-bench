"""Step 9: score each Snake formulation on the same seeds, next to code-only baselines.

  uv run python 09_snake_benchmark.py                       # 4 formulations + 3 baselines, 10 seeds, 12x12
  uv run python 09_snake_benchmark.py --only facts --seeds 3
  uv run python 09_snake_benchmark.py --engine http:http://127.0.0.1:8009,kev-4b --only grid judged

A game ends on death, a full board, `--max-steps`, or `size*size` steps without food (starved).
Writes results/snake/games/<engine>-<name>.json (every decision, requests excluded) and results/snake/SUMMARY.md.
"""
import argparse
import json
import random
import statistics as st
import sys
import time
from pathlib import Path

from snake.agent import baseline_move, play_step
from snake.engine import engine_tag
from snake.formulations import FORMULATIONS
from snake.game import Game

BASELINES = ["random", "greedy", "greedy-safe"]
OUT = Path("results/snake/games")


def run(name, seeds, size, max_steps, engine=None):
    games = []
    for seed in seeds:
        g, rng, log = Game(size=size, seed=seed), random.Random(seed), []
        while not g.over and g.steps < max_steps:
            if name in BASELINES:
                g.apply(baseline_move(name, g, rng))
                continue
            t = play_step(engine, name, g)
            log.append({k: t.get(k) for k in ("step", "source", "move", "how", "latency_ms", "input_tokens", "died")}
                       | ({"probs": t["answers"]["move"]["probabilities"]} if "answers" in t else {}))
        games.append({"seed": seed, "score": g.score, "steps": g.steps, "cause": g.cause or "max steps", "decisions": log})
        print(f"  {name:12s} seed {seed}: score {g.score:2d}, {g.steps:3d} steps, {g.cause or 'max steps'}",
              file=sys.stderr, flush=True)
    return games


def summarise(name, games):
    lat = [d["latency_ms"] for g in games for d in g["decisions"] if d["source"] == "model"]
    tok = [d["input_tokens"] for g in games for d in g["decisions"] if d["source"] == "model"]
    n_dec = sum(len(g["decisions"]) for g in games)
    died = [g for g in games if g["cause"].startswith(("hit", "reversed"))]
    return {"name": name, "games": len(games),
            "score_mean": st.mean(g["score"] for g in games), "score_max": max(g["score"] for g in games),
            "steps_mean": st.mean(g["steps"] for g in games), "death_rate": len(died) / len(games),
            "starved": sum(g["cause"].startswith("starved") for g in games),
            "model_calls": len(lat), "code_ticks": n_dec - len(lat),
            "latency_p50_ms": st.median(lat) if lat else None, "latency_mean_ms": st.mean(lat) if lat else None,
            "tokens_p50": st.median(tok) if tok else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--size", type=int, default=12)
    ap.add_argument("--max-steps", type=int, default=500)
    ap.add_argument("--only", nargs="*", help="formulations / baselines to run")
    ap.add_argument("--engine", default="decider", help="decider | laya | http:<url>,<model>")
    a = ap.parse_args()
    names = a.only or [*FORMULATIONS, *BASELINES]
    seeds = list(range(a.seeds))
    engine = None
    if any(n in FORMULATIONS for n in names):
        from snake.engine import make_engine
        engine = make_engine(a.engine)
        for f in FORMULATIONS:                                   # warm up MPS kernels
            play_step(engine, f, Game(size=a.size))
    OUT.mkdir(parents=True, exist_ok=True)
    tag = engine_tag(a.engine)
    for n in names:
        t0 = time.time()
        games = run(n, seeds, a.size, a.max_steps, engine)
        s = summarise(n, games)
        s["wall_s"] = round(time.time() - t0, 1)
        s["engine"] = "code" if n in BASELINES else tag
        json.dump({"config": vars(a), "summary": s, "games": games},
                  open(OUT / f"{'code' if n in BASELINES else tag}-{n}.json", "w"))
        print(json.dumps(s), flush=True)

    rows = [json.load(open(p))["summary"] for p in sorted(OUT.glob("*.json"))]
    order = {n: i for i, n in enumerate([*FORMULATIONS, *BASELINES])}
    MODEL = {"decider": "Decider 2B", "decider-4b-v2": "Decider 4B", "kev-4b": "Kev 4B", "clm-latest": "CLM 8B",
             "gliner-decide": "GLiNER2.5-Decide", "gliner-decide-1b": "GLiNER2.5-Decide-1B", "laya": "Laya"}
    rank = {m: i for i, m in enumerate(MODEL)} | {"code": 99}
    rows.sort(key=lambda r: (rank.get(r["engine"], 50), order.get(r["name"], 99)))
    lines = ["| Controller | Food eaten (mean / best) | Steps | Died | Starved | Model calls | Code-only ticks | Latency p50 / mean | Tokens/call |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        who = (f"{MODEL.get(r['engine'], r['engine'])} · {FORMULATIONS[r['name']].title}" if r["name"] in FORMULATIONS
               else f"*{r['name']} (code only)*")
        mean = r.get("latency_mean_ms") or st.mean(d["latency_ms"] for g in json.load(open(OUT / f"{r['engine']}-{r['name']}.json"))["games"]
                                                  for d in g["decisions"] if d["source"] == "model") if r["model_calls"] else None
        lat = f"{r['latency_p50_ms']:.0f} / {mean:.0f} ms" if mean is not None else "–"
        tok = f"{r['tokens_p50']:.0f}" if r["tokens_p50"] else "–"
        lines.append(f"| {who} | {r['score_mean']:.1f} / {r['score_max']} | {r['steps_mean']:.0f} | "
                     f"{r['death_rate']:.0%} | {r['starved']} | {r['model_calls']} | {r['code_ticks']} | {lat} | {tok} |")
    (OUT.parent / "SUMMARY.md").write_text(f"{rows[0]['games']} seeds, {a.size}x{a.size} board, max {a.max_steps} steps.\n\n"
                                    + "\n".join(lines) + "\n")
    print("\n".join(lines))
