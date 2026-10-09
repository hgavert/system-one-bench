"""Draws a Snake board as the image a vision model sees. Pure Pillow, deterministic.

Laid out for Qwen-style vision encoders (Clef-flash's is Qwen3.5's): 16-px patches merged 2x2, so one image token
covers 32x32 px. At CELL = 32 every board cell is exactly one token, and the wall ring is one more cell on each side,
so a 12x12 board is a 14x14-cell, 448x448 image (196 image tokens). Images under 256x256 get upscaled by the
processor, which would break the alignment, so keep CELL at 32.

Styles (choose with `style=`), so the probe can tell which drawing choices matter:
  clear         wall as a solid dark ring, body segments joined in order, head with eyes looking where it is going
  plain         hatch's "Eyes against state" look: no wall ring, separate squares, a plain black head (no heading)
  blocks        every obstacle the same: wall cells and body cells are separate dark squares; the head is a blue
                arrow pointing where it is going
  blocks-nowall the same without the wall ring (the image edge is the wall)

`previous(g)` rebuilds the board one step earlier, for requests that show two frames (the motion shows heading).
"""
import base64
import io
from dataclasses import dataclass

from PIL import Image, ImageDraw

from snake.game import DIRS, Game, step_point

CELL = 32


@dataclass(frozen=True)
class Style:
    walls: str           # "" no ring | "solid" one dark ring | "blocks" a dark square per wall cell, like the body
    joined: bool         # bridge consecutive body segments, so the body reads as one ordered chain
    head_shape: str      # "square" | "eyes" (square with eyes towards the heading) | "arrow" (triangle, no square)
    floor: tuple = (245, 240, 228)
    grid: tuple = (222, 214, 198)
    wall: tuple = (70, 70, 78)
    body: tuple = (46, 160, 90)
    head: tuple = (20, 90, 50)
    food: tuple = (225, 40, 40)
    eye: tuple = (255, 255, 255)
    inset: int = 4


_BLOCKS = dict(joined=False, head_shape="arrow", floor=(255, 255, 255), grid=(225, 225, 225), wall=(45, 45, 55),
               body=(45, 45, 55), head=(30, 110, 235), food=(225, 30, 30), inset=2)
STYLES = {
    "clear": Style(walls="solid", joined=True, head_shape="eyes"),
    "plain": Style(walls="", joined=False, head_shape="square", floor=(255, 244, 224), grid=(233, 220, 196),
                   body=(47, 158, 110), head=(23, 20, 15), food=(240, 83, 45), inset=2),
    "blocks": Style(walls="blocks", **_BLOCKS),
    "blocks-nowall": Style(walls="", **_BLOCKS),
}

DESCRIPTIONS = {          # what the request's state says the picture shows; no positions, no directions
    "clear": "A Snake game board. The dark grey border is the wall. The green chain is the snake; its darker head "
             "has white eyes facing the way it is moving. The red dot is the food.",
    "plain": "A Snake game board. The black square is the snake's head, the green squares are its body, "
             "and the red dot is the food. The edge of the image is the wall.",
    "blocks": "A Snake game board. Dark squares are obstacles: the wall around the board and the snake's body. "
              "The blue arrow is the snake's head, pointing the way it is moving. The red dot is the food. "
              "White cells are free.",
    "blocks-nowall": "A Snake game board. Dark squares are the snake's body; the edge of the image is the wall. "
                     "The blue arrow is the snake's head, pointing the way it is moving. The red dot is the food. "
                     "White cells are free.",
}
TWO_FRAMES = " Two pictures: the first is the board one step earlier, the second is the board now."


