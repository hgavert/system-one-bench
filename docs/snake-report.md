# Asking for a Snake Move

> Generated from the same data as the interactive version, [`docs/snake-report/index.html`](snake-report/index.html), by `docs/snake-report/build.py`. Key code and details: [docs/5-snake.md](5-snake.md).

People posted Jev playing Snake. We read how six of those demos phrase each move, then asked the same questions of seven open System One models on a laptop, zero-shot, 10 games each. **The fast, straight-to-the-food videos rely on code for the geometry.** Asked to read the board themselves, every model is poor at it, and so is Jev. Given one verdict per option, five of the seven play well, but each one needs the wording to suit it.

## What we found

1. **The simple way fails, for Jev and for every open model.** The only published numbers of Jev playing (nadeem4's arena) are 1.8 food per game against 17.3 for a few lines of greedy code; it circled until it starved. On the raw board, five of the six models we tried it on died within about 9 steps in every game; with nadeem4's phrasing or sorrycc's facts they circled and starved. Only Kev 4B partly reads the board (13.1 food with nadeem4's phrasing), and it still dies every game.
2. **The demos that look good move the spatial work into code**: filtering out fatal moves, flood-fill facts, confidence gates, or a waypoint pathfinder that steers every tick while Jev only picks a target every 2.6 seconds. CLM's own game demo does the same.
3. **What works: one verdict per option, and nothing else in the state.** Code writes "moves closer to the food; keeps the most room" into each option. For five models the best such request picks a good single move 95–99% of the time (90–100% on the hard states below). Two things had broken them: numbers they would have to compare across options, and direction words in the state (`heading: up`) that pull them to go straight.
4. **The wording has to suit the model.** CLM and GLiNER 340M give any option that says "eats the food" almost no probability, so they circle next to the food. Worded as "moves closer to the food", CLM goes from 0 to 36.2 food per game and GLiNER from 2.7 to 26.3. For the others it makes little difference (Decider 2B −2.0, Kev 4B −4.2, Decider 4B +1.5).
5. **Better single moves don't mean longer games.** Decider 4B and Kev 4B are more decisive than Decider 2B and follow "closer to the food" almost literally, into tight spaces: they die in 9 and 10 of 10 games, Decider 2B in 2. With 36.9 food per game, the 2B is the best model that decides every move itself, close to the best code baseline (41.1).
6. **Speed varies 60-fold.** CLM answers in ~4 ms once its cache is warm (10 games in 16 s), GLiNER in 70–80 ms, Kev in ~110, Decider 2B in ~145 and Decider 4B in ~260. Adding ximing's extra questions roughly doubles the time, and on those rows code chooses up to two moves in three (below).

## Best result per model

Each model's best request among those where the model decides every move (so not "composed", where code steps in when the model is unsure). 10 games each, 12×12 board, 500-step cap.

| Model | Best request | Food / game | Best game | Died | Per move | Probe, hard states |
|---|---|--:|--:|--:|--:|--:|
| **Decider 2B** | Judged options | 36.9 | 46 | 2 of 10 | 145 ms | 100% |
| **CLM 8B** | Judged, plain wording | 36.2 | 44 | 5 of 10 | 4 ms | 100% |
| **Decider 4B** | Judged, plain wording | 30.8 | 43 | 9 of 10 | 260 ms | 100% |
| **Kev 4B** | Judged options | 29.5 | 41 | 10 of 10 | 108 ms | 100% |
| GLiNER 340M | Judged, plain wording | 26.3 | 37 | 5 of 10 | 70 ms | 90% |
| GLiNER 1B | Judged options | 15.3 | 25 | 4 of 10 | 82 ms | 72% |
| Laya | Facts in the options | 0.5 | 2 | 0 of 10 | 100 ms | 18% |
| *code only* | *greedy + dead-end check* | *41.1* | *44* | *2 of 10* | – | – |

## Who decides what, in each published demo

Every demo sends the same Jev request: a `state` plus one typed `choice` question per tick. What differs is how much has already been decided by code before the model sees the options. From model-reads-the-board to code-does-the-pathing:

