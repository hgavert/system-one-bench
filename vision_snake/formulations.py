"""Three ways to ask for a Snake move from a picture, from "the model does everything" to "code does the logic".

Every request carries the picture(s) in `images` and says only what the colours mean; no positions, no directions,
no facts computed by code (that is what the text test's judged options do, docs/5-snake.md). All three use absolute
directions, worded as places on the board ("towards the top of the board"), since that is what a picture shows.

  see-4      picture + all four directions. Code knows nothing; a reversal is ignored by the game (keeps going).
             hatch's "Eyes against state" request.
  see-legal  picture + only the moves that don't end the game now (code filters walls, body and the reversal, as
             coderhh/sorrycc do in text). One legal move: code moves, no model call.
  see-ask    picture + two yes/no questions per direction in one request ("is the cell towards the top free?",
             "would that bring the head closer to the food?"); code takes the free direction most likely to get
             closer. The model only perceives; code doesn't look at the board at all.
"""
from snake.game import DIRS, Game

from .render import description, images

TOWARDS = {"up": "the top", "down": "the bottom", "left": "the left side", "right": "the right side"}
MOVE_TEXT = {d: f"move the head one cell towards {t} of the board" for d, t in TOWARDS.items()}
INSTRUCTIONS = ("Snake game: pick the next move of the snake's head. Moving into the wall or the snake's body ends "
                "the game. Prefer a move that reaches the food or brings the head closer to it.")


class VisionFormulation:
    name = title = blurb = ""

    def __init__(self, style="blocks", frames=1):
        self.style, self.frames = style, frames

    def _base(self, g: Game, prev: Game | None):
        return {"state": description(self.style, self.frames), "images": images(g, self.style, self.frames, prev)}

    def request(self, g: Game, prev: Game | None = None):
        """-> (request or None, move chosen by code or None, context for pick)"""
        raise NotImplementedError

    def pick(self, g: Game, answers: dict, ctx):
        """-> (move, how it was chosen, {direction: probability the model gives it} for the probe)"""
        m = answers["move"]
        return m["choice"], "model's top choice", m["probabilities"]


class See4(VisionFormulation):
    name, title = "see-4", "Picture, four directions"
    blurb = "The picture and all four directions; code knows nothing (hatch's request)."

    def request(self, g, prev=None):
        q = {"type": "choice", "instructions": INSTRUCTIONS, "criteria": dict(MOVE_TEXT)}
        return {**self._base(g, prev), "questions": {"move": q}}, None, None


class SeeLegal(VisionFormulation):
    name, title = "see-legal", "Picture, legal moves only"
    blurb = "The picture and only the moves that don't end the game now; code removes the fatal ones."

    def request(self, g, prev=None):
        legal = g.legal()
        if len(legal) <= 1:
            return None, legal[0] if legal else g.heading, "one or no safe move: code decides, no model call"
        q = {"type": "choice", "instructions": INSTRUCTIONS.replace("Moving into", "Every listed move is safe for "
                                                                    "this step; moving into"),
             "criteria": {d: MOVE_TEXT[d] for d in legal}}
        return {**self._base(g, prev), "questions": {"move": q}}, None, None


class SeeAsk(VisionFormulation):
    name, title = "see-ask", "Picture, yes/no per direction"
    blurb = ("Two yes/no questions per direction in one request (free? closer to the food?); code takes the free "
             "direction most likely to get closer. The model perceives, code decides, nobody else reads the board.")

    def request(self, g, prev=None):
        qs = {}
        for d, t in TOWARDS.items():
            qs[f"free_{d}"] = {"type": "noul", "instructions": f"Is the cell next to the snake's head, towards {t} "
                                                                f"of the board, free: neither the wall nor part of "
                                                                f"the snake?"}
            qs[f"closer_{d}"] = {"type": "noul", "instructions": f"Would moving the snake's head one cell towards "
                                                                  f"{t} of the board bring it closer to the food?"}
        return {**self._base(g, prev), "questions": qs}, None, None

    def pick(self, g, answers, ctx):
        free = {d: answers[f"free_{d}"]["noul"] for d in DIRS}
        closer = {d: answers[f"closer_{d}"]["noul"] for d in DIRS}
        cands = [d for d in DIRS if free[d] >= 0.5] or [max(DIRS, key=free.get)]
        move = max(cands, key=lambda d: (closer[d], free[d]))
        score = {d: free[d] * (0.5 + closer[d]) for d in DIRS}        # a soft version, for the probe's mass
        z = sum(score.values()) or 1
        return move, f"free {free[move]:.2f}, closer {closer[move]:.2f}", {d: v / z for d, v in score.items()}


FORMULATIONS = {f.name: f for f in (See4, SeeLegal, SeeAsk)}