def render(g: Game, style="clear") -> Image.Image:
    s = STYLES[style]
    off = 1 if s.walls else 0                       # board cell (r, c) sits at image cell (r + off, c + off)
    side = (g.size + 2 * off) * CELL
    im = Image.new("RGB", (side, side), s.wall if s.walls == "solid" else s.floor)
    d = ImageDraw.Draw(im)

    def box(r, c, inset=0):
        x, y = (c + off) * CELL, (r + off) * CELL
        return [x + inset, y + inset, x + CELL - 1 - inset, y + CELL - 1 - inset]

    for r in range(-off, g.size + off):             # floor with a faint 1-px grid on each cell's top/left edge
        for c in range(-off, g.size + off):
            if s.walls == "solid" and not g.inside((r, c)):
                continue
            x0, y0, x1, y1 = box(r, c)
            d.rectangle([x0, y0, x1, y1], fill=s.grid)
            d.rectangle([x0 + 1, y0 + 1, x1, y1], fill=s.floor)
            if s.walls == "blocks" and not g.inside((r, c)):
                d.rectangle(box(r, c, s.inset), fill=s.wall)

    if g.food:
        x0, y0, x1, y1 = box(*g.food, inset=5)
        d.ellipse([x0, y0, x1, y1], fill=s.food)

    for (r, c) in g.snake[1:]:
        d.rectangle(box(r, c, s.inset), fill=s.body)
    if s.joined:                                    # bridge each pair of consecutive segments
        for a, b in zip(g.snake, g.snake[1:]):
            ax0, ay0, ax1, ay1 = box(*a, s.inset)
            bx0, by0, bx1, by1 = box(*b, s.inset)
            d.rectangle([min(ax0, bx0), min(ay0, by0), max(ax1, bx1), max(ay1, by1)], fill=s.body)
    head = box(*g.snake[0], s.inset)
    if s.head_shape == "arrow":
        d.polygon(_arrow(head, g.heading), fill=s.head)
    else:
        d.rectangle(head, fill=s.head)
    if s.head_shape == "eyes":
        _eyes(d, head, g.heading, s.eye)
    return im


def _arrow(b, heading):
    """A triangle filling the head cell, its tip at the middle of the edge it is moving towards."""
    x0, y0, x1, y1 = b
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return {"up": [(cx, y0), (x1, y1), (x0, y1)], "down": [(cx, y1), (x0, y0), (x1, y0)],
            "left": [(x0, cy), (x1, y0), (x1, y1)], "right": [(x1, cy), (x0, y1), (x0, y0)]}[heading]


def _eyes(d, head_box, heading, color):
    """Two 8-px eyes on the front half of the head, side by side across the direction of travel."""
    x0, y0, x1, y1 = head_box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dr, dc = DIRS[heading]
    fx, fy = cx + dc * 6, cy + dr * 6               # towards the front
    px, py = -dr, dc                                # perpendicular
    for k in (-1, 1):
        ex, ey = fx + px * k * 6, fy + py * k * 6
        d.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=color)


def previous(g: Game) -> Game:
    """The board one step earlier, rebuilt from a snapshot (games keep the real one). The head steps back onto the
    neck; the tail grows back one cell, continuing the tail's line where that cell is free. If the snake has just
    eaten, it was one shorter and the food was where the head is now (the old food is drawn there)."""
    import copy
    p = copy.copy(g)
    body = list(g.snake[1:])
    if g.since_food == 0 and g.steps > 0:
        p.food = g.snake[0]
    else:
        tail, before = g.snake[-1], g.snake[-2]
        line = (tail[0] - before[0], tail[1] - before[1])
        cands = [(tail[0] + line[0], tail[1] + line[1])] + [step_point(tail, k) for k in DIRS]
        grown = next((t for t in cands if g.inside(t) and t not in g.snake and t != g.food), None)
        if grown:
            body.append(grown)
    p.snake = body
    a, b = body[0], body[1]
    p.heading = next(k for k in DIRS if step_point(b, k) == a)
    return p


def png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def data_uri(im: Image.Image) -> str:
    """How an image goes into a /v1/systemone request's `images` list (Clef's processor decodes it)."""
    return "data:image/png;base64," + base64.b64encode(png_bytes(im)).decode()


def images(g: Game, style="clear", frames=1, prev: Game | None = None) -> list[str]:
    """The request's `images`: the board now, or (frames=2) the board one step earlier and now."""
    now = data_uri(render(g, style))
    if frames == 1:
        return [now]
    return [data_uri(render(prev or previous(g), style)), now]


def description(style="clear", frames=1) -> str:
    return DESCRIPTIONS[style] + (TWO_FRAMES if frames == 2 else "")
