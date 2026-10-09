"""Step 15 (vision Snake, test 4): moves from a picture. Single decisions with a known answer, then games.

  uv run python 15_vision_snake.py probe                         # see-4, see-legal, see-ask on the probe states
  uv run python 15_vision_snake.py games --seeds 10              # the same three, played on seeds 0-9
  uv run python 15_vision_snake.py games --only see-ask --style blocks --frames 2
  uv run python 15_vision_snake.py summary                       # tables from what is saved

The requests are in vision_snake/formulations.py. `probe` uses the text probe's states (snake/probe_states.py): `all`
(150 states with at least one bad legal move) and `hard` (100 where going straight is legal but not good). A choice of
going back the way the snake came counts as going straight, since that is what the game does with it. `games` uses
the text test's rules (12x12, 500-step cap, starved after 144 steps without food) and seeds, so the results line up
with results/snake/games. Each finished game is appended to games/<...>.partial.jsonl, so a stopped `games`
run picks up at the next seed. Writes results/vision_snake/moves-<engine>.json and games/<engine>-<name>-<style>.json.
"""
import argparse
import copy
import json
import statistics as st
import sys
import time
from pathlib import Path

from snake.engine import engine_tag, make_engine
from snake.game import OPPOSITE, Game
from snake.probe_states import sample_states
from vision_snake.formulations import FORMULATIONS
from vision_snake.render import STYLES

OUT = Path("results/vision_snake")


def decide(engine, f, g, prev=None):
    req, code_move, ctx = f.request(g, prev)
    if req is None:
        return {"source": "code", "move": code_move, "how": ctx, "latency_ms": 0, "input_tokens": 0}
    answers, ms, tokens = engine.ask(req)
    move, how, probs = f.pick(g, answers, ctx)
    return {"source": "model", "move": move, "how": how, "probs": {k: round(v, 4) for k, v in probs.items()},
            "latency_ms": round(ms, 1), "input_tokens": tokens}


def effective(g, d):
    return g.heading if d == OPPOSITE[g.heading] else d


