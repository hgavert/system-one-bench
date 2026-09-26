"""Markdown twin of the Snake report page: docs/snake-report.md + docs/snake-report/probe.svg.

Called by docs/snake-report/build.py with the same data as docs/snake-report/index.html, so the two never disagree.
The prose mirrors template.html; edit both when a finding changes.
"""
from pathlib import Path

from build import LABEL, MODELS, NAMES, REQS, GAMES_NOTE, best_rows, ended_text, games_intro, who

OUT_MD = Path("docs/snake-report.md")
OUT_SVG = Path("docs/snake-report/probe.svg")
# fixed colours on a light card: GitHub shows an SVG image as-is in both of its themes
COLOR = {"decider": "#2d6a3e", "decider-4b-v2": "#174a26", "kev-4b": "#3450a1", "clm-latest": "#a8761b",
         "gliner-decide": "#8a3f8c", "gliner-decide-1b": "#b98cba", "laya": "#8b9585"}


def svg_chart(probe):
    present = [(m, l) for m, l, _ in MODELS if m in probe]
    bar, gap, left, width, right = 11, 3, 250, 420, 50
    group_h = len(present) * (bar + gap) + 22
    W = left + width + right
    items, x, ly = [], 16, 16                              # legend, wrapped to the card width (~7.5 px per character)
    for m, l in present + [(None, "chance")]:
        step = 15 + int(7.5 * len(l)) + 18
        if x + step > W - 16:
            x, ly = 16, ly + 20
        items.append((m, l, x, ly))
        x += step
    legend_h = ly + 30
    H = legend_h + len(REQS) * group_h + 36
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" rx="8" fill="#f9faf4" stroke="#d6dbcb"/>']
    for m, l, x, ly in items:
        if m is None:
            out.append(f'<line x1="{x + 5}" y1="{ly - 2}" x2="{x + 5}" y2="{ly + 12}" stroke="#5d6857" stroke-dasharray="3 2"/>'
                       f'<text x="{x + 15}" y="{ly + 9}" fill="#5d6857">{l}</text>')
        else:
            out.append(f'<rect x="{x}" y="{ly}" width="10" height="10" rx="2" fill="{COLOR[m]}"/>'
                       f'<text x="{x + 15}" y="{ly + 9}" fill="#1c2419">{l}</text>')
    y = legend_h
    for key, label in REQS:
        out.append(f'<text x="16" y="{y + 14}" fill="#1c2419" font-weight="600">{label}</text>')
        by = y + 4
        for m, l in present:
            if key in probe[m]:
                v = probe[m][key]["hard"]["good"]
                out.append(f'<rect x="{left}" y="{by}" width="{width}" height="{bar}" rx="2" fill="#e6e9df"/>'
                           f'<rect x="{left}" y="{by}" width="{max(v * width, 1.5):.1f}" height="{bar}" rx="2" fill="{COLOR[m]}"/>'
                           f'<text x="{left + width + 8}" y="{by + bar - 1}" fill="#5d6857">{v * 100:.0f}%</text>')
            by += bar + gap
        cx = left + width / 2
        out.append(f'<line x1="{cx}" y1="{y + 1}" x2="{cx}" y2="{by}" stroke="#5d6857" stroke-dasharray="3 2"/>')
        y += group_h
    for frac, t in ((0, "0%"), (0.5, "50%"), (1, "100%")):
        tx = left + frac * width
        out.append(f'<text x="{tx}" y="{y + 10}" fill="#5d6857" text-anchor="middle">{t}</text>')
    out.append(f'<text x="16" y="{y + 10}" fill="#5d6857">good pick, hard states</text>')
    out.append("</svg>")
    return "\n".join(out)


def table(header, rows, align=None):
    align = align or ["---"] * len(header)
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"


