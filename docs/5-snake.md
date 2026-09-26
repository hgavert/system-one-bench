# 5 · System One models play Snake

*Researched 23–26 September 2026.* Within a week of Jev's release, several people posted Snake played by Jev. This
doc reads how they asked for each move, puts the same requests to seven open System One models, and finds the
requests those models can actually play with. The results in report form: [snake-report.md](snake-report.md).

Files: [`snake/game.py`](../snake/game.py) (rules, flood fill), [`snake/formulations.py`](../snake/formulations.py)
(the six requests), [`snake/engine.py`](../snake/engine.py) (the engines), [`08_snake_server.py`](../08_snake_server.py)
(the demo), [`09_snake_benchmark.py`](../09_snake_benchmark.py) (games), [`10_snake_probe.py`](../10_snake_probe.py)
(single decisions with a known right answer).

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
and circled until the starvation limit. A few lines of greedy code ate 17.3. So the smooth "straight to the food"
videos come from demos where code carries the spatial work: legal-move filtering, flood-fill facts, gates, or a
waypoint pathfinder.

## 5.2 The seven models and how they plug in

Every Snake script takes `--engine`, and every engine answers the same Jev request (`engine.ask(request)` returns
the answers, the latency and the input tokens). Three models load in-process; the other four sit behind a
TypeSafe-compatible `POST /v1/systemone` server and are reached by `HTTPEngine`.

```python
def make_engine(spec):
    """'decider' | 'decider:<model dir>' | 'laya' | 'http:<url>[,<model>]'"""
    if spec == "decider":
        return DeciderEngine()
    if spec.startswith("decider:"):
        return DeciderEngine(path=spec.split(":", 1)[1])
    if spec == "laya":
        return LayaEngine()
    if spec.startswith("http:"):
        url, _, model = spec[5:].partition(",")
        return HTTPEngine(url, model or "kev-latest")
```

| Model | How it reads the request | `--engine` | Served by |
|---|---|---|---|
| Decider 2B | Qwen3.5-2B fine-tune: state, question and lettered options in one sequence; answer from the letter logits | `decider` | in-process (`models/decider-2b`, its own `decider/` package) |
| Decider 4B v2 | the same, on Qwen3.5-4B | `decider:models/decider-4b-v2` | in-process; only one Decider version per process, since each ships its own `decider/` |
| Kev 4B | LoRA on Qwen3.5-4B-Base; a pointer head scores each option's end token | `http:http://127.0.0.1:8009,kev-4b` | Kev's own server (MLX) |
| CLM 8B | bi-encoder: frozen Qwen3-8B embeds state + question and each option *separately*; softmax over cosines | `http:http://127.0.0.1:8700,clm-latest` | unchanged `clm-serve`, with Qwen3-8B on MLX via `adapters/mlx_embed_server.py` ([doc 4 §4.6](4-zero-shot-reproductions.md)) |
| GLiNER 340M | GLiNER2.5-Decide, a DeBERTa-v3-large schema encoder: question and all labels packed before the text | `http:http://127.0.0.1:8710,gliner-decide` | [`adapters/gliner_systemone_server.py`](../adapters/gliner_systemone_server.py) in `third_party/gliner2-env` |
| GLiNER 1B | GLiNER2.5-Decide-1B, the larger variant | `http:http://127.0.0.1:8711,gliner-decide-1b` | the same adapter, `--model fastino/GLiNER2.5-Decide-1B` |
| Laya | ModernBERT-large encoder (421M) with a `[MASK]` marker per option | `laya` | in-process |

