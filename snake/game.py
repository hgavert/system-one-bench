"""Snake rules and exact per-move facts. Pure Python, no model.

The engine owns the rules (walls, body, growth, seeded food). The model only ever picks a direction.
Coordinates are (row, col) with row 0 at the top, as in every published Jev snake demo.
"""
import random
from dataclasses import dataclass, field

DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
CLOCKWISE = {"up": "right", "right": "down", "down": "left", "left": "up"}
COUNTER = {v: k for k, v in CLOCKWISE.items()}


def step_point(p, d):
    return p[0] + DIRS[d][0], p[1] + DIRS[d][1]


def turn_of(heading, d):
    """Absolute direction -> 'straight' / 'left turn' / 'right turn' (never a reversal)."""
    if d == heading:
        return "straight"
    return "right turn" if CLOCKWISE[heading] == d else "left turn"


@dataclass
class Game:
    size: int = 12
    seed: int = 0
    starve_after: int = 0            # 0 = size*size: ends a game that circles forever without eating
    snake: list = field(default_factory=list)    # head first
    heading: str = "up"
    food: tuple | None = None
    steps: int = 0
    since_food: int = 0
    score: int = 0
    over: bool = False
    cause: str | None = None

    def __post_init__(self):
        self.rng = random.Random(self.seed)
        self.starve_after = self.starve_after or self.size * self.size
        m = self.size // 2
        self.snake = [(m, m), (m + 1, m), (m + 2, m)]
        self.food = self._place_food()

    def _place_food(self):
        free = [(r, c) for r in range(self.size) for c in range(self.size) if (r, c) not in self.snake]
        return self.rng.choice(free) if free else None

    def inside(self, p):
        return 0 <= p[0] < self.size and 0 <= p[1] < self.size

    def fatal(self, d):
        """Why moving `d` now ends the game, or None. The tail cell is safe unless we eat (it moves away)."""
        if d == OPPOSITE[self.heading]:
            return "reversed into its own neck"
        t = step_point(self.snake[0], d)
        if not self.inside(t):
            return "hit the wall"
        body = self.snake if t == self.food else self.snake[:-1]
        if t in body:
            return "hit its own body"
        return None

    def legal(self):
        return [d for d in DIRS if self.fatal(d) is None]

    def apply(self, d):
        """Move one cell. Returns the cause string if the snake died."""
        if self.over:
            return self.cause
        if d == OPPOSITE[self.heading]:      # like the Nokia original: a reversal is ignored, keep going
            d = self.heading
        why = self.fatal(d)
        self.steps += 1
        if why:
            self.over, self.cause = True, why
            return why
        t = step_point(self.snake[0], d)
        self.heading = d
        if t == self.food:
            self.snake = [t, *self.snake]
            self.score += 1
            self.since_food = 0
            self.food = self._place_food()
            if self.food is None:
                self.over, self.cause = True, "filled the board"
        else:
            self.snake = [t, *self.snake[:-1]]
            self.since_food += 1
            if self.since_food >= self.starve_after:
                self.over, self.cause = True, f"starved ({self.starve_after} steps without food)"
        return self.cause

    # ---- views -------------------------------------------------------------------------------------------------
    def board(self):
        """Text grid: H head, o body, T tail, F food, . empty."""
        g = [["."] * self.size for _ in range(self.size)]
        if self.food:
            g[self.food[0]][self.food[1]] = "F"
        for i, (r, c) in enumerate(self.snake):
            g[r][c] = "H" if i == 0 else "T" if i == len(self.snake) - 1 else "o"
        return ["".join(row) for row in g]

    def frame(self):
        return {"size": self.size, "snake": [list(p) for p in self.snake], "food": list(self.food) if self.food else None,
                "heading": self.heading, "steps": self.steps, "score": self.score, "over": self.over, "cause": self.cause}


# ---- exact facts code computes for every candidate move (sorrycc/typesafe-snake's analysis.ts, ported) ---------
def flood(g: Game, start, blocked):
    seen, stack = set(), [start]
    while stack:
        p = stack.pop()
        for d in DIRS:
            n = step_point(p, d)
            if g.inside(n) and n not in blocked and n not in seen:
                seen.add(n)
                stack.append(n)
    return seen


def move_facts(g: Game, d):
    t = step_point(g.snake[0], d)
    eats = t == g.food
    after = [t, *(g.snake if eats else g.snake[:-1])]
    blocked = set(after)
    region = flood(g, t, blocked)
    tail = after[-1]
    can_reach_tail = any(step_point(tail, k) == t or step_point(tail, k) in region for k in DIRS)
    return {
        "dir": d,
        "turn": turn_of(g.heading, d),
        "target": t,
        "eats": eats,
        "food_distance": abs(g.food[0] - t[0]) + abs(g.food[1] - t[1]) if g.food else None,
        "reachable": len(region),
        "free_total": g.size * g.size - len(after),
        "dead_end": len(region) < len(after) and not can_reach_tail,
        "can_reach_tail": can_reach_tail,
    }


def ray(g: Game, d):
    """Free cells straight ahead in direction d before a wall or the body (nadeem4/jev-demo's `_look`)."""
    body = set(g.snake[:-1])
    p, free = g.snake[0], 0
    while True:
        p = step_point(p, d)
        if not g.inside(p):
            return free, "the wall"
        if p in body:
            return free, "your own body"
        free += 1