def main(data):
    probe = data["probe"]
    OUT_SVG.write_text(svg_chart(probe))
    present = [(m, l) for m, l, _ in MODELS if m in probe]
    md = []
    w = md.append

    w("# Asking for a Snake Move\n")
    w("> Generated from the same data as the interactive version, [`docs/snake-report/index.html`](snake-report/index.html), "
      "by `docs/snake-report/build.py`. Key code and details: [docs/5-snake.md](5-snake.md).\n")
    w("People posted Jev playing Snake. We read how six of those demos phrase each move, then asked the same questions of "
      "seven open System One models on a laptop, zero-shot, 10 games each. **The fast, straight-to-the-food videos rely on "
      "code for the geometry.** Asked to read the board themselves, every model is poor at it, and so is Jev. Given one "
      "verdict per option, five of the seven play well, but each one needs the wording to suit it.\n")

    w("## What we found\n")
    w("1. **The simple way fails, for Jev and for every open model.** The only published numbers of Jev playing (nadeem4's "
      "arena) are 1.8 food per game against 17.3 for a few lines of greedy code; it circled until it starved. On the raw "
      "board, five of the six models we tried it on died within about 9 steps in every game; with nadeem4's phrasing or "
      "sorrycc's facts they circled and starved. Only Kev 4B partly reads the board (13.1 food with nadeem4's phrasing), "
      "and it still dies every game.")
    w("2. **The demos that look good move the spatial work into code**: filtering out fatal moves, flood-fill facts, "
      "confidence gates, or a waypoint pathfinder that steers every tick while Jev only picks a target every 2.6 seconds. "
      "CLM's own game demo does the same.")
    w("3. **What works: one verdict per option, and nothing else in the state.** Code writes \"moves closer to the food; "
      "keeps the most room\" into each option. For five models the best such request picks a good single move 95–99% of "
      "the time (90–100% on the hard states below). Two things had broken them: numbers they would have to compare "
      "across options, and direction words in the state (`heading: up`) that pull them to go straight.")
    w("4. **The wording has to suit the model.** CLM and GLiNER 340M give any option that says \"eats the food\" almost no "
      "probability, so they circle next to the food. Worded as \"moves closer to the food\", CLM goes from 0 to 36.2 food "
      "per game and GLiNER from 2.7 to 26.3. For the others it makes little difference (Decider 2B −2.0, Kev 4B −4.2, "
      "Decider 4B +1.5).")
    w("5. **Better single moves don't mean longer games.** Decider 4B and Kev 4B are more decisive than Decider 2B and "
      "follow \"closer to the food\" almost literally, into tight spaces: they die in 9 and 10 of 10 games, Decider 2B in "
      "2. With 36.9 food per game, the 2B is the best model that decides every move itself, close to the best code "
      "baseline (41.1).")
    w("6. **Speed varies 60-fold.** CLM answers in ~4 ms once its cache is warm (10 games in 16 s), GLiNER in 70–80 ms, "
      "Kev in ~110, Decider 2B in ~145 and Decider 4B in ~260. Adding ximing's extra questions roughly doubles the time, "
      "and on those rows code chooses up to two moves in three (below).\n")

    w("## Best result per model\n")
    w("Each model's best request among those where the model decides every move (so not \"composed\", where code steps in "
      "when the model is unsure). 10 games each, 12×12 board, 500-step cap.\n")
    rows = []
    for r in best_rows(data):
        pr = probe.get(r["engine"], {}).get(r["name"], {}).get("hard", {}).get("good")
        rows.append([f"**{LABEL[r['engine']]}**" if r["score_mean"] >= 29 else LABEL[r["engine"]], NAMES[r["name"]],
                     f"{r['score_mean']:.1f}", r["score_max"], f"{r['died']} of {r['games']}",
                     f"{r['latency_mean_ms']:.0f} ms", f"{pr:.0%}" if pr is not None else "–"])
    code = next((r for r in data["rows"] if r["engine"] == "code" and r["name"] == "greedy-safe"), None)
    if code:
        rows.append(["*code only*", "*greedy + dead-end check*", f"*{code['score_mean']:.1f}*", f"*{code['score_max']}*",
                     f"*{code['died']} of {code['games']}*", "–", "–"])
    w(table(["Model", "Best request", "Food / game", "Best game", "Died", "Per move", "Probe, hard states"], rows,
            ["---", "---", "--:", "--:", "--:", "--:", "--:"]))

    w("## Who decides what, in each published demo\n")
    w("Every demo sends the same Jev request: a `state` plus one typed `choice` question per tick. What differs is how "
      "much has already been decided by code before the model sees the options. From model-reads-the-board to "
      "code-does-the-pathing:\n")
    w(table(["Demo", "State sent", "Options", "Code decides"], [
        ["[iammusham](https://github.com/iammusham/jev-snake)", "coordinates, body, walls, danger cells (JSON)",
         "`UP` \"Move one cell in negative y\", ×4", "nothing"],
        ["[nadeem4](https://github.com/nadeem4/jev-demo)", "\"food: 3 cells ahead and 2 to your right\", \"if_you_turn_left: "
         "clear for 4 cells, then the wall\"", "`TURN_LEFT` `STRAIGHT` `TURN_RIGHT`", "nothing (Jev: 1.8 food / game)"],
        ["[coderhh](https://github.com/coderhh/jev-snake)", "text grid, heading", "only non-fatal directions",
         "fatal-move filter; override for Laya"],
        ["[sorrycc](https://github.com/sorrycc/typesafe-snake)", "text grid, head, food, heading",
         "safe directions with facts: \"food is 8 steps away after this move; 141 of 141 empty cells stay reachable\"",
         "filter, flood fill"],
        ["[ximing](https://github.com/ximing/jev-snake-game)", "grid + per-candidate facts",
         "move choice, danger score, survival noul, safe + progress noul per direction", "filter, thresholds + fallbacks"],
        ["[StevanusPangau](https://github.com/StevanusPangau/jev-snake)", "snapshot + waypoints",
         "`food` / `open_area` / `border_loop`", "every tick: greedy pathing + BFS seatbelt"],
    ]))

    w("## One decision, known answer\n")
    w("Games mix many effects, so we first asked for single moves on fixed situations where code knows the good moves: not "
      "a dead end, and as close to the food as any non-dead-end move. The chart shows the **hard** set, 100 states where "
      "going straight is legal but wrong. Chance is about 50%.\n")
    w("![Good picks on hard states, per request and model](snake-report/probe.svg)\n")
    rows = []
    for key, label in REQS:
        lat = probe.get("decider", {}).get(key, {}).get("all", {}).get("p50_ms")
        cells = [f"{probe[m][key]['all']['good']:.2f} / {probe[m][key]['hard']['good']:.2f}" if key in probe[m] else "–"
                 for m, _ in present]
        bold = key in ("judged", "judged-plain")
        rows.append([f"**{label}**" if bold else label] + cells + [f"{lat:.0f} ms" if lat else "–"])
    w(table(["Request"] + [l for _, l in present] + ["Decider 2B latency"], rows,
            ["---"] + ["--:"] * (len(present) + 1)))
    w("Cells: good pick on all 150 states / on the 100 hard states. Kev 4B is the only model that reads the raw board (93%) "
      "and isn't distracted by the heading. Laya, a 421M encoder, stays below chance on the hard states with every "
      "request, and in games it never gets going (0–0.5 food).\n")

    w("## The two things that break a small model\n")
    w("**Numbers that must be compared across options.** sorrycc's options carry exact numbers. Decider 2B picks the good "
      "move 67% of the time. Adding the rule \"take the move after which the food is the fewest steps away\" to the "
      "instruction lifts that to 82%. Writing the comparison into each option lifts it to 98–99%, whether as words "
      "(\"moves closer to the food\") or as a before→after number (\"distance changes from 9 to 8\").\n")
    w("**Direction words in the state.** With `heading: up` and \"the food is 5 down and 5 right\" in the context, Decider "
      "went straight on 43% of the hard states, even when the straight option read \"moves away from the food\". With the "
      "state removed: 0%. Renaming the options from `up/down/left/right` to `move 1/2/3` changed nothing. It's the context "
      "that pulls.\n")
    w("sorrycc's facts, as Decider reads them (67% good):\n")
    w("```text\nContext:\n{\"board\": [..12 rows..], \"legend\": \"H = snake head, ...\",\n \"head\": {\"row\": 4, \"col\": 9}, "
      "\"food\": {\"row\": 8, \"col\": 4},\n \"heading\": \"right\", \"snake_length\": 3, ...}\n\nQuestion: You are playing "
      "the game Snake. Choose the direction ... Player strategy: Stay alive and eat food.\nOptions:\n(A) up: left turn, "
      "head moves to row 3 col 9; food is 10 steps away after this move; 141 of 141 empty cells stay reachable; can still "
      "follow its own tail out\n(B) down: right turn, head moves to row 5 col 9; food is 8 steps away after this move; "
      "141 of 141 ...\n(C) right: straight, head moves to row 4 col 10; food is 10 steps away after this move; 141 of 141 "
      "...\nAnswer: (\n```\n")
    w("Judged options, same situation (99% good):\n")
    w("```text\nContext:\nChoose the best move for the snake.\n\nQuestion: Snake game: pick the next move. Every listed "
      "move is safe for this step. Never take a DEAD END. Prefer a move that eats the food or moves closer to it, unless "
      "it leaves much less room than another move. Player strategy: Stay alive and eat food.\nOptions:\n(A) up: moves "
      "away from the food; keeps the most room\n(B) down: moves closer to the food; keeps the most room\n(C) right: "
      "moves away from the food; keeps the most room\nAnswer: (\n```\n")
    w("Decider scores the logits of the letters `A`, `B`, `C` right after the final `(` and applies its temperature (1.3). "
      "Nothing is generated. Code has done the geometry: which moves survive, distance before and after, flood-fill "
      "room, dead ends. The model's remaining job is to weigh the verdicts against the instruction and the player's "
      "strategy text. That's also the only step that responds to natural language.\n")

    w("## CLM 8B: a bi-encoder reads options differently\n")
    w("[CLM](https://github.com/Contrastive-LM/CLM) (Contrastive-LM, 24 September) serves the same `/v1/systemone` API but "
      "works differently: a frozen Qwen3-8B embeds the state + question and each option *separately*, trained heads "
      "project both into one space, and the answer is a softmax over cosines. On this Mac, Qwen3-8B runs on MLX in place "
      "of vLLM (`adapters/mlx_embed_server.py`). Three consequences in Snake:\n")
    w("- **Identical option texts get identical probabilities.** Two moves that both read \"moves away from the food; keeps "
      "the most room\" score exactly the same (0.293 each). An option can't see the others, so nothing can be compared "
      "across options. Only the verdict text written into each one counts.")
    w("- **It has a blind spot for \"eats\".** On 80 states where one move eats the food, CLM picked it 0% of the time with "
      "every wording tried: \"eats the food\", \"reaches the food\", \"moves onto the food\", \"moves closer to the food "
      "and eats it\". With the eating move described as \"moves closer to the food; keeps the most room\" (true: the "
      "distance drops to 0), 97%. Its judged games went from 0 food (all starved) to 36.2.")
    w("- **It's nearly free once warm.** With judged options the state is a fixed sentence and the verdicts come from a "
      "handful of strings, so after the first ticks every vector is cached: ~4 ms per move on average, 10 games in 16 s. "
      "With changing texts (facts in the options) a call costs ~300 ms here, mostly the 8B encoder.\n")
    w("CLM's own game demo, [T-Rex runner vs Jev](https://github.com/Contrastive-LM/CLM/tree/main/examples/t_rex), phrases "
      "moves the same way: a physics planner labels each action, as in `jump: Safe. Clears the 2 large cacti. Best.`, and "
      "a shield replaces unsafe answers. With that help both models survive every course, but CLM agreed with the planner "
      "on 66% of decisions (4,883 shield interventions) and Jev on 99% (28).\n")

    w("## Decider 4B and GLiNER\n")
    w("Three more models from the sentiment tutorial, zero-shot as released: **Decider 4B v2** (Qwen3.5-4B, the best "
      "sentiment model here at 75.0%) and **GLiNER2.5-Decide** at 340M and 1B (DeBERTa-style encoders that pack the "
      "question and every label into one prompt). GLiNER runs in its own environment behind a small `/v1/systemone` "
      "adapter (`adapters/gliner_systemone_server.py`), using gliner2's `Classifier` API so every option gets a "
      "probability. It rejects \"(\" in option text, so the adapter writes braces instead.\n")
    w("- **Decider 4B isn't distracted by the heading** (judged + heading: 99% / 100%, where the 2B drops to 57% on hard "
      "states) and puts 91% of the probability on good moves. In games it's the greedier player: when a roomier move "
      "existed it took the \"leaves much less room\" option 26% of the time (Decider 2B 6%, Kev 4B 58%). It's also about "
      "twice as slow: ~260 ms per move.")
    w("- **GLiNER shares CLM's blind spot for \"eats\".** GLiNER 340M picks 93% good moves in the probe but ate 2.7 per game "
      "with judged options, starving every time. With the eating move worded \"moves closer to the food\", 26.3. Both "
      "score option text by matching; neither reasons over it.")
    w("- **The composed rows are mostly the code's work.** ximing's gate hands the move to code when the model is under "
      "0.55 confident, so the flatter a model's probabilities, the more code plays:\n")
    rows = [[LABEL.get(r["engine"], r["engine"]), f"{r['score_mean']:.1f}"] + [f"{r['split'][k]:.0%}" for k in ("model", "low", "surv", "code1")]
            for r in sorted((r for r in data["rows"] if "split" in r), key=lambda r: -r["score_mean"])]
    w(table(["Composed questions", "Food / game", "Model's choice", "Code: model unsure", "Code: survival mode",
             "Code: one safe move"], rows, ["---"] + ["--:"] * 5))
    w("GLiNER 340M's 39.4 food is the best model row, but code chose two moves in three, close to what code alone scores "
      "(41.1). CLM answers the danger and survival questions as if the snake were always in trouble, so the gate stays in "
      "survival mode, always takes the roomiest move, and never eats. That 0 is for this request only: composed is built "
      "on the original judged wording (\"eats the food\"). CLM's own best is **judged, plain wording: 36.2 food at ~4 ms "
      "per move** (CLM section above).\n")

    w("## Full games\n")
    w(games_intro(data["config"]) + "\n")
    rows = []
    for r in data["rows"]:
        lat = f"{r['latency_p50_ms']:.0f} / {r['latency_mean_ms']:.0f} ms" if r["latency_mean_ms"] is not None else "–"
        name = who(r)
        if r["engine"] == "code":
            name = f"*{name}*"
        elif r["name"] in ("judged", "judged-plain") and r["score_mean"] >= 29:
            name = f"**{name}**"
        rows.append([name, f"{r['score_mean']:.1f}", r["score_max"], f"{r['steps_mean']:.0f}", ended_text(r), lat])
    w(table(["Controller", "Food / game", "Best", "Steps", "Ended by", "Per move, p50 / mean"], rows,
            ["---", "--:", "--:", "--:", "---", "--:"]))
    w(f"> {GAMES_NOTE}\n")

    w("## The request that works\n")
    w("Sent once per tick when at least two moves survive; with one safe move, code takes it without calling the model.\n")
    w("```json\n{\n  \"state\": \"Choose the best move for the snake.\",\n  \"questions\": {\"move\": {\n    \"type\": \"choice\",\n"
      "    \"instructions\": \"Snake game: pick the next move. Every listed move is safe for this step. Never take a DEAD END. "
      "Prefer a move that eats the food or moves closer to it, unless it leaves much less room than another move. Player "
      "strategy: Stay alive and eat food.\",\n    \"criteria\": {\n      \"up\":    \"moves away from the food; keeps the most "
      "room\",\n      \"down\":  \"moves closer to the food; keeps the most room\",\n      \"right\": \"moves away from the "
      "food; keeps the most room\"\n    }}}\n}\n```\n")
    w("Verdicts come from `snake/formulations.py` (`judge()`): *eats the food* / *moves closer* / *moves away*, then *DEAD "
      "END* (flood fill smaller than the snake and no way to follow the tail), *keeps the most room*, *keeps almost as much "
      "room* (≥ 80%), or *leaves much less room (n of m cells)*. For CLM and GLiNER 340M, use the plain wording, which "
      "describes the eating move as \"moves closer to the food; keeps the most room\".\n")

    w("## Limits of this test\n")
    w("We had no TypeSafe API key, so hosted Jev is represented only by nadeem4's published run (10 games, 10×10, relative "
      "phrasing, starvation after 60 steps without food). That setup differs from ours (12×12, 144 steps), so compare the "
      "1.8 with our rows only loosely. Every model runs zero-shot, as released. The probe's \"good move\" only checks food "
      "distance and dead ends, not room, which is why it misses the 4B models' habit of chasing food into tight spaces. On "
      "composed rows, code chooses a third to two thirds of the moves. Ten seeds per row give wide intervals, so read "
      "differences of a few food as noise, and most of the best games hit the 500-step cap.\n")
    w("---\n")
    w("Code: `snake/`, `08_snake_server.py` (live demo with the decision panel), `09_snake_benchmark.py`, "
      "`10_snake_probe.py`; write-up in [docs/5-snake.md](5-snake.md). Models: Decider 2B v10 and 4B v2 (PyTorch MPS), "
      "Kev 4B (MLX server), CLM 8B (MLX encoder + CPU heads), GLiNER2.5-Decide 340M and 1B (MPS, own environment), Laya "
      "(MPS), all on an Apple M5 with 32 GB.")
    OUT_MD.write_text("\n".join(md) + "\n")
    print("wrote", OUT_MD, "and", OUT_SVG)