The GLiNER adapter maps each Jev question to a gliner2 `Classifier` task (choice → single-label, noul →
true/false, score → ordinal) because that API returns a probability for every label; the sentiment adapter's
`classify_text` returns only the winner. gliner2 rejects `(` and `)` in labels and instructions, so the adapter
writes `{ }` instead. GLiNER scores all questions of a request in one prompt, so extra questions can change its move
answer; the other engines score each question in its own row (Decider's `independent=True`).

For the demo, "What the model reads" shows Decider's exact rows: `DeciderEngine.rows()` rebuilds them with the
checkpoint's own prompt builder (Decider 4B exposes `_system_one_items()` for this). The HTTP engines show only the
request JSON.

## 5.3 Six requests

`snake/formulations.py` implements four published requests and two written here from what the probe (5.4) showed:

* **grid**: raw board, 3 directions (iammusham / coderhh, without the fatal-move filter)
* **relative**: nadeem4's phrases and `TURN_*` options, verbatim
* **facts**: sorrycc's state and option text, verbatim
* **judged**: sorrycc's facts, rewritten as verdicts, with no state (5.5)
* **judged-plain**: *judged*, with the eating move worded "moves closer to the food; keeps the most room"
* **composed**: ximing's extra `danger` score and `survival` noul on top of *judged*, gated by the same thresholds

## 5.4 Probe: one decision, known answer

Playing games mixes many effects. `10_snake_probe.py` asks for single moves on fixed states where code knows which
moves are good (not a dead end, and as close to the food as any non-dead-end move). The **hard** set holds only
states where going straight is legal but wrong.

Good pick, all states / hard states (chance ≈ 0.50 on both):

| Request | Decider 2B | Decider 4B | Kev 4B | CLM 8B | GLiNER 340M | GLiNER 1B | Laya |
|---|---|---|---|---|---|---|---|
| grid | 0.59 / 0.05 | 0.63 / 0.10 | 0.93 / 0.79 | 0.45 / 0.25 | 0.58 / 0.00 | 0.58 / 0.00 | 0.58 / 0.00 |
| relative | 0.69 / 0.46 | 0.69 / 0.54 | 0.84 / 0.93 | 0.35 / 0.45 | 0.38 / 0.59 | 0.65 / 0.60 | 0.47 / 0.40 |
| facts (sorrycc) | 0.68 / 0.10 | 0.74 / 0.46 | 0.74 / 0.31 | 0.64 / 0.19 | 0.65 / 0.00 | 0.60 / 0.14 | 0.52 / 0.18 |
| judged + heading and food in state | 0.73 / 0.57 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.80 / 0.28 | 0.69 / 0.00 | 0.73 / 0.25 |
| **judged, verdicts only** | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.93 / 0.89 | 0.93 / 0.86 | 0.81 / 0.72 | 0.61 / 0.39 |
| judged, eating worded as "closer" | 0.98 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.95 / 0.90 | 0.79 / 0.70 | – |

Kev 4B is the only model that reads the raw board. Three things break the others:

1. **Numbers to compare across options.** With sorrycc's facts, every model is at 0–46% on the hard states. The
   same facts as a verdict in each option lift all of them, and all but Laya to 72–100%. On Decider 2B, spelling out
   the rule in the instruction ("take the move after which the food is the fewest steps away") got only from 0.67 to
   0.82 on all states; writing the comparison into each option (*"moves closer to the food"*, or *"distance changes
   from 9 to 8"*) reached 0.98–0.99.
2. **Direction words in the state pull toward straight.** Compare the two judged rows: with `heading: up` and "the
   food is 5 down and 5 right" in the context, Decider 2B drops to 0.57 on the hard states, GLiNER 340M to 0.28 and
   GLiNER 1B to 0.00, going straight even when that option reads "moves away from the food". The two 4B models and
   CLM are unaffected. On Decider 2B, renaming `up/down/left/right` to `move 1/2/3` changed nothing: it's the context
   that pulls.
3. **The word "eats"** (CLM, GLiNER 340M). Both score option text by matching it. CLM embeds each option on its own,
   so identical option texts get identical probabilities (two "moves away from the food; keeps the most room":
   0.293 each). On 80 states with an eating move, CLM picked it 0% of the time with every wording tried ("eats the
   food", "reaches the food", "moves onto the food", "moves closer to the food and eats it") and ranked "moves away
   from the food" above it; described as "moves closer to the food; keeps the most room" (true: the distance drops
   to 0), 97%. The probe rarely has the food one step away, so this shows mostly in games (5.6).

CLM's own game demo ([`examples/t_rex`](https://github.com/Contrastive-LM/CLM/tree/main/examples/t_rex), T-Rex runner
vs Jev) phrases actions the same way: a physics planner labels each one (`jump: Safe. Clears the 2 large cacti.
Best.`) and a shield replaces unsafe answers. With that help both survive every course, but CLM agreed with the
planner on 66% of decisions (4,883 shield interventions) and Jev on 99% (28).

## 5.5 The request that works

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

The verdicts come from `judge()` in `snake/formulations.py`: *eats the food* / *moves closer* / *moves away*, then
*DEAD END* (flood fill smaller than the snake and no way to follow the tail), *keeps the most room*, *keeps almost as
much room* (≥ 80%), or *leaves much less room (n of m cells)*. With `plain=True` (the judged-plain request) the eating
move reads "moves closer to the food; keeps the most room"; use that for CLM and GLiNER 340M.

Code does the geometry: which moves survive, Manhattan distance before and after, flood-fill room, dead ends. The
model does the one thing left: weigh the verdicts against the instruction and the player's strategy text. That is
also the only part that responds to natural language. Write "hug the walls" into the strategy and the probabilities
move; nothing else in the pipeline reads it.

## 5.6 Games

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
  145 ms per move. CLM 8B with the plain wording is level (36.2) at 4 ms. The best code baseline, which knows the same
  facts, gets 41.1.
* **The "eats" wording decides two models' games.** Judged → judged-plain: CLM 0 → 36.2, GLiNER 340M 2.7 → 26.3.
  For the others the plain wording makes little difference (Decider 2B −2.0, Decider 4B +1.5, Kev −4.2, GLiNER 1B
  −1.6).
* **Better single moves, shorter games.** Decider 4B and Kev 4B match Decider 2B on the probe and are more decisive
  (84–91% of the probability on good moves, against 71%), but die in 9 and 10 games of 10. Replaying their judged
  games: when a roomier move existed, they took the "leaves much less room" option 26% (Decider 4B) and 58% (Kev)
  of the time, against 6% for Decider 2B, and almost never stepped away from the food (0.5% and 0.2%, against 4.6%).
  They follow "closer to the food" and skip the "unless it leaves much less room" part.
* **Speed.** Per move, on average: CLM ~4 ms with judged options (after the first ticks every state and option
  vector is in its cache; ~300 ms when texts change every tick, as with facts), GLiNER 70–85 ms, Kev ~110 ms,
  Decider 2B ~145 ms, Decider 4B ~260 ms. CLM's latency medians mostly measure cache hits.
* **Composed rows are partly code.** ximing's gate hands the move to code when the model is below 0.55 confident.
  Share of moves the model chose itself: Decider 4B 67%, Decider 2B 50%, GLiNER 1B 41%, GLiNER 340M 33%. GLiNER
  340M's 39.4 is therefore mostly the fallback's. CLM stays in survival mode (97% of moves, code picks the roomiest)
  and never eats.
* Most of the best games hit the 500-step cap, so their food counts are capped too.

## 5.7 Run it

```bash
uv run python 08_snake_server.py                   # demo on http://127.0.0.1:8765, Decider 2B
uv run python 10_snake_probe.py --engine laya      # probe one model
uv run python 09_snake_benchmark.py --only judged  # 10 games
uv run python docs/snake-report/build.py           # rebuild both report versions from results/snake/
```

Pass `--engine` (5.2) to any of the three scripts. The HTTP engines need their server running first:

* **Kev 4B**: as `run_kev.sh` does, `(cd third_party/kev && uv run --extra serve python -m kev.serve --run jaredpalmer/kev-4b --port 8009)`
* **CLM 8B**: its encoder, `third_party/kev/.venv/bin/python adapters/mlx_embed_server.py --model Qwen/Qwen3-8B --port 8090`,
  then `(cd third_party/clm && CLM_DEVICE=cpu .venv/bin/clm-serve --port 8700 --emb-url http://127.0.0.1:8090/v1/embeddings --ckpt checkpoints/CLM_v0.1-8B.pt --no-download)`.
  In the demo, the page opens on "Judged, plain wording" when the model is CLM.
* **GLiNER**: `third_party/gliner2-env/.venv/bin/python adapters/gliner_systemone_server.py --port 8710` (add
  `--model fastino/GLiNER2.5-Decide-1B --port 8711` for the 1B)

Models and engines are fetched by `scripts/download_models.py` and `scripts/setup_engines.sh`.
