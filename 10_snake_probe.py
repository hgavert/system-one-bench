"""Step 10: which way of asking works? Score formulations on fixed Snake situations, per model, without playing.

  uv run python 10_snake_probe.py                          # Decider 2B
  uv run python 10_snake_probe.py --engine laya
  uv run python 10_snake_probe.py --engine keyword          # phrase table, no model (snake.engine.KeywordEngine)
  ./run_kev.sh-style server on :8009, then: uv run python 10_snake_probe.py --engine http:http://127.0.0.1:8009,kev-4b

Two sets of situations (snake/probe_states.py), each move labelled good or not by code:
  all   150 states from noisy greedy games, with at least one bad legal move
  hard  100 states where going straight is legal but NOT good (the trap a heading-biased model falls into)
Reports: top choice is good, probability mass on good moves, and how often the model just went straight.
"""
import argparse
import json
from pathlib import Path

from snake.engine import engine_tag, make_engine
from snake.formulations import FORMULATIONS
from snake.probe_states import sample_states

VARIANTS = {
    "grid": "Raw board (as published)",
    "relative": "Relative, in words (as published)",
    "facts": "Facts in the options (as published)",
    "judged+state": "Judged options, with heading + food position in the state",
    "judged": "Judged options, verdicts only",
    "judged-plain": "Judged options, eating worded as 'closer'",
}


def request(v, g):
    if v == "judged+state":
        r, _, _ = FORMULATIONS["judged"].request(g)
        (hr, hc), (fr, fc) = g.snake[0], g.food
        where = [f"{hr - fr} up" if fr < hr else f"{fr - hr} down" if fr > hr else "",
                 f"{hc - fc} left" if fc < hc else f"{fc - hc} right" if fc > hc else ""]
        r["state"] = {"food": "the food is " + " and ".join(w for w in where if w) + " from the head",
                      "heading": g.heading, "snake_length": len(g.snake)}
        return r, FORMULATIONS["judged"]
    f = FORMULATIONS[v]
    return f.request(g)[0], f


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="decider")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    e = make_engine(a.engine)
    sets = {"all": sample_states(150, seed=0)}
    sets["hard"] = [(g, gd) for g, gd in sample_states(600, seed=1) if g.heading in g.legal() and g.heading not in gd][:100]
    out = {"engine": e.name, "results": {}}
    for v in a.only or VARIANTS:
        res = {}
        for sname, states in sets.items():
            hit = mass = straight = 0
            lat = []
            for g, good in states:
                r, f = request(v, g)
                ans, ms, _ = e.ask(r, f.independent)
                m = ans["move"]
                dirs = {o: f.to_dir(g, o) for o in m["probabilities"]}
                hit += dirs[m["choice"]] in good
                mass += sum(p for o, p in m["probabilities"].items() if dirs[o] in good)
                straight += dirs[m["choice"]] == g.heading
                lat.append(ms)
            n = len(states)
            res[sname] = {"n": n, "good": round(hit / n, 3), "mass": round(mass / n, 3),
                          "straight": round(straight / n, 3), "p50_ms": round(sorted(lat)[n // 2], 1)}
        out["results"][v] = res
        print(f"{v:14s} all: good {res['all']['good']:.2f} mass {res['all']['mass']:.2f} | "
              f"hard: good {res['hard']['good']:.2f} straight {res['hard']['straight']:.2f} | {res['all']['p50_ms']:.0f} ms",
              flush=True)
    Path("results/snake").mkdir(parents=True, exist_ok=True)
    tag = engine_tag(a.engine)
    path = Path(f"results/snake/probe-{tag}.json")
    if path.exists():                                   # --only adds to earlier results instead of replacing them
        out["results"] = json.load(open(path))["results"] | out["results"]
    json.dump(out, open(path, "w"), indent=1)
