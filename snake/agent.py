"""One tick: formulation -> (maybe) one System One request -> move -> game.apply. Shared by the demo and the benchmark."""
import random

from .formulations import FORMULATIONS


def decide(engine, formulation, game, strategy="", rows=False):
    """Pick a move for `game` and return the full trace (the move is not applied yet)."""
    f = FORMULATIONS[formulation]
    req, code_move, ctx = f.request(game, strategy)
    trace = {"step": game.steps + 1, "formulation": f.name, "heading": game.heading}
    if req is None:
        return {**trace, "source": "code", "move": code_move, "how": ctx, "latency_ms": 0, "input_tokens": 0}
    answers, ms, tokens = engine.ask(req, f.independent)
    move, how = f.pick(game, answers, ctx)
    trace.update(source="model", move=move, how=how, request=req, answers=answers,
                 latency_ms=round(ms, 1), input_tokens=tokens,
                 option_dirs={o: f.to_dir(game, o) for o in req["questions"]["move"]["criteria"]})
    if rows:
        trace["rows"] = engine.rows(req, f.independent)
    return trace


def play_step(engine, formulation, game, strategy="", rows=False):
    trace = decide(engine, formulation, game, strategy, rows)
    trace["died"] = game.apply(trace["move"]) if not game.over else game.cause
    trace["ate"] = game.since_food == 0 and not trace["died"]
    return trace


# ---- code-only baselines for the benchmark (no model) ---------------------------------------------------------
def baseline_move(name, game, rng: random.Random):
    from .game import move_facts
    legal = game.legal() or [game.heading]
    if name == "random":                                 # a uniformly random move that survives this step
        return rng.choice(legal)
    facts = [move_facts(game, d) for d in legal]
    if name == "greedy":                                 # closest to food, never an immediately fatal cell
        return min(facts, key=lambda f: f["food_distance"] or 0)["dir"]
    if name == "greedy-safe":                            # the same, but skips dead ends when it can
        open_ = [f for f in facts if not f["dead_end"]] or facts
        return min(open_, key=lambda f: (f["food_distance"] or 0, -f["reachable"]))["dir"]
    raise ValueError(name)
