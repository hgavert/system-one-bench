# 7 · Vision Snake: playing from a picture of the board

*Started 9 October 2026.* Test 4. The same Snake game as [doc 5](5-snake.md), but the model gets a **picture of the
board** instead of text. Of the models in this repo only Clef-flash takes images (Qwen3.5-9B with its vision encoder
kept), so this is a separate benchmark, built so other vision models can be added later. Clef-flash only for now; the
27B Clef doesn't fit a 32 GB Mac.

The results in report form: [vision-snake-report.md](vision-snake-report.md).

Files: [`vision_snake/render.py`](../vision_snake/render.py) (the picture),
[`vision_snake/perception.py`](../vision_snake/perception.py) (questions with known answers),
[`14_vision_snake_probe.py`](../14_vision_snake_probe.py) (the probe), [`vision_snake/formulations.py`](../vision_snake/formulations.py)
(the move requests), [`15_vision_snake.py`](../15_vision_snake.py) (single moves and games).

## 7.1 What others found

No one has published games played from images with Clef. Cloudflare's own vision examples are classification
(website screenshots, receipts, webcam checks); the one Clef game demo, prokube's Tetris (open issue, no code yet),
has the model pick among legal placements code computes.

The closest prior work is [hatch's "Eyes against state"](https://github.com/nikhil-vytla/hatch/pull/187) (3 Oct 2026):
Qwen3-VL-4B and 8B (4-bit, the encoder family Clef-flash's comes from) played Snake from 320×320 screenshots, one
forward pass per move, scoring the answer letters for up / right / down / left. Over 23 seeds both lost every game,
median 8–9 moves, against 21 of 23 survived by greedy code. Yet the 8B said correctly where the food was relative to
the head 93–94% of the time: **seeing was fine, deciding wasn't**; it answered only "right" or "up". In the wider
literature, BALROG found most vision-language models play worse given an image than a text description, and
"Vision language models are blind" found they can't count grid rows or columns and confuse touching shapes.

So before any games: find out what the model can see.

## 7.2 Drawing the board

Clef-flash's processor (Qwen3-VL's) cuts 16-px patches and merges 2×2 into one token, so **a 32-px cell is exactly
one image token**. The 12×12 board plus a one-cell wall ring is 14×14 cells, 448×448 px, 196 image tokens (checked
with the processor; images under 256×256 are upscaled, which would break the alignment). Images go into the request
as PNG data URIs in `images`; Clef's processor decodes them, so [`adapters/clef_server.py`](../adapters/clef_server.py)
needed no change. Clef puts the image first, right after `STATE:`, then the state text, then the questions.

Four styles, to see whether drawing choices matter (the first two first; the blocks styles were drawn after their
results):

* **clear**: dark wall ring, the body drawn as one joined chain (so its order is visible), a darker head with two
  white eyes facing the heading (a still frame doesn't otherwise show which way the snake moves)
* **plain**: hatch's look: no wall ring (the image edge is the wall), separate squares, a plain black head
* **blocks**: every obstacle looks the same: wall cells and body cells are separate dark squares on white; the head
  is a blue arrow pointing the way it moves; the state says "dark squares are obstacles"
* **blocks-nowall**: the same without the wall ring

Any style can also be sent as **two frames** (`--frames 2`): the board one step earlier, then now. Games keep the
real previous board; for the probe's snapshots `render.previous()` rebuilds it (head back onto the neck, the tail one
cell longer).

The state text only says what the colours mean, never positions or directions (direction words in the state pulled
the small text models towards straight, [doc 5 §5.4](5-snake.md)).

## 7.3 Perception probe

The 150 states of the text probe (`snake/probe_states.py`, seed 0), seven questions each, all answerable from the
game state:

| Question | Type | Asks |
|---|---|---|
| `food_above`, `food_right` | noul | is the food higher up / further right than the head (skipped when on the same row / column) |
| `heading` | choice | which way is the head moving: towards the top / bottom / left / right of the board |
| `free_up`, `free_down`, `free_left`, `free_right` | noul | is the cell next to the head neither wall nor snake |

`joint` asks all seven in one request (one picture, one pass: how a game would ask); `separate` one per request. The
same questions on the text board (`--modality text`) are the control: does the picture tell the model more or less
than the text grid? Balanced accuracy is reported because most cells next to the head are free.

### Results (Clef-flash, 9 October 2026)

Balanced accuracy per question (chance 0.50 for the yes/no questions, 0.25 for heading). All seven questions in one
request unless marked:

| Question | clear | clear, one per request | plain | blocks | blocks-nowall | blocks, 2 frames | Text board |
|---|--:|--:|--:|--:|--:|--:|--:|
| `food_above` | 0.97 | 0.98 | 0.97 | **0.98** | 0.96 | 0.95 | **0.98** |
| `food_right` | 0.95 | 0.95 | 0.94 | **0.96** | 0.94 | **0.96** | 0.78 |
| `heading` | 0.37 | 0.44 | 0.26 | 0.53 | 0.53 | **0.70** | 0.21 |
| `free_up` | 0.65 | 0.60 | **0.73** | 0.72 | 0.72 | 0.66 | 0.53 |
| `free_down` | 0.77 | 0.73 | 0.79 | 0.79 | 0.76 | 0.70 | **0.82** |
| `free_left` | 0.80 | 0.76 | 0.82 | 0.81 | **0.83** | 0.80 | 0.81 |
| `free_right` | 0.69 | 0.66 | 0.74 | 0.79 | **0.81** | 0.77 | 0.49 |
| Blocked cells seen as blocked | 0.57 | 0.48 | 0.70 | **0.81** | **0.81** | **0.81** | 0.57 |
| Request, p50 | 2.2 s | 1.0 s (×7) | 2.2 s | 2.3 s | 2.2 s | 2.8 s | 1.9 s |

Rows: `results/vision_snake/probe-clef-flash-<condition>.jsonl`; summary `probe-clef-flash.json`.

1. **Clef-flash sees where the food is.** 0.94–0.98 on both axes, in every style. That replicates hatch's Qwen3-VL-8B
   (93–94%).
2. **The picture beats the text board** for left/right: `food_right` 0.94–0.96 against 0.78, and the text board is at
   chance on `free_up` and `free_right`. In text, left/right means counting characters along a row.
3. **Heading needs to be drawn, and motion helps most.** 0.26 with the plain head (chance: the picture doesn't show
   it), 0.37 with eyes, 0.53 with an arrow, 0.70 with the arrow and the previous frame. With eyes it said "right" for
   half the states (74 of 150, truth 38), the same pull towards one direction hatch saw.
4. **Blocked cells next to the head are the weak spot, and drawing fixes part of it.** With the joined green body it
   saw 57% of the 187 blocked neighbour cells, with hatch's separate squares 70%, with all obstacles as the same dark
   squares 81%. It still calls too many cells free, so about one blocked cell in five is missed. The wall ring
   makes no difference (blocks vs blocks-nowall).
5. **The second frame trades free cells for heading.** Heading +0.17, free cells −0.01 to −0.09, +0.6 s.
6. **Asking jointly costs little.** Separate questions help heading (+0.07) and hurt free cells; one joint request
   (2.2 s) is cheaper than seven separate ones (7 × 1.0 s).

So far it matches the text tests and hatch: the model reads coarse relations (food up/down/left/right) well, and the
fine local geometry a move depends on less well, though how the board is drawn moves it from 57% to 81% on blocked
cells. **blocks** is the style for the move tests.

## 7.4 Asking for a move

Three requests ([`vision_snake/formulations.py`](../vision_snake/formulations.py)), all on the **blocks** picture. The
state only says what the colours mean; options are absolute directions worded as places on the board ("move the head
one cell towards the top of the board"). No positions, no facts computed by code.

| Request | The model gets | Code does |
|---|---|---|
| **see-4** | the picture and all four directions (hatch's request) | nothing; the game ignores a reversal and keeps going |
| **see-legal** | the picture and only the moves that don't end the game now | removes fatal moves (as coderhh/sorrycc do in text); moves alone when one is left |
| **see-ask** | two yes/no questions per direction in one request: is that cell free? would it bring the head closer to the food? | takes the free direction most likely to get closer; never looks at the board |

[`15_vision_snake.py`](../15_vision_snake.py) `probe` asks for single moves on the text probe's states (good = not a
dead end, and as close to the food as any non-dead-end move); `games` plays the text test's seeds and rules (12×12,
10 seeds, 500-step cap, starved after 144 steps without food), so the games line up with `results/snake/games`.
Clef-flash's answers are deterministic: seeds replayed after a restart gave identical games.

### Single moves (good pick, all 150 states / 100 hard states where straight is legal but wrong)

| Request | One frame | Two frames | Fatal pick (all) | Straight on hard (1 / 2 frames) | Per move |
|---|--:|--:|--:|--:|--:|
| see-4 | 0.83 / 0.74 | 0.83 / 0.66 | 0.06 | 0.26 / 0.34 | 1.1 s |
| see-legal | **0.98 / 0.98** | 0.92 / 0.78 | 0 (filtered) | 0.02 / 0.21 | 1.1 s |
| see-ask | 0.82 / 0.73 | 0.81 / 0.59 | 0.02 | 0.23 / 0.39 | 2.6 s |
| *text board, Clef-flash (grid, [doc 5](5-snake.md))* | *0.87 / 0.85* | | | *0.10* | *0.8 s* |
| *text verdicts, Clef-flash (judged)* | *0.99 / 1.00* | | | *0.00* | *0.6 s* |

**The second frame hurts every request.** It made heading easier to name (0.53 → 0.70 in the perception probe), but
as a move it pulls towards straight: on the hard states straight goes up by 8–16 points for all three. It's the same
pull as direction words in the text state (doc 5 §5.4). Games were played with one frame.

### Games (blocks, one frame, 10 seeds)

| Player | Food per game (mean / best) | Steps (median) | Died | Starved | Per move |
|---|--:|--:|--:|--:|--:|
| **Clef-flash, see-legal** | **25.2** / 39 | 260 | 9 (all trapped) | 0 | 1.1 s |
| Clef-flash, see-ask | 1.2 / 2 | 44 | 6 | 4 | 2.6 s |
| Clef-flash, see-4 | 1.1 / 5 | 8 | 10 | 0 | 1.1 s |
| *Clef-flash, text board (grid)* | *6.5 / 15* | | *10* | | |
| *Clef-flash, text verdicts (judged)* | *39.3 / 45* | *500* | *0* | | |
| *code: greedy (closest to food, never fatal)* | *21.0 / 32* | | *10* | | |
| *code: greedy + dead-end check* | *41.1 / 44* | | *2* | | |
| *hatch: Qwen3-VL-4B / 8B from a screenshot* | *1.1 / 0.0* | *9 / 8* | *23 of 23* | | |

Games: `results/vision_snake/games/clef-flash-<request>-blocks.json`.

1. **With the fatal moves filtered out, Clef-flash plays from the picture better than greedy code** (25.2 against
   21.0 food) and four times better than from the text board (6.5). 94% of its moves get closer to the food. Nine of
   ten games end trapped: nothing in the picture or the options warns of a dead end, which is what the text verdicts
   add (39.3).
2. **Alone, it dies as hatch's models did** (see-4: 1.1 food, median 8 steps, 10 of 10 into a wall). 8 of the 10
   deaths came from choosing the reversal next to a wall: the game ignores it and the snake goes straight on. 19% of
   its picks in games were reversals; in the probe they counted as "straight" and were rare.
3. **Splitting the move into yes/no questions fails in games** (see-ask: 1.2 food), though it matched see-4 on single
   moves. Its "closer to the food?" answers carry no signal in play: the move it took had P(closer) 0.50 on average and
   got closer only 56% of the time, so it wanders and starves (4 of 10). Asked as one choice among moves, the same
   judgement is right 94% of the time. As in the text tests, the model judges best when the options are compared
   with each other in one question.

## 7.5 What this says about vision for Clef-flash

* It **perceives** a well-drawn board: food direction 0.94–0.98, blocked neighbours 0.81, heading 0.53 (0.70 with
  motion). How the board is drawn matters a lot (blocked cells 0.57 → 0.81).
* It **chooses** well from the picture when the choice is one comparison ("which of these moves?") and code keeps it
  from the moves that kill it. That puts it above greedy code, with no positions or facts in text.
* It doesn't see far enough ahead to avoid dead ends, and it can't be trusted with the reversal or with yes/no
  questions about each direction.

Open next steps: dead-end avoidance from the picture (e.g. a second question "which move leaves the snake more
room?"), the 27B Clef, and other vision models through the same `/v1/systemone` + `images` contract.