def probe(engine, f, sets):
    res = {}
    for sname, states in sets.items():
        hit = mass = straight = fatal = 0
        lat = []
        for g, good in states:
            t = decide(engine, f, g)
            d = effective(g, t["move"])
            hit += d in good
            straight += d == g.heading
            fatal += d not in g.legal()
            if t["source"] == "model":
                mass += sum(p for o, p in t["probs"].items() if effective(g, o) in good)
                lat.append(t["latency_ms"])
            else:
                mass += t["move"] in good
        n = len(states)
        res[sname] = {"n": n, "good": round(hit / n, 3), "mass": round(mass / n, 3), "straight": round(straight / n, 3),
                      "fatal": round(fatal / n, 3), "p50_ms": round(sorted(lat)[len(lat) // 2], 1) if lat else None}
    return res


def play(engine, f, seeds, size, max_steps, partial: Path):
    """Plays the seeds not yet in `partial` (one finished game per line), so a stopped run resumes where it was."""
    games = [json.loads(l) for l in open(partial)] if partial.exists() else []
    done = {g["seed"] for g in games}
    for seed in seeds:
        if seed in done:
            continue
        g, prev, log = Game(size=size, seed=seed), None, []
        while not g.over and g.steps < max_steps:
            t = decide(engine, f, g, prev)
            prev = copy.deepcopy(g)
            t["died"] = g.apply(t["move"])
            t["step"] = g.steps
            log.append(t)
        games.append({"seed": seed, "score": g.score, "steps": g.steps, "cause": g.cause or "max steps", "decisions": log})
        with open(partial, "a") as out:
            out.write(json.dumps(games[-1]) + "\n")
        print(f"  {f.name:10s} seed {seed}: score {g.score:2d}, {g.steps:3d} steps, {g.cause or 'max steps'}",
              file=sys.stderr, flush=True)
    return sorted((g for g in games if g["seed"] in seeds), key=lambda g: g["seed"])


def summarise(games):
    model = [d for g in games for d in g["decisions"] if d["source"] == "model"]
    return {"games": len(games), "score_mean": st.mean(g["score"] for g in games),
            "score_max": max(g["score"] for g in games), "steps_mean": st.mean(g["steps"] for g in games),
            "steps_median": st.median(g["steps"] for g in games),
            "died": sum(g["cause"].startswith(("hit", "reversed")) for g in games),
            "starved": sum(g["cause"].startswith("starved") for g in games),
            "model_calls": len(model), "latency_p50_ms": st.median(d["latency_ms"] for d in model) if model else None}


def cond_name(name, style, frames):
    return f"{name}-{style}" + ("-2f" if frames == 2 else "")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["probe", "games", "summary"])
    ap.add_argument("--engine", default="http:http://127.0.0.1:8720,clef-flash")
    ap.add_argument("--only", nargs="*", choices=list(FORMULATIONS))
    ap.add_argument("--style", choices=list(STYLES), default="blocks")
    ap.add_argument("--frames", type=int, choices=[1, 2], default=1)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--size", type=int, default=12)
    ap.add_argument("--max-steps", type=int, default=500)
    a = ap.parse_args()
    tag = engine_tag(a.engine)
    moves_path = OUT / f"moves-{tag}.json"
    (OUT / "games").mkdir(parents=True, exist_ok=True)

    if a.what == "summary":                         # markdown tables; also written to SUMMARY.md (games/ is gitignored)
        lines = []
        if moves_path.exists():
            lines += ["## Single moves", "", "| Request | Good pick, all / hard | Straight on hard | Fatal pick, all / hard "
                      "| Per move |", "|---|--:|--:|--:|--:|"]
            for c, r in json.load(open(moves_path))["results"].items():
                lines.append(f"| {c} | {r['all']['good']:.2f} / {r['hard']['good']:.2f} | {r['hard']['straight']:.2f} | "
                             f"{r['all']['fatal']:.2f} / {r['hard']['fatal']:.2f} | {r['all']['p50_ms']:.0f} ms |")
        games = sorted((OUT / "games").glob(f"{tag}-*.json"))
        if games:
            lines += ["", "## Games", "", "| Request | Food mean / best | Steps, median | Died | Starved | Per model call |",
                      "|---|--:|--:|--:|--:|--:|"]
            for p in games:
                s = json.load(open(p))["summary"]
                lines.append(f"| {p.stem} | {s['score_mean']:.1f} / {s['score_max']} | {s['steps_median']:.0f} | "
                             f"{s['died']} of {s['games']} | {s['starved']} | {s['latency_p50_ms']:.0f} ms |")
            (OUT / "SUMMARY.md").write_text(f"# Vision Snake, {tag}\n\n" + "\n".join(lines) + "\n")
        print("\n".join(lines))
        raise SystemExit

    e = make_engine(a.engine)
    names = a.only or list(FORMULATIONS)
    if a.what == "probe":
        sets = {"all": sample_states(150, seed=0)}
        sets["hard"] = [(g, gd) for g, gd in sample_states(600, seed=1) if g.heading in g.legal() and g.heading not in gd][:100]
        done = json.load(open(moves_path)) if moves_path.exists() else {"results": {}}
        for n in names:
            r = probe(e, FORMULATIONS[n](a.style, a.frames), sets)
            c = cond_name(n, a.style, a.frames)
            done["results"][c] = r
            json.dump(done, open(moves_path, "w"), indent=1)
            print(f"{c:26s} all: good {r['all']['good']:.2f} fatal {r['all']['fatal']:.2f} | hard: good "
                  f"{r['hard']['good']:.2f} straight {r['hard']['straight']:.2f} fatal {r['hard']['fatal']:.2f} | "
                  f"{r['all']['p50_ms']} ms", flush=True)
    else:
        for n in names:
            t0 = time.time()
            path = OUT / "games" / f"{tag}-{cond_name(n, a.style, a.frames)}.json"
            partial = path.with_suffix(".partial.jsonl")
            games = play(e, FORMULATIONS[n](a.style, a.frames), list(range(a.seeds)), a.size, a.max_steps, partial)
            s = summarise(games) | {"wall_s": round(time.time() - t0, 1), "engine": tag, "name": n,
                                    "style": a.style, "frames": a.frames}
            json.dump({"config": vars(a), "summary": s, "games": games}, open(path, "w"))
            partial.unlink()
            print(json.dumps(s), flush=True)
