"""Step 14 (vision Snake, test 4): can the model see the board? Perception questions with known answers, no games.

  third_party/clef-env/.venv/bin/python adapters/clef_server.py --port 8720               # Clef-flash
  uv run python 14_vision_snake_probe.py                                                  # image, clear style, joint
  uv run python 14_vision_snake_probe.py --modality text                                  # same questions, text board
  uv run python 14_vision_snake_probe.py --style plain --mode separate
  uv run python 14_vision_snake_probe.py --summary-only

The states are the text probe's (snake/probe_states.py, 150 states from noisy greedy games, seed 0), drawn by
vision_snake/render.py. The questions (vision_snake/perception.py): is the food above / right of the head, which
way is the head moving, and is each of the four cells next to the head free. `joint` asks all seven in one request
(one image, one forward pass, the way a game would ask); `separate` asks each on its own. Any /v1/systemone engine
works (snake.engine.make_engine); the image goes in the request's `images` as a PNG data URI.
Writes results/vision_snake/probe-<engine>.json (summary per condition) and probe-<engine>-<condition>.jsonl (rows).
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from snake.engine import engine_tag, make_engine
from snake.probe_states import sample_states
from vision_snake.perception import QUESTIONS, request
from vision_snake.render import STYLES, render

OUT = Path("results/vision_snake")


def p_true(answer, truth):
    """Probability the model gave the right option."""
    if answer["type"] == "noul":
        return answer["noul"] if truth == "true" else 1 - answer["noul"]
    return answer["probabilities"][truth]


def picked(answer):
    return ("true" if answer["noul"] >= 0.5 else "false") if answer["type"] == "noul" else answer["choice"]


def summarize(rows):
    out = {}
    for q in QUESTIONS:
        rs = [r for r in rows if r["q"] == q.id]
        if not rs:
            continue
        n = len(rs)
        by_truth = Counter(r["truth"] for r in rs)
        recall = {t: sum(r["pick"] == t for r in rs if r["truth"] == t) / k for t, k in by_truth.items()}
        out[q.id] = {"n": n, "acc": round(sum(r["pick"] == r["truth"] for r in rs) / n, 3),
                     "balanced_acc": round(sum(recall.values()) / len(recall), 3),
                     "p_truth": round(sum(r["p_truth"] for r in rs) / n, 3),
                     "majority": round(by_truth.most_common(1)[0][1] / n, 3),
                     "picks": dict(Counter(r["pick"] for r in rs))}
    lat = sorted(r["ms"] for r in rows if r.get("ms") is not None)
    out["_"] = {"p50_ms": round(lat[len(lat) // 2], 1) if lat else None,
                "input_tokens": max((r["tokens"] for r in rows), default=0)}
    return out


def table(summary):
    lines = [f"{'question':12s} {'n':>4s} {'acc':>6s} {'bal.acc':>8s} {'p(truth)':>9s} {'majority':>9s}"]
    for q, s in summary.items():
        if q != "_":
            lines.append(f"{q:12s} {s['n']:4d} {s['acc']:6.2f} {s['balanced_acc']:8.2f} {s['p_truth']:9.2f} "
                         f"{s['majority']:9.2f}")
    lines.append(f"p50 {summary['_']['p50_ms']} ms per request, {summary['_']['input_tokens']} input tokens")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="http:http://127.0.0.1:8720,clef-flash")
    ap.add_argument("--modality", choices=["image", "text"], default="image")
    ap.add_argument("--style", choices=list(STYLES), default="clear")
    ap.add_argument("--frames", type=int, choices=[1, 2], default=1, help="2: also show the board one step earlier")
    ap.add_argument("--mode", choices=["joint", "separate"], default="joint")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--save-frames", type=int, default=6, help="write the first N pictures to results/vision_snake/frames")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()

    tag = engine_tag(a.engine)
    path = OUT / f"probe-{tag}.json"
    done = json.load(open(path)) if path.exists() else {"results": {}}
    if a.summary_only:
        for cond, s in done["results"].items():
            print(f"\n== {cond}\n{table(s)}")
        raise SystemExit

    cond = f"{a.modality}-{a.style}{'-2f' if a.frames == 2 else ''}-{a.mode}" if a.modality == "image" else f"text-{a.mode}"
    e = make_engine(a.engine)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "frames").mkdir(exist_ok=True)
    rows_path = OUT / f"probe-{tag}-{cond}.jsonl"
    rows = []
    with open(rows_path, "w") as f:
        for i, (g, _) in enumerate(sample_states(a.n, seed=0)):
            if a.modality == "image" and i < a.save_frames:
                render(g, a.style).save(OUT / "frames" / f"{a.style}-{i:03d}.png")
            qs = [q for q in QUESTIONS if q.truth(g) is not None]
            for batch in [qs] if a.mode == "joint" else [[q] for q in qs]:
                ans, ms, tokens = e.ask(request(g, batch, a.modality, a.style, a.frames))
                for q in batch:
                    t = q.truth(g)
                    r = {"i": i, "q": q.id, "truth": t, "pick": picked(ans[q.id]), "p_truth": round(p_true(ans[q.id], t), 4),
                         "ms": round(ms, 1), "tokens": tokens}
                    rows.append(r)
                    f.write(json.dumps(r) + "\n")
            if (i + 1) % 25 == 0:
                print(f"{i + 1}/{a.n} states", flush=True)

    summary = summarize(rows)
    summary["_"]["engine"] = e.name
    print(f"\n== {cond} ({e.name})\n{table(summary)}")
    done["results"][cond] = summary
    json.dump(done, open(path, "w"), indent=1)
