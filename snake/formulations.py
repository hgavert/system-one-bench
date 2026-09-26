"""Six ways to ask a System One model for a Snake move, four from published Jev snake demos, two written here.

Each formulation turns a Game into one Jev-shaped request ({"state", "questions"}, the POST /v1/systemone body) and
turns the typed answers back into a move. Code can also decide on its own (only one safe move) and skip the model.

  grid      raw board + coordinates, 3 directions      iammusham/jev-snake, coderhh/jev-snake
  relative  words about what's left/ahead/right         nadeem4/jev-demo (arena/games/snake.py)
  facts     only safe moves, each with computed facts   sorrycc/typesafe-snake (src/jev/prompt.ts)
  judged    facts rewritten as verdicts in words          this repo (what a 2B model needs)
  judged-plain  the same, eating worded as "closer"         this repo (what CLM 8B needs)
  composed  judged + danger score + survival yes/no,    ximing/jev-snake-game (packages/game/src/compose.ts)
            combined by code with thresholds
"""
from .game import CLOCKWISE, COUNTER, DIRS, OPPOSITE, Game, move_facts, ray

LEGEND = ("H = snake head, o = snake body, T = snake tail, F = food, . = empty. "
          "Row 0 is the top row, column 0 is the leftmost column. Leaving the grid hits a wall.")
DEFAULT_STRATEGY = "Stay alive and eat food."


class Formulation:
    name = title = origin = blurb = ""
    independent = True           # one scoring row per question (see engine.DeciderEngine.ask)

    def request(self, g: Game, strategy: str = ""):
        """-> (request dict or None, move chosen by code or None, note)"""
        raise NotImplementedError

    def pick(self, g: Game, answers: dict, ctx):
        """answers from the model -> (move, how it was chosen)"""
        a = answers["move"]
        return self.to_dir(g, a["choice"]), "model's top choice"

    def to_dir(self, g, option):
        return option


# ---- 1. raw board -----------------------------------------------------------------------------------------------
class Grid(Formulation):
    name, title = "grid", "Raw board"
    origin = "iammusham/jev-snake, coderhh/jev-snake"
    blurb = ("The model gets the board as text and coordinates, and has to work out walls, body and food itself. "
             "Nothing is filtered except the reversal; a fatal pick kills the snake.")

    def request(self, g, strategy=""):
        head = g.snake[0]
        state = {
            "board": g.board(),
            "legend": LEGEND,
            "head": {"row": head[0], "col": head[1]},
            "food": {"row": g.food[0], "col": g.food[1]} if g.food else None,
            "heading": g.heading,
            "snake_length": len(g.snake),
            "grid_size": g.size,
        }
        crit = {"up": "move one row up (row - 1)", "down": "move one row down (row + 1)",
                "left": "move one column left (col - 1)", "right": "move one column right (col + 1)"}
        crit.pop(OPPOSITE[g.heading])
        q = {"type": "choice",
             "instructions": "You are playing Snake. Choose the direction the head moves next. Do not hit a wall or "
                             "the snake's own body, and move toward the food.",
             "criteria": crit}
        return {"state": state, "questions": {"move": q}}, None, ""


# ---- 2. relative, in words --------------------------------------------------------------------------------------
def _cells(n):
    return f"{n} cell" if n == 1 else f"{n} cells"


class Relative(Formulation):
    name, title = "relative", "Relative, in words"
    origin = "nadeem4/jev-demo"
    blurb = ("No board. Code describes the food and what lies left, ahead and right in short phrases; the model "
             "picks TURN_LEFT / STRAIGHT / TURN_RIGHT. A fatal pick still kills the snake.")
    ACT = {"TURN_LEFT": COUNTER, "STRAIGHT": None, "TURN_RIGHT": CLOCKWISE}

    def _look(self, g, d):
        free, what = ray(g, d)
        if free == 0:
            return f"BLOCKED: {'wall' if what == 'the wall' else what} right next to you"
        return f"clear for {_cells(free)}, then {what}"

    def _food(self, g):
        (hr, hc), (fr, fc) = g.snake[0], g.food
        ar, ac = DIRS[g.heading]
        rr, rc = DIRS[CLOCKWISE[g.heading]]
        ahead, right = (fr - hr) * ar + (fc - hc) * ac, (fr - hr) * rr + (fc - hc) * rc
        along = f"{_cells(abs(ahead))} {'ahead' if ahead > 0 else 'behind'}" if ahead else ""
        side = f"{_cells(abs(right))} to your {'right' if right > 0 else 'left'}" if right else ""
        return " and ".join(x for x in (along, side) if x)

    def request(self, g, strategy=""):
        state = {
            "food": self._food(g),
            "if_you_turn_left": self._look(g, COUNTER[g.heading]),
            "if_you_go_straight": self._look(g, g.heading),
            "if_you_turn_right": self._look(g, CLOCKWISE[g.heading]),
            "your_length": f"{len(g.snake)} cells ({g.score} food eaten)",
        }
        q = {"type": "choice",
             "instructions": "You are the snake. Reach the food without hitting a wall or your own body. Pick the next move.",
             "criteria": {"TURN_LEFT": "Turn left, relative to the direction you are moving.",
                          "STRAIGHT": "Keep going straight.",
                          "TURN_RIGHT": "Turn right, relative to the direction you are moving."}}
        return {"state": state, "questions": {"move": q}}, None, ""

    def to_dir(self, g, option):
        m = self.ACT[option]
        return g.heading if m is None else m[g.heading]


