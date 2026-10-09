"""Perception questions: things about the picture whose answer code knows from the game state.

Asked before any game, to separate "can't see" from "can't decide" (hatch's Eyes against state: Qwen3-VL-8B saw
where the food was 93-94% of the time, yet drove into a wall in every game). Every question is a plain Jev question,
so any /v1/systemone engine answers it; the picture goes in the request's `images`.

`truth(g)` returns the right option, or None when the question doesn't apply to this state (food on the head's row
for "above", say), and the state is skipped for that question.
"""
from dataclasses import dataclass
from typing import Callable

from snake.game import DIRS, Game, step_point

from .render import description, images

SIDE = {"up": "directly above", "down": "directly below", "left": "directly to the left of",
        "right": "directly to the right of"}
TOWARDS = {"up": "towards the top of the board", "down": "towards the bottom of the board",
           "left": "towards the left side of the board", "right": "towards the right side of the board"}


@dataclass(frozen=True)
class Question:
    id: str
    question: dict                               # the Jev question, as sent
    truth: Callable[[Game], str | None]


def _noul(text):
    return {"type": "noul", "instructions": text}


def _cmp(a, b):
    return None if a == b else ("true" if a < b else "false")


def _free(d):
    def truth(g):
        t = step_point(g.snake[0], d)
        return "true" if g.inside(t) and t not in g.snake else "false"
    return truth


QUESTIONS = [
    Question("food_above", _noul("Is the food higher up on the board than the snake's head?"),
             lambda g: _cmp(g.food[0], g.snake[0][0])),
    Question("food_right", _noul("Is the food further to the right on the board than the snake's head?"),
             lambda g: _cmp(g.snake[0][1], g.food[1])),
    Question("heading", {"type": "choice", "instructions": "Which way is the snake's head moving?",
                         "criteria": dict(TOWARDS)}, lambda g: g.heading),
    *[Question(f"free_{d}", _noul(f"Is the cell {SIDE[d]} the snake's head free, that is, neither the wall nor "
                                  f"part of the snake?"), _free(d)) for d in DIRS],
]

TEXT_STATE = ("A Snake game board as text, row by row from the top. H is the snake's head, o its body, T its tail, "
              "F the food, and . empty floor. Everything outside the grid is the wall.")


def request(g: Game, questions, modality="image", style="clear", frames=1):
    """One /v1/systemone request asking `questions` about this state, shown as a picture (or two: the step before
    and now) or as the text board."""
    body = {"questions": {q.id: q.question for q in questions}}
    if modality == "image":
        body["state"] = description(style, frames)
        body["images"] = images(g, style, frames)
    else:
        body["state"] = TEXT_STATE + "\n\n" + "\n".join(g.board())
    return body
