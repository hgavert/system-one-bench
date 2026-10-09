"""Figures for docs/vision-snake-report.md, drawn from the saved games (no model needed: games replay exactly).

  uv run python docs/vision_snake_figures.py [--out docs]

  vision-snake-tokens.png    the board with the encoder's grid: 16-px patches, merged 2x2 into one token per cell
  vision-snake-request.png   one see-legal move: the picture, the text sent with it, the probabilities it returned
  vision-snake-reversal.png  how see-4 dies: the last frames before it picks the reversal next to the wall
  vision-snake-game.gif      a see-legal game (seed 1), every 2nd step
"""
import argparse
import json
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))     # repo root: snake/, vision_snake/

from PIL import Image, ImageDraw, ImageFont

from snake.game import OPPOSITE, Game
from vision_snake.formulations import FORMULATIONS
from vision_snake.render import CELL, render

GAMES = Path("results/vision_snake/games")
INK, MUTED, ACCENT, GOOD, BAD = (30, 30, 35), (110, 110, 120), (30, 110, 235), (40, 150, 80), (215, 50, 40)


def font(size, mono=False):
    for f in (["/System/Library/Fonts/Menlo.ttc"] if mono else []) + ["/System/Library/Fonts/Helvetica.ttc",
                                                                      "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def replay(name, seed):
    """-> [(Game before the move, decision)] for one saved game."""
    g = json.load(open(GAMES / f"clef-flash-{name}-blocks.json"))
    game = next(x for x in g["games"] if x["seed"] == seed)
    import copy
    state, out = Game(size=12, seed=seed), []
    for d in game["decisions"]:
        out.append((copy.deepcopy(state), d))
        state.apply(d["move"])
    return out, state


def tokens(out):
    g = replay("see-legal", 1)[0][40][0]
    im = render(g, "blocks").convert("RGBA")
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    for x in range(0, im.width + 1, 16):                       # 16-px patches, thin
        d.line([(x, 0), (x, im.height)], fill=(255, 140, 0, 90), width=1)
        d.line([(0, x), (im.width, x)], fill=(255, 140, 0, 90), width=1)
    for x in range(0, im.width + 1, CELL):                     # 32-px tokens (2x2 patches), thick
        d.line([(x, 0), (x, im.height)], fill=(255, 120, 0, 230), width=2)
        d.line([(0, x), (im.width, x)], fill=(255, 120, 0, 230), width=2)
    board = Image.alpha_composite(im, over).convert("RGB")
    W, H = board.width + 420, board.height + 20
    fig = Image.new("RGB", (W, H), "white")
    fig.paste(board, (10, 10))
    d = ImageDraw.Draw(fig)
    x = board.width + 40
    d.text((x, 20), "How the picture becomes tokens", fill=INK, font=font(24))
    lines = ["The vision encoder cuts the image into", "16 × 16 px patches (thin lines) and merges",
             "2 × 2 patches into one token (thick lines).", "", "We draw each board cell at 32 × 32 px,",
             "so every cell is exactly one token:", "", "12 × 12 board + wall ring = 14 × 14 cells", "= 448 × 448 px = 196 image tokens.",
             "", "A cell split across tokens, or an image", "under 256 px (which gets upscaled),", "would put two cells into one token."]
    for i, t in enumerate(lines):
        d.text((x, 70 + i * 26), t, fill=INK if t and not t.startswith("=") else MUTED, font=font(18))
    fig.save(out / "vision-snake-tokens.png", optimize=True)


def bar(d, x, y, w, p, color):
    d.rectangle([x, y, x + w, y + 16], fill=(235, 235, 240))
    d.rectangle([x, y, x + int(w * p), y + 16], fill=color)


def request_fig(out):
    frames = replay("see-legal", 1)[0]
    g, dec = next((g, d) for g, d in frames[40:] if d["source"] == "model" and len(d["probs"]) == 3)
    req, _, _ = FORMULATIONS["see-legal"]("blocks").request(g)
    q = req["questions"]["move"]
    board = render(g, "blocks")
    W, H = board.width + 700, board.height + 60
    fig = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(fig)
    d.text((10, 10), "1. images: the picture", fill=MUTED, font=font(18))
    fig.paste(board, (10, 44))
    x, y = board.width + 40, 10
    d.text((x, y), "2. state: what the colours mean (no positions, no directions)", fill=MUTED, font=font(18))
    y += 30
    for t in textwrap.wrap(req["state"], 62):
        d.text((x, y), t, fill=INK, font=font(17, mono=True)); y += 22
    y += 18
    d.text((x, y), "3. question: one choice, only the safe moves", fill=MUTED, font=font(18)); y += 30
    for t in textwrap.wrap(q["instructions"], 62):
        d.text((x, y), t, fill=INK, font=font(17, mono=True)); y += 22
    y += 18
    d.text((x, y), "4. what Clef-flash answered (one forward pass, ~1.1 s)", fill=MUTED, font=font(18)); y += 32
    for opt, text in q["criteria"].items():
        p = dec["probs"][opt]
        pick = opt == dec["move"]
        d.text((x, y), f"{opt:5s}", fill=ACCENT if pick else INK, font=font(17, mono=True))
        bar(d, x + 70, y + 2, 260, p, ACCENT if pick else (170, 170, 180))
        d.text((x + 345, y), f"{p:.2f}" + ("  picked" if pick else ""), fill=ACCENT if pick else INK, font=font(17))
        d.text((x + 70, y + 22), text, fill=MUTED, font=font(14)); y += 52
    removed = [k for k in ("up", "down", "left", "right") if k not in q["criteria"]]
    d.text((x, y + 4), f"Not offered (code removed them as deadly): {', '.join(removed)}", fill=BAD, font=font(16))
    fig.save(out / "vision-snake-request.png", optimize=True)


def reversal(out):
    frames, end = replay("see-4", 1)
    last = frames[-4:]
    tiles = []
    for g, dec in last:
        im = render(g, "blocks")
        rev = dec["move"] == OPPOSITE[g.heading]
        cap = Image.new("RGB", (im.width, im.height + 92), "white")
        cap.paste(im, (0, 0))
        d = ImageDraw.Draw(cap)
        d.text((8, im.height + 8), f"step {dec['step']}: heading {g.heading}", fill=MUTED, font=font(18))
        d.text((8, im.height + 34), f"model picks {dec['move']} ({dec['probs'][dec['move']]:.2f})",
               fill=BAD if rev else INK, font=font(20))
        if rev:
            d.text((8, im.height + 62), "= reverse: game keeps going " + g.heading, fill=BAD, font=font(16))
        tiles.append(cap.resize((cap.width * 3 // 4, cap.height * 3 // 4), Image.LANCZOS))
    W = sum(t.width for t in tiles) + 16 * (len(tiles) - 1)
    fig = Image.new("RGB", (W, tiles[0].height + 76), "white")
    d = ImageDraw.Draw(fig)
    d.text((0, 8), f"see-4, seed 1: how it dies ({end.cause} after {end.steps} steps, {end.score} food)",
           fill=INK, font=font(22))
    d.text((0, 38), "The food is behind the head (up and to the left). The model picks left, towards the food, which is "
                    "backwards: the game can't reverse, so the snake keeps going right into the wall.", fill=MUTED, font=font(17))
    x = 0
    for t in tiles:
        fig.paste(t, (x, 76)); x += t.width + 16
    fig.save(out / "vision-snake-reversal.png", optimize=True)


def game_gif(out, every=2, limit=260):
    frames, end = replay("see-legal", 1)
    imgs = []
    for g, dec in frames[:limit:every]:
        im = render(g, "blocks").resize((336, 336), Image.NEAREST)
        cap = Image.new("RGB", (336, 372), "white")
        cap.paste(im, (0, 0))
        ImageDraw.Draw(cap).text((6, 342), f"step {g.steps:3d}   food {g.score:2d}   next: {dec['move']}",
                                 fill=INK, font=font(16))
        imgs.append(cap.convert("P", palette=Image.ADAPTIVE, colors=16))
    imgs[0].save(out / "vision-snake-game.gif", save_all=True, append_images=imgs[1:], duration=120, loop=0,
                 optimize=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    tokens(out)
    request_fig(out)
    reversal(out)
    game_gif(out)
    for p in sorted(out.glob("vision-snake-*")):
        print(p, p.stat().st_size // 1024, "KB")