# ---- 3. facts in the options ------------------------------------------------------------------------------------
def describe(f):
    t = f["target"]
    parts = [f"{f['turn']}, head moves to row {t[0]} col {t[1]}",
             "EATS THE FOOD now" if f["eats"] else f"food is {f['food_distance']} steps away after this move",
             f"{f['reachable']} of {f['free_total']} empty cells stay reachable"]
    if f["dead_end"]:
        parts.append("DEAD END: less room than the snake is long and no way to follow the tail out")
    elif f["can_reach_tail"]:
        parts.append("can still follow its own tail out")
    return "; ".join(parts)


RULES = ("You are playing the game Snake. Choose the direction the snake's head moves on the next step. "
         "Every listed direction is safe for this single step; the facts next to each direction were computed by "
         "code and are exact. A move marked DEAD END almost always loses the game a few steps later. The snake grows "
         "by one when it eats the food, and the game ends when the head hits a wall or its own body.")


class Facts(Formulation):
    name, title = "facts", "Facts in the options"
    origin = "sorrycc/typesafe-snake"
    blurb = ("Code lists only the moves that survive this step and writes exact facts into each option: food "
             "distance, reachable cells (flood fill), dead ends. The model weighs the facts; it cannot pick a fatal move.")

    def request(self, g, strategy=""):
        legal = g.legal()
        if len(legal) == 0:
            return None, g.heading, "no safe move: code goes straight"
        if len(legal) == 1:
            return None, legal[0], "only one safe move: code decides, no model call"
        facts = [move_facts(g, d) for d in legal]
        head = g.snake[0]
        state = {
            "board": g.board(),
            "legend": LEGEND,
            "head": {"row": head[0], "col": head[1]},
            "food": {"row": g.food[0], "col": g.food[1]} if g.food else None,
            "heading": g.heading,
            "snake_length": len(g.snake),
            "food_is_adjacent": any(f["eats"] for f in facts),
        }
        q = {"type": "choice",
             "instructions": f"{RULES} Player strategy: {strategy.strip() or DEFAULT_STRATEGY}",
             "criteria": {f["dir"]: describe(f) for f in facts}}
        return {"state": state, "questions": {"move": q}}, None, {f["dir"]: f for f in facts}


# ---- 4. judged options: code states each option's consequence in words ------------------------------------------
def judge(f, cur, best_room, plain=False):
    """One plain-language verdict per move. No numbers to compare across options: a 2B model reads a label
    reliably, but it can't tell which of '6 steps' / '4 steps' is smaller (probe: 99% vs 67% good picks).
    plain=True words the eating move as 'moves closer to the food; keeps the most room': CLM 8B gives any
    option that mentions eating ~0.3% and would never eat (with this wording: 97%)."""
    if f["eats"] and plain:
        return "moves closer to the food; keeps the most room"
    if f["eats"]:
        parts = ["eats the food"]
    elif f["food_distance"] < cur:
        parts = ["moves closer to the food"]
    else:
        parts = ["moves away from the food"]
    if f["dead_end"]:
        parts.append("DEAD END: the snake gets trapped")
    elif f["reachable"] >= best_room:
        parts.append("keeps the most room")
    elif f["reachable"] >= 0.8 * best_room:
        parts.append("keeps almost as much room")
    else:
        parts.append(f"leaves much less room ({f['reachable']} of {best_room} cells)")
    return "; ".join(parts)