| Demo | State sent | Options | Code decides |
|---|---|---|---|
| [iammusham](https://github.com/iammusham/jev-snake) | coordinates, body, walls, danger cells (JSON) | `UP` "Move one cell in negative y", ×4 | nothing |
| [nadeem4](https://github.com/nadeem4/jev-demo) | "food: 3 cells ahead and 2 to your right", "if_you_turn_left: clear for 4 cells, then the wall" | `TURN_LEFT` `STRAIGHT` `TURN_RIGHT` | nothing (Jev: 1.8 food / game) |
| [coderhh](https://github.com/coderhh/jev-snake) | text grid, heading | only non-fatal directions | fatal-move filter; override for Laya |
| [sorrycc](https://github.com/sorrycc/typesafe-snake) | text grid, head, food, heading | safe directions with facts: "food is 8 steps away after this move; 141 of 141 empty cells stay reachable" | filter, flood fill |
| [ximing](https://github.com/ximing/jev-snake-game) | grid + per-candidate facts | move choice, danger score, survival noul, safe + progress noul per direction | filter, thresholds + fallbacks |
| [StevanusPangau](https://github.com/StevanusPangau/jev-snake) | snapshot + waypoints | `food` / `open_area` / `border_loop` | every tick: greedy pathing + BFS seatbelt |

## One decision, known answer

Games mix many effects, so we first asked for single moves on fixed situations where code knows the good moves: not a dead end, and as close to the food as any non-dead-end move. The chart shows the **hard** set, 100 states where going straight is legal but wrong. Chance is about 50%.

![Good picks on hard states, per request and model](snake-report/probe.svg)

| Request | Decider 2B | Decider 4B | Kev 4B | CLM 8B | GLiNER 340M | GLiNER 1B | Laya | Decider 2B latency |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Raw board | 0.59 / 0.05 | 0.63 / 0.10 | 0.93 / 0.79 | 0.45 / 0.25 | 0.58 / 0.00 | 0.58 / 0.00 | 0.58 / 0.00 | 353 ms |
| Relative, in words | 0.69 / 0.46 | 0.69 / 0.54 | 0.84 / 0.93 | 0.35 / 0.45 | 0.38 / 0.59 | 0.65 / 0.60 | 0.47 / 0.40 | 184 ms |
| Facts in the options (sorrycc) | 0.68 / 0.10 | 0.74 / 0.46 | 0.74 / 0.31 | 0.64 / 0.19 | 0.65 / 0.00 | 0.60 / 0.14 | 0.52 / 0.18 | 532 ms |
| Judged options + heading in state | 0.73 / 0.57 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.80 / 0.28 | 0.69 / 0.00 | 0.73 / 0.25 | 185 ms |
| **Judged options, verdicts only** | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.93 / 0.86 | 0.81 / 0.72 | 0.61 / 0.39 | 142 ms |
| **Judged, eating worded as 'closer'** | 0.98 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.95 / 0.90 | 0.79 / 0.70 | – | 140 ms |

Cells: good pick on all 150 states / on the 100 hard states. Kev 4B is the only model that reads the raw board (93%) and isn't distracted by the heading. Laya, a 421M encoder, stays below chance on the hard states with every request, and in games it never gets going (0–0.5 food).

## The two things that break a small model

**Numbers that must be compared across options.** sorrycc's options carry exact numbers. Decider 2B picks the good move 67% of the time. Adding the rule "take the move after which the food is the fewest steps away" to the instruction lifts that to 82%. Writing the comparison into each option lifts it to 98–99%, whether as words ("moves closer to the food") or as a before→after number ("distance changes from 9 to 8").

**Direction words in the state.** With `heading: up` and "the food is 5 down and 5 right" in the context, Decider went straight on 43% of the hard states, even when the straight option read "moves away from the food". With the state removed: 0%. Renaming the options from `up/down/left/right` to `move 1/2/3` changed nothing. It's the context that pulls.

sorrycc's facts, as Decider reads them (67% good):

```text
Context:
{"board": [..12 rows..], "legend": "H = snake head, ...",
 "head": {"row": 4, "col": 9}, "food": {"row": 8, "col": 4},
 "heading": "right", "snake_length": 3, ...}

Question: You are playing the game Snake. Choose the direction ... Player strategy: Stay alive and eat food.
Options:
(A) up: left turn, head moves to row 3 col 9; food is 10 steps away after this move; 141 of 141 empty cells stay reachable; can still follow its own tail out
(B) down: right turn, head moves to row 5 col 9; food is 8 steps away after this move; 141 of 141 ...
(C) right: straight, head moves to row 4 col 10; food is 10 steps away after this move; 141 of 141 ...
Answer: (
```

Judged options, same situation (99% good):

```text
Context:
Choose the best move for the snake.

Question: Snake game: pick the next move. Every listed move is safe for this step. Never take a DEAD END. Prefer a move that eats the food or moves closer to it, unless it leaves much less room than another move. Player strategy: Stay alive and eat food.
Options:
(A) up: moves away from the food; keeps the most room
(B) down: moves closer to the food; keeps the most room
(C) right: moves away from the food; keeps the most room
Answer: (
```

Decider scores the logits of the letters `A`, `B`, `C` right after the final `(` and applies its temperature (1.3). Nothing is generated. Code has done the geometry: which moves survive, distance before and after, flood-fill room, dead ends. The model's remaining job is to weigh the verdicts against the instruction and the player's strategy text. That's also the only step that responds to natural language.

## CLM 8B: a bi-encoder reads options differently

[CLM](https://github.com/Contrastive-LM/CLM) (Contrastive-LM, 24 September) serves the same `/v1/systemone` API but works differently: a frozen Qwen3-8B embeds the state + question and each option *separately*, trained heads project both into one space, and the answer is a softmax over cosines. On this Mac, Qwen3-8B runs on MLX in place of vLLM (`adapters/mlx_embed_server.py`). Three consequences in Snake:

- **Identical option texts get identical probabilities.** Two moves that both read "moves away from the food; keeps the most room" score exactly the same (0.293 each). An option can't see the others, so nothing can be compared across options. Only the verdict text written into each one counts.
- **It has a blind spot for "eats".** On 80 states where one move eats the food, CLM picked it 0% of the time with every wording tried: "eats the food", "reaches the food", "moves onto the food", "moves closer to the food and eats it". With the eating move described as "moves closer to the food; keeps the most room" (true: the distance drops to 0), 97%. Its judged games went from 0 food (all starved) to 36.2.
- **It's nearly free once warm.** With judged options the state is a fixed sentence and the verdicts come from a handful of strings, so after the first ticks every vector is cached: ~4 ms per move on average, 10 games in 16 s. With changing texts (facts in the options) a call costs ~300 ms here, mostly the 8B encoder.

CLM's own game demo, [T-Rex runner vs Jev](https://github.com/Contrastive-LM/CLM/tree/main/examples/t_rex), phrases moves the same way: a physics planner labels each action, as in `jump: Safe. Clears the 2 large cacti. Best.`, and a shield replaces unsafe answers. With that help both models survive every course, but CLM agreed with the planner on 66% of decisions (4,883 shield interventions) and Jev on 99% (28).

## Decider 4B and GLiNER

Three more models from the sentiment tutorial, zero-shot as released: **Decider 4B v2** (Qwen3.5-4B, the best sentiment model here at 75.0%) and **GLiNER2.5-Decide** at 340M and 1B (DeBERTa-style encoders that pack the question and every label into one prompt). GLiNER runs in its own environment behind a small `/v1/systemone` adapter (`adapters/gliner_systemone_server.py`), using gliner2's `Classifier` API so every option gets a probability. It rejects "(" in option text, so the adapter writes braces instead.

- **Decider 4B isn't distracted by the heading** (judged + heading: 99% / 100%, where the 2B drops to 57% on hard states) and puts 91% of the probability on good moves. In games it's the greedier player: when a roomier move existed it took the "leaves much less room" option 26% of the time (Decider 2B 6%, Kev 4B 58%). It's also about twice as slow: ~260 ms per move.
- **GLiNER shares CLM's blind spot for "eats".** GLiNER 340M picks 93% good moves in the probe but ate 2.7 per game with judged options, starving every time. With the eating move worded "moves closer to the food", 26.3. Both score option text by matching; neither reasons over it.
- **The composed rows are mostly the code's work.** ximing's gate hands the move to code when the model is under 0.55 confident, so the flatter a model's probabilities, the more code plays:

| Composed questions | Food / game | Model's choice | Code: model unsure | Code: survival mode | Code: one safe move |
|---|--:|--:|--:|--:|--:|
| GLiNER 340M | 39.4 | 33% | 59% | 0% | 7% |
| Decider 2B | 38.3 | 50% | 43% | 0% | 7% |
| Decider 4B | 32.7 | 67% | 26% | 0% | 7% |
| GLiNER 1B | 3.8 | 41% | 54% | 0% | 5% |
| CLM 8B | 0.0 | 0% | 0% | 97% | 3% |

GLiNER 340M's 39.4 food is the best model row, but code chose two moves in three, close to what code alone scores (41.1). CLM answers the danger and survival questions as if the snake were always in trouble, so the gate stays in survival mode, always takes the roomiest move, and never eats. That 0 is for this request only: composed is built on the original judged wording ("eats the food"). CLM's own best is **judged, plain wording: 36.2 food at ~4 ms per move** (CLM section above).

## Full games

Same 10 seeds for every row, 12×12 board. A game ends on death, after 144 steps without food (starved), or at 500 steps. Raw board and relative phrasing let the model pick fatal moves; the other requests only offer safe ones.

| Controller | Food / game | Best | Steps | Ended by | Per move, p50 / mean |
|---|--:|--:|--:|---|--:|
| Decider 2B · Raw board | 0.0 | 0 | 7 | died 10 | 357 / 358 ms |
| Decider 2B · Relative, in words | 0.1 | 1 | 145 | starved 10 | 185 / 185 ms |
| Decider 2B · Facts in the options | 1.2 | 4 | 175 | starved 10 | 448 / 456 ms |
| **Decider 2B · Judged options** | 36.9 | 46 | 477 | step cap (500) 8, died 2 | 141 / 145 ms |
| **Decider 2B · Judged, plain wording** | 34.9 | 46 | 459 | died 5, step cap (500) 5 | 140 / 141 ms |
| Decider 2B · Composed questions | 38.3 | 44 | 486 | step cap (500) 8, died 2 | 308 / 311 ms |
| Decider 4B · Raw board | 0.1 | 1 | 9 | died 10 | 557 / 556 ms |
| Decider 4B · Relative, in words | 0.0 | 0 | 144 | starved 10 | 310 / 312 ms |
| Decider 4B · Facts in the options | 3.6 | 7 | 211 | starved 10 | 813 / 773 ms |
| **Decider 4B · Judged options** | 29.3 | 43 | 312 | died 9, step cap (500) 1 | 257 / 259 ms |
| **Decider 4B · Judged, plain wording** | 30.8 | 43 | 332 | died 9, step cap (500) 1 | 261 / 260 ms |
| Decider 4B · Composed questions | 32.7 | 40 | 380 | died 7, step cap (500) 3 | 502 / 504 ms |
| Kev 4B · Raw board | 9.0 | 17 | 92 | died 10 | 265 / 268 ms |
| Kev 4B · Relative, in words | 13.1 | 22 | 166 | died 10 | 207 / 208 ms |
| Kev 4B · Facts in the options | 17.2 | 25 | 411 | step cap (500) 6, starved 4 | 332 / 334 ms |
| **Kev 4B · Judged options** | 29.5 | 41 | 321 | died 10 | 108 / 108 ms |
| Kev 4B · Judged, plain wording | 25.3 | 34 | 251 | died 10 | 108 / 110 ms |
| CLM 8B · Raw board | 0.0 | 0 | 7 | died 10 | 284 / 254 ms |
| CLM 8B · Relative, in words | 0.0 | 0 | 144 | starved 10 | 0 / 5 ms |
| CLM 8B · Facts in the options | 1.8 | 6 | 167 | starved 9, died 1 | 0 / 295 ms |
| CLM 8B · Judged options | 0.0 | 0 | 144 | starved 10 | 0 / 0 ms |
| **CLM 8B · Judged, plain wording** | 36.2 | 44 | 461 | died 5, step cap (500) 5 | 0 / 4 ms |
| CLM 8B · Composed questions | 0.0 | 0 | 144 | starved 10 | 0 / 0 ms |
| GLiNER 340M · Raw board | 0.0 | 0 | 7 | died 10 | 256 / 256 ms |
| GLiNER 340M · Relative, in words | 0.0 | 0 | 144 | starved 10 | 102 / 103 ms |
| GLiNER 340M · Facts in the options | 0.4 | 2 | 153 | starved 10 | 373 / 375 ms |
| GLiNER 340M · Judged options | 2.7 | 15 | 181 | starved 10 | 72 / 71 ms |
| GLiNER 340M · Judged, plain wording | 26.3 | 37 | 371 | died 5, step cap (500) 4, starved 1 | 71 / 70 ms |
| GLiNER 340M · Composed questions | 39.4 | 44 | 497 | step cap (500) 9, died 1 | 169 / 166 ms |
| GLiNER 1B · Raw board | 0.0 | 0 | 7 | died 10 | 268 / 273 ms |
| GLiNER 1B · Relative, in words | 1.7 | 6 | 121 | starved 7, died 3 | 123 / 123 ms |
| GLiNER 1B · Facts in the options | 0.3 | 1 | 151 | starved 10 | 317 / 320 ms |
| GLiNER 1B · Judged options | 15.3 | 25 | 315 | starved 4, died 4, step cap (500) 2 | 84 / 82 ms |
| GLiNER 1B · Judged, plain wording | 13.7 | 24 | 324 | starved 6, died 3, step cap (500) 1 | 81 / 82 ms |
| GLiNER 1B · Composed questions | 3.8 | 8 | 235 | starved 10 | 196 / 196 ms |
| Laya · Facts in the options | 0.5 | 2 | 155 | starved 10 | 100 / 100 ms |
| Laya · Judged options | 0.0 | 0 | 144 | starved 10 | 38 / 39 ms |
| *code only: random safe move* | 0.5 | 2 | 175 | starved 10 | – |
| *code only: greedy* | 21.0 | 32 | 213 | died 10 | – |
| *code only: greedy + dead-end check* | 41.1 | 44 | 484 | step cap (500) 8, died 2 | – |

> Most judged, composed and greedy + dead-end games reach the 500-step cap, so their food counts are capped too. The code baselines use the same facts the judged options are written from, so the judged request doesn't beat code at Snake. It matches code while the move stays a model decision, one you can steer with the strategy text.

## The request that works

Sent once per tick when at least two moves survive; with one safe move, code takes it without calling the model.

```json
{
  "state": "Choose the best move for the snake.",
  "questions": {"move": {
    "type": "choice",
    "instructions": "Snake game: pick the next move. Every listed move is safe for this step. Never take a DEAD END. Prefer a move that eats the food or moves closer to it, unless it leaves much less room than another move. Player strategy: Stay alive and eat food.",
    "criteria": {
      "up":    "moves away from the food; keeps the most room",
      "down":  "moves closer to the food; keeps the most room",
      "right": "moves away from the food; keeps the most room"
    }}}
}
```

Verdicts come from `snake/formulations.py` (`judge()`): *eats the food* / *moves closer* / *moves away*, then *DEAD END* (flood fill smaller than the snake and no way to follow the tail), *keeps the most room*, *keeps almost as much room* (≥ 80%), or *leaves much less room (n of m cells)*. For CLM and GLiNER 340M, use the plain wording, which describes the eating move as "moves closer to the food; keeps the most room".

## Limits of this test

We had no TypeSafe API key, so hosted Jev is represented only by nadeem4's published run (10 games, 10×10, relative phrasing, starvation after 60 steps without food). That setup differs from ours (12×12, 144 steps), so compare the 1.8 with our rows only loosely. Every model runs zero-shot, as released. The probe's "good move" only checks food distance and dead ends, not room, which is why it misses the 4B models' habit of chasing food into tight spaces. On composed rows, code chooses a third to two thirds of the moves. Ten seeds per row give wide intervals, so read differences of a few food as noise, and most of the best games hit the 500-step cap.

---

Code: `snake/`, `08_snake_server.py` (live demo with the decision panel), `09_snake_benchmark.py`, `10_snake_probe.py`; write-up in [docs/5-snake.md](5-snake.md). Models: Decider 2B v10 and 4B v2 (PyTorch MPS), Kev 4B (MLX server), CLM 8B (MLX encoder + CPU heads), GLiNER2.5-Decide 340M and 1B (MPS, own environment), Laya (MPS), all on an Apple M5 with 32 GB.
