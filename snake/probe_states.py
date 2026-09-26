"""A fixed set of Snake situations with a known good answer, for testing formulations without playing games.

States come from seeded games of a noisy greedy player (so the snake ends up in varied, sometimes tight spots).
A move is "good" if it isn't a dead end and gets as close to the food as any non-dead-end move can.
"""
import random

from .game import Game, move_facts


def good_moves(g):
    facts = {d: move_facts(g, d) for d in g.legal()}
    open_ = {d: f for d, f in facts.items() if not f["dead_end"]} or facts
    best = min((0 if f["eats"] else f["food_distance"]) for f in open_.values())
    return {d for d, f in open_.items() if (0 if f["eats"] else f["food_distance"]) == best}, facts


def sample_states(n=150, size=12, seed=0, noise=0.3):
    """-> [(Game snapshot, good move set)] with at least one bad legal move (otherwise it isn't a test)."""
    import copy
    rng, out, s = random.Random(seed), [], 0
    while len(out) < n:
        g = Game(size=size, seed=1000 + s)
        s += 1
        while not g.over and len(out) < n and g.steps < 400:
            legal = g.legal()
            if not legal:
                break
            good, facts = good_moves(g)
            if len(legal) >= 2 and len(good) < len(legal) and rng.random() < 0.35:
                out.append((copy.deepcopy(g), good))
            if rng.random() < noise:
                g.apply(rng.choice(legal))
            else:
                g.apply(rng.choice(sorted(good)))
    return out