class Judged(Formulation):
    name, title = "judged", "Judged options"
    plain = False
    origin = "sorrycc's facts, rewritten here for small models"
    blurb = ("Code computes the same facts but writes each option as a verdict in words (closer / away from the "
             "food, keeps the most room, DEAD END). The model weighs verdicts instead of comparing numbers.")

    def request(self, g, strategy=""):
        legal = g.legal()
        if len(legal) == 0:
            return None, g.heading, "no safe move: code goes straight"
        if len(legal) == 1:
            return None, legal[0], "only one safe move: code decides, no model call"
        facts = {d: move_facts(g, d) for d in legal}
        (hr, hc), (fr, fc) = g.snake[0], g.food
        cur = abs(hr - fr) + abs(hc - fc)
        best_room = max((f["reachable"] for f in facts.values() if not f["dead_end"]), default=0)
        # No heading, no board, no food coordinates: with them in the context Decider went straight on 43% of
        # states where straight was the wrong move; with the verdicts alone, 0% (snake/probe notes in docs/5-snake.md).
        state = "Choose the best move for the snake."
        q = {"type": "choice",
             "instructions": "Snake game: pick the next move. Every listed move is safe for this step. Never take a "
                             "DEAD END. Prefer a move that eats the food or moves closer to it, unless it leaves much "
                             f"less room than another move. Player strategy: {strategy.strip() or DEFAULT_STRATEGY}",
             "criteria": {d: judge(f, cur, best_room, self.plain) for d, f in facts.items()}}
        return {"state": state, "questions": {"move": q}}, None, facts


class JudgedPlain(Judged):
    name, title = "judged-plain", "Judged, plain wording"
    origin = "judged options, reworded for CLM 8B"
    blurb = ("Judged options, but the move that eats the food is described as 'moves closer to the food'. "
             "CLM (a bi-encoder) scores options by similarity and almost never picks one that says 'eats'.")
    plain = True


# ---- 5. several typed questions, composed by code ---------------------------------------------------------------
THRESHOLDS = {"danger_score": 1.5, "survival_noul": 0.7, "move_confidence": 0.55}


class Composed(Judged):
    name, title = "composed", "Composed questions"
    origin = "ximing/jev-snake-game"
    blurb = ("Judged options plus two more typed questions in one request: how threatened the snake is "
             "(score 0-2) and whether to ignore food to survive (noul). Code combines them with fixed thresholds.")
    independent = False          # all three questions share one row: one forward pass instead of five on MPS

    def request(self, g, strategy=""):
        req, move, ctx = super().request(g, strategy)
        if req is None:
            return req, move, ctx
        req["questions"]["danger"] = {
            "type": "score",
            "instructions": "How threatened is the snake right now? Judge remaining space and how many safe moves "
                            "remain, not how close the food is.",
            "criteria": ["Open: ample reachable space and at least two safe moves with room to turn.",
                         "Pressured: limited space, close to walls or body, or the food may be a trap.",
                         "Nearly trapped: reachable space is very small or most moves lead into a dead end."]}
        req["questions"]["survival"] = {
            "type": "noul",
            "instructions": "Should the snake ignore the food this step and move only to stay alive?",
            "criteria": {"true": "Survival should outrank food this step: a food-seeking move would shrink the "
                                 "reachable space badly.",
                         "false": "A safe move can also make progress toward the food."}}
        return req, None, ctx

    def pick(self, g, answers, facts):
        mv, danger, surv = answers["move"], answers["danger"]["score"], answers["survival"]["noul"]
        open_moves = [d for d in facts if not facts[d]["dead_end"]] or list(facts)
        if danger >= THRESHOLDS["danger_score"] or surv >= THRESHOLDS["survival_noul"]:
            best = max(open_moves, key=lambda d: (facts[d]["reachable"], mv["probabilities"][d]))
            return best, f"survival mode (danger {danger:.2f}, survive P={surv:.2f}): most reachable space"
        if mv["confidence"] >= THRESHOLDS["move_confidence"]:
            return mv["choice"], f"model's choice (confidence {mv['confidence']:.2f} ≥ {THRESHOLDS['move_confidence']})"
        best = min(open_moves, key=lambda d: (facts[d]["food_distance"] or 0, -facts[d]["reachable"]))
        return best, f"low confidence ({mv['confidence']:.2f}): code falls back to closest-to-food open move"


FORMULATIONS = {f.name: f for f in (Grid(), Relative(), Facts(), Judged(), JudgedPlain(), Composed())}
