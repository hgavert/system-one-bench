# 5 · A System One model plays Snake

*Researched 23 September 2026.* Within a week of Jev's release, several people posted Snake played by Jev.
This doc reads how they asked for each move, tries the same requests on the open models from this repo,
and finds the version a small open model can actually play.

Files: [`snake/game.py`](../snake/game.py) (rules, flood fill), [`snake/formulations.py`](../snake/formulations.py)
(the six requests), [`snake/engine.py`](../snake/engine.py) (Decider / Laya / any `/v1/systemone` server),
[`08_snake_server.py`](../08_snake_server.py) (the demo), [`09_snake_benchmark.py`](../09_snake_benchmark.py) (games),
[`10_snake_probe.py`](../10_snake_probe.py) (single decisions with a known right answer).

## 5.1 How the published demos ask

Every demo sends the same shape, `{"state": ..., "questions": {"move": {"type": "choice", ...}}}`, once per tick.
They differ in what goes into `state`, what the options say, and how much code decides before or after the model.

| Demo | State | Options | Code decides |
|---|---|---|---|
| [iammusham/jev-snake](https://github.com/iammusham/jev-snake) | coordinates, body, walls, danger cells as JSON | `UP/DOWN/LEFT/RIGHT`: "Move one cell in negative y" | nothing (no pathing, no filter) |
| [nadeem4/jev-demo](https://github.com/nadeem4/jev-demo) | phrases: food "3 cells ahead and 2 to your right", "if_you_turn_left: clear for 4 cells, then the wall" | `TURN_LEFT / STRAIGHT / TURN_RIGHT` | nothing |
| [coderhh/jev-snake](https://github.com/coderhh/jev-snake) | text grid, heading | only legal (non-fatal) directions | removes fatal moves; skips the model when one move is left; for Laya, overrides any move away from the food |
| [sorrycc/typesafe-snake](https://github.com/sorrycc/typesafe-snake) | text grid, head, food, heading | only safe directions, each with facts: "food is 8 steps away after this move; 141 of 141 empty cells stay reachable; DEAD END" | removes fatal moves; computes facts (flood fill) |
| [ximing/jev-snake-game](https://github.com/ximing/jev-snake-game) | grid, per-candidate facts | one request: move `choice`, `danger` score, `prioritize_survival` noul, and a `safe` + `progress` noul per direction | thresholds: survival mode picks max reachable space; low confidence falls back to progress, then Manhattan distance |
| [StevanusPangau/jev-snake](https://github.com/StevanusPangau/jev-snake) | snapshot + waypoints | a **waypoint** (`food`, `open_area`, `border_loop`) every ~2.6 s | everything per tick: greedy pathing to the waypoint and a BFS "seatbelt" that vetoes moves into pockets under 8 cells |

The one published measurement of Jev itself playing ([nadeem4's arena](https://github.com/nadeem4/jev-demo), 10 games,
10×10, the *relative, in words* request): **Jev ate 1.8 food per game**, never died, but turned right on 71% of moves
and circled until the starvation limit. A few lines of greedy code ate 17.3. Laya ate 0.5 and died in 9 of 10.
So the smooth "straight to the food" videos come from demos where code carries the spatial work: legal-move
filtering, flood-fill facts, gates, or a waypoint pathfinder.

## 5.2 Six requests

`snake/formulations.py` implements four published requests and two written here:

* **grid**: raw board, 3 directions (iammusham / coderhh, without the fatal-move filter)
* **relative**: nadeem4's phrases and `TURN_*` options, verbatim
* **facts**: sorrycc's state and option text, verbatim
* **judged**: sorrycc's facts, rewritten as verdicts, with no state (below)
* **judged-plain**: *judged*, with the eating move worded "moves closer to the food; keeps the most room" (for CLM, 5.6)
* **composed**: ximing's extra `danger` score and `survival` noul on top of *judged*, gated by the same thresholds

## 5.3 Probe: one decision, known answer

Playing games mixes many effects. `10_snake_probe.py` asks for single moves on fixed states where code knows
which moves are good (not a dead end, and as close to the food as any non-dead-end move). The **hard** set holds
only states where going straight is legal but wrong.

Good pick, all states / hard states (chance ≈ 0.50 on both):

| Request | Decider 2B | Decider 4B | Kev 4B | CLM 8B | GLiNER 340M | GLiNER 1B | Laya |
|---|---|---|---|---|---|---|---|
| grid | 0.59 / 0.05 | 0.63 / 0.10 | 0.93 / 0.79 | 0.45 / 0.25 | 0.58 / 0.00 | 0.58 / 0.00 | 0.58 / 0.00 |
| relative | 0.69 / 0.46 | 0.69 / 0.54 | 0.84 / 0.93 | 0.35 / 0.45 | 0.38 / 0.59 | 0.65 / 0.60 | 0.47 / 0.40 |
| facts (sorrycc) | 0.68 / 0.10 | 0.74 / 0.46 | 0.74 / 0.31 | 0.64 / 0.19 | 0.65 / 0.00 | 0.60 / 0.14 | 0.52 / 0.18 |
| judged + heading and food in state | 0.73 / 0.57 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.80 / 0.28 | 0.69 / 0.00 | 0.73 / 0.25 |
| **judged, verdicts only** | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.93 / 0.86 | 0.81 / 0.72 | 0.61 / 0.39 |
| judged, eating worded as "closer" | 0.98 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.95 / 0.90 | 0.79 / 0.70 | – |

Two things break the small models:

1. **Numbers to compare across options.** Decider can't tell which of "food is 10 steps away" and "8 steps away"
   is smaller: 0.67 good. With the rule spelled out in the instruction, still 0.82. With the comparison written
   into each option (*"moves closer to the food"*, or *"distance changes from 9 to 8"*), 0.98–0.99.
2. **Direction words in the state pull toward straight.** With `heading: up` and "the food is 5 down and 5 right"
   in the context, Decider went straight on 43% of hard states, even when that option read "moves away from the
   food". Remove the state and it went straight 0%. Kev 4B is not distracted by it.

The option *names* don't matter: renaming `up/down/left/right` to `move 1/2/3` changed nothing.

## 5.4 The request that works

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

What Decider reads (`decider/prompt.py` layout; the answer is the softmax over the logits of `A`, `B`, `C` right
after the final `(`, at temperature 1.3):

```
Context:
Choose the best move for the snake.

Question: Snake game: pick the next move. Every listed move is safe for this step. Never take a DEAD END. ...
Options:
(A) up: moves away from the food; keeps the most room
(B) down: moves closer to the food; keeps the most room
(C) right: moves away from the food; keeps the most room
Answer: (
```

Code does the geometry: which moves survive, Manhattan distance before and after, flood-fill room, dead ends.
The model does the one thing left: weigh the verdicts against the instruction and the player's strategy text.
That is also the only part that responds to natural language. Write "hug the walls" into the strategy and the
probabilities move; nothing else in the pipeline reads it.

## 5.5 Games

10 seeds, 12x12 board, max 500 steps.

| Controller | Food eaten (mean / best) | Steps | Died | Starved | Model calls | Code-only ticks | Latency p50 / mean | Tokens/call |
|---|---|---|---|---|---|---|---|---|
| Decider 2B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 357 / 358 ms | 361 |
| Decider 2B · Relative, in words | 0.1 / 1 | 145 | 0% | 10 | 1446 | 0 | 185 / 185 ms | 160 |
| Decider 2B · Facts in the options | 1.2 / 4 | 175 | 0% | 10 | 1603 | 144 | 448 / 456 ms | 477 |
| Decider 2B · Judged options | 36.9 / 46 | 477 | 20% | 0 | 4419 | 348 | 141 / 145 ms | 120 |
| Decider 2B · Judged, plain wording | 34.9 / 46 | 459 | 50% | 0 | 4247 | 346 | 140 / 141 ms | 121 |
| Decider 2B · Composed questions | 38.3 / 44 | 486 | 20% | 0 | 4535 | 326 | 308 / 311 ms | 303 |
| Decider 4B · Raw board | 0.1 / 1 | 9 | 100% | 0 | 86 | 0 | 557 / 556 ms | 360 |
| Decider 4B · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 310 / 312 ms | 160 |
| Decider 4B · Facts in the options | 3.6 / 7 | 211 | 0% | 10 | 2057 | 55 | 813 / 773 ms | 524 |
| Decider 4B · Judged options | 29.3 / 43 | 312 | 90% | 0 | 2944 | 177 | 257 / 259 ms | 121 |
| Decider 4B · Judged, plain wording | 30.8 / 43 | 332 | 90% | 0 | 3111 | 211 | 261 / 260 ms | 121 |
| Decider 4B · Composed questions | 32.7 / 40 | 380 | 70% | 0 | 3527 | 272 | 502 / 504 ms | 304 |
| Kev 4B · Raw board | 9.0 / 17 | 92 | 100% | 0 | 920 | 0 | 265 / 268 ms | 243 |
| Kev 4B · Relative, in words | 13.1 / 22 | 166 | 100% | 0 | 1664 | 0 | 207 / 208 ms | 138 |
| Kev 4B · Facts in the options | 17.2 / 25 | 411 | 0% | 4 | 3884 | 230 | 332 / 334 ms | 371 |
| Kev 4B · Judged options | 29.5 / 41 | 321 | 100% | 0 | 2990 | 218 | 108 / 108 ms | 108 |
| Kev 4B · Judged, plain wording | 25.3 / 34 | 251 | 100% | 0 | 2334 | 175 | 108 / 110 ms | 108 |
| CLM 8B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 284 / 254 ms | 183 |
| CLM 8B · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 0 / 5 ms | – |
| CLM 8B · Facts in the options | 1.8 / 6 | 167 | 10% | 9 | 1604 | 67 | 0 / 295 ms | – |
| CLM 8B · Judged options | 0.0 / 0 | 144 | 0% | 10 | 1397 | 43 | 0 / 0 ms | – |
| CLM 8B · Judged, plain wording | 36.2 / 44 | 461 | 50% | 0 | 4305 | 308 | 0 / 4 ms | – |
| CLM 8B · Composed questions | 0.0 / 0 | 144 | 0% | 10 | 1397 | 43 | 0 / 0 ms | – |
| GLiNER2.5-Decide · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 256 / 256 ms | – |
| GLiNER2.5-Decide · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 102 / 103 ms | – |
| GLiNER2.5-Decide · Facts in the options | 0.4 / 2 | 153 | 0% | 10 | 1400 | 130 | 373 / 375 ms | – |
| GLiNER2.5-Decide · Judged options | 2.7 / 15 | 181 | 0% | 10 | 1748 | 66 | 72 / 71 ms | – |
| GLiNER2.5-Decide · Judged, plain wording | 26.3 / 37 | 371 | 50% | 1 | 3440 | 273 | 71 / 70 ms | – |
| GLiNER2.5-Decide · Composed questions | 39.4 / 44 | 497 | 10% | 0 | 4606 | 368 | 169 / 166 ms | – |
| GLiNER2.5-Decide-1B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 268 / 273 ms | – |
| GLiNER2.5-Decide-1B · Relative, in words | 1.7 / 6 | 121 | 30% | 7 | 1211 | 0 | 123 / 123 ms | – |
| GLiNER2.5-Decide-1B · Facts in the options | 0.3 / 1 | 151 | 0% | 10 | 1398 | 115 | 317 / 320 ms | – |
| GLiNER2.5-Decide-1B · Judged options | 15.3 / 25 | 315 | 40% | 4 | 2837 | 317 | 84 / 82 ms | – |
| GLiNER2.5-Decide-1B · Judged, plain wording | 13.7 / 24 | 324 | 30% | 6 | 2849 | 387 | 81 / 82 ms | – |
| GLiNER2.5-Decide-1B · Composed questions | 3.8 / 8 | 235 | 0% | 10 | 2242 | 106 | 196 / 196 ms | – |
| Laya · Facts in the options | 0.5 / 2 | 155 | 0% | 10 | 1442 | 111 | 100 / 100 ms | 336 |
| Laya · Judged options | 0.0 / 0 | 144 | 0% | 10 | 1305 | 135 | 38 / 39 ms | 99 |
| *random (code only)* | 0.5 / 2 | 175 | 0% | 10 | 0 | 0 | – | – |
| *greedy (code only)* | 21.0 / 32 | 213 | 100% | 0 | 0 | 0 | – | – |
| *greedy-safe (code only)* | 41.1 / 44 | 484 | 20% | 0 | 0 | 0 | – | – |

**Reading it.**

* **Only the judged requests let models play.** On the raw board, five of the six models tried die within ~9 steps
  every game; with nadeem4's phrasing or sorrycc's facts, all but Kev circle and starve. Kev 4B partly reads the
  board (9.0 raw, 13.1 relative; Jev's published figure with that phrasing, on a 10×10 board, is 1.8).
* **Best model that decides every move: Decider 2B, judged options**: 36.9 food, best game 46, 2 of 10 died,
  145 ms per move. The best code baseline, which knows the same facts, gets 41.1.
* **Better single moves, shorter games.** Decider 4B and Kev 4B match the 2B on the probe but die in 9 and 10 games
  of 10. Replaying their judged games: when a roomier move existed, they took the "leaves much less room" option
  26% (4B) and 58% (Kev) of the time, against 6% for the 2B, and almost never stepped away from the food (0.5% and
  0.2%, against 4.6%). They follow "closer to the food" and skip the "unless it leaves much less room" part.
* **Composed rows are partly code.** ximing's gate hands the move to code when the model is below 0.55 confident.
  Share of moves the model chose itself: Decider 4B 67%, Decider 2B 50%, GLiNER 1B 41%, GLiNER 340M 33%. GLiNER
  340M's 39.4 is therefore mostly the fallback's. CLM stays in survival mode (97% of moves, code picks the roomiest)
  and never eats.
* Most of the best games hit the 500-step cap, so their food counts are capped too.

## 5.6 CLM 8B: a bi-encoder needs its own wording

[CLM](https://github.com/Contrastive-LM/CLM) serves the same `/v1/systemone` API, so it plugs in as an HTTP
engine (setup in [doc 4 §4.5](4-zero-shot-reproductions.md): Qwen3-8B on MLX via `adapters/mlx_embed_server.py`,
then the unchanged `clm-serve`). It embeds state + question and each option **separately** and answers with a
softmax over cosines. Three consequences:

* **Identical option texts get identical probabilities** (two "moves away from the food; keeps the most room"
  options: 0.293 each). Nothing is compared across options; only the verdict in each option counts.
* **A blind spot for "eats".** On 80 states with an eating move, CLM picked it 0% of the time with every wording
  tried ("eats the food", "reaches the food", "moves onto the food", "moves closer to the food and eats it"),
  and ranked "moves away from the food" above it. With the eating move described as "moves closer to the food;
  keeps the most room" (true: the distance drops to 0), 97%. Its judged games went from 0 food (all 10 starved)
  to 36.2.
* **Nearly free once warm.** With judged options the state is a fixed sentence and the verdicts come from a handful
  of strings, so after the first ticks every vector is in CLM's cache: 4 ms per move on average, all 10 games in
  16 s of wall time. With texts that change every tick (facts), ~300 ms per call here, mostly the 8B encoder.

CLM's own game demo ([`examples/t_rex`](https://github.com/Contrastive-LM/CLM/tree/main/examples/t_rex), T-Rex
runner vs Jev) phrases actions the same way: a physics planner labels each one (`jump: Safe. Clears the 2 large
cacti. Best.`) and a shield replaces unsafe answers. With that help both survive every course, but CLM agreed
with the planner on 66% of decisions (4,883 shield interventions) and Jev on 99% (28).

## 5.7 Decider 4B and GLiNER

* **Decider 4B v2** (`models/decider-4b-v2`, from the sentiment tutorial): pass `--engine decider:models/decider-4b-v2`
  to any Snake script. It isn't distracted by the heading (judged + heading: 0.99 / 1.00, the 2B: 0.73 / 0.57) and puts 91% of the
  probability on good moves, but plays the greedier game above, at ~260 ms per move.
* **GLiNER2.5-Decide 340M and 1B** run in `third_party/gliner2-env` behind
  [`adapters/gliner_systemone_server.py`](../adapters/gliner_systemone_server.py), a `/v1/systemone` adapter on
  gliner2's `Classifier` API, which returns a probability for every label (the sentiment adapter's `classify_text`
  returns only the winner). gliner2 rejects `(` and `)` in labels and instructions, so the adapter writes `{ }`.
  GLiNER packs all questions of a request into one prompt, so extra questions change its move answer.
* **GLiNER 340M shares CLM's "eats" blind spot**: 2.7 food with judged options, 26.3 with the plain wording. GLiNER 1B
  doesn't (15.3 / 13.7); it's just weaker. Both GLiNER models answer in 70–85 ms.

## 5.8 Run it

```bash
uv run python 08_snake_server.py                   # demo on http://127.0.0.1:8765, Decider 2B
uv run python 10_snake_probe.py --engine laya      # probe one model
uv run python 09_snake_benchmark.py --only judged  # 10 games
```

Kev 4B: start its server as `run_kev.sh` does (`third_party/kev`, `python -m kev.serve --run jaredpalmer/kev-4b --port 8009`),
then pass `--engine http:http://127.0.0.1:8009,kev-4b` to any of the three scripts. GLiNER:
`third_party/gliner2-env/.venv/bin/python adapters/gliner_systemone_server.py --port 8710` (add
`--model fastino/GLiNER2.5-Decide-1B` for the 1B), then `--engine http:http://127.0.0.1:8710,gliner-decide`. CLM: start its encoder and
`clm-serve` as in doc 4 §4.5, then `--engine http:http://127.0.0.1:8700,clm-latest`, and pick the
"Judged, plain wording" tab in the demo.
