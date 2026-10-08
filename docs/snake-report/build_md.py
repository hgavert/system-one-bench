"""Markdown twin of the Snake report page: docs/snake-report.md + docs/snake-report/probe.svg.

Called by docs/snake-report/build.py with the same data as docs/snake-report/index.html, so the two never disagree.
The prose mirrors template.html; edit both when a finding changes.
"""
from pathlib import Path

from build import keyword_rows, LABEL, MODELS, NAMES, REQS, GAMES_NOTE, best_rows, ended_text, games_intro, who

OUT_MD = Path("docs/snake-report.md")
OUT_SVG = Path("docs/snake-report/probe.svg")
# fixed colours on a light card: GitHub shows an SVG image as-is in both of its themes
COLOR = {"jev": "#1f2937", "clef-flash": "#0f7b8a", "decider": "#2d6a3e", "decider-4b-v2": "#174a26", "kev-4b": "#3450a1", "clm-latest": "#a8761b",
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
    w('People posted Jev playing Snake. We read how six of those demos phrase each move, then put the same requests to eight open System One models on one laptop and to hosted Jev, zero-shot, 10 games per model and request. **The fast, straight-to-the-food videos rely on code for the geometry.** Asked to play from the board itself, every model fails, Jev included, although Jev and Clef-flash read single positions well. Given one verdict per option, Jev, Clef-flash and five other models play well, each with wording that suits it. And once the options carry verdicts, seven keyword rules with no model play about as well as any of them.\n')

    w("## What we found\n")
    w("1. **The simple way fails, for Jev and for the open models.** The only published numbers of Jev playing (nadeem4's arena) are 1.8 food per game against 17.3 for a few lines of greedy code; it circled until it starved, and hosted Jev does the same here with that phrasing (82% right turns, starved in 10 of 10). On the raw board every model dies in every game. Reading a single position is easier: hosted Jev picks a good move on 97% of the hard raw-board states, Clef-flash on 85% and Kev 4B on 79%, but none of them turns that into a game.")
    w("2. **The demos that look good move the spatial work into code**: filtering out fatal moves, flood-fill facts, confidence gates, or a waypoint pathfinder that steers every tick while Jev only picks a target every 2.6 seconds. CLM's own game demo does the same.")
    w('3. **What works: one verdict per option, and nothing else in the state.** Code writes "moves closer to the food; keeps the most room" into each option. For five open models the best such request picks a good single move 95–99% of the time (90–100% on the hard states). Three things had broken them: numbers to compare across options, direction words in the state, and, for two models, the word "eats".')
    w('4. **The wording has to suit the model.** CLM 8B and GLiNER 340M give any option that says "eats the food" almost no probability, so they circle next to the food. Worded as "moves closer to the food", CLM goes from 0 to 36.2 food per game and GLiNER from 2.7 to 26.3. For the other models it makes little difference.')
    w('5. **Hosted Jev is the best player, Clef-flash the best open one.** With judged options Jev eats 40.6 food per game and Clef-flash 39.3, neither dying once in 10 games, against 41.1 for the best code baseline. Decider 4B and Kev 4B follow "closer to the food" into tight spaces and die in 9 and 10 of 10 games; Decider 2B (36.9) in 2. Only Jev also plays well from sorrycc\'s facts in the options (37.3; the open models 0.5–17.2).')
    w("6. **Speed varies over 100-fold.** CLM answers in ~4 ms once its cache is warm (10 games in 16 s), GLiNER in 70–80 ms, Kev in ~110, Decider 2B in ~145, Decider 4B in ~260 and Clef-flash in ~520 ms per move on the laptop; hosted Jev in ~270 ms including the network round trip. ximing's extra questions roughly double that, and on those rows code picks up to two moves in three.")
    w("7. **A table of phrases does about as well.** Once each option carries a verdict, adding up points for seven phrases, with no model at all, picks a good move on 100% of the hard states and eats 39.0 food per game without dying, between Clef-flash (39.3) and Jev (40.6). In Snake the model doesn't need to be smart: code has already done the understanding when it wrote the options.\n")

    w("## The models\n")
    w("All zero-shot, as released: the same models as in the sentiment benchmark. Every one answers the same Jev request, "
      "`{state, questions}`, and returns a probability per option. They differ in how they read it, which turns out to "
      "matter here.\n")
    w(table(["Model", "How it reads the request", "Runs here as", "Sentiment"], [
        ["Jev (hosted)", "TypeSafe's own System One model, closed weights; the reference the others reproduce (jev-1.13.0, run by Rami Luisto)", "TypeSafe API over the network (`jev_client.py`); latency includes the round trip", "73.7%"],
        ["Clef-flash", "Cloudflare's post-trained Qwen3.5-9B: a joint schema head reads the final hidden states and scores the options of all questions together; options are sorted before encoding", "own environment, `/v1/systemone` adapter (PyTorch MPS)", "59.7%"],
        ["Decider 2B", "Qwen3.5-2B fine-tune: state, question and lettered options in one sequence; answer from the letter logits",
         "in-process, PyTorch MPS", "74.0%"],
        ["Decider 4B v2", "the same, on Qwen3.5-4B", "in-process, PyTorch MPS", "75.0%"],
        ["Kev 4B", "LoRA on Qwen3.5-4B-Base; a pointer head scores each option's end token",
         "its own `/v1/systemone` server (MLX)", "63.7%"],
        ["CLM 8B", "bi-encoder: frozen Qwen3-8B embeds state + question and each option *separately*; softmax over cosines",
         "`clm-serve`, Qwen3-8B on MLX", "51.7%"],
        ["GLiNER 340M", "GLiNER2.5-Decide, a DeBERTa-v3-large schema encoder: question and all labels packed before the text",
         "own environment, `/v1/systemone` adapter", "63.7%"],
        ["GLiNER 1B", "GLiNER2.5-Decide-1B, the larger variant", "own environment, `/v1/systemone` adapter", "63.0%"],
        ["Laya", "ModernBERT-large encoder (421M) with a `[MASK]` marker per option", "in-process, PyTorch MPS", "63.3%"],
    ], ["---", "---", "---", "--:"]))
    w("Sentiment: zero-shot accuracy on 300 tweets, from the companion benchmark ([sentiment-report.md](sentiment-report.md)). "
      "Laya played games on two requests only (facts and judged options); it can't play with either.\n")

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

    w("## How the published demos ask\n")
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

    w("## Six ways of asking\n")
    w("Four requests reproduce published demos; two are written here from what the probe below showed. All are in "
      "`snake/formulations.py`.\n")
    w(table(["Request", "Based on", "What the model gets"], [
        ["Raw board", "iammusham, coderhh", "the board as text rows, head and food coordinates; options up / left / right, fatal ones included"],
        ["Relative, in words", "nadeem4, verbatim", "phrases about the food and what lies left, ahead and right; options `TURN_LEFT` / `STRAIGHT` / `TURN_RIGHT`"],
        ["Facts in the options", "sorrycc, verbatim", "board and heading; only safe moves, each with exact numbers (food distance, reachable cells, dead end)"],
        ["Judged options", "sorrycc's facts, rewritten", "no state; only safe moves, each with a verdict in words"],
        ["Judged, plain wording", "judged options", "the same, with the eating move worded \"moves closer to the food\""],
        ["Composed questions", "ximing", "judged options plus a danger score and a survival yes/no in one request; code combines them with thresholds"],
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
        rows.append([f"**{label}**" if key in ("judged", "judged-plain") else label] + cells + [f"{lat:.0f} ms" if lat else "–"])
    w(table(["Request"] + [l for _, l in present] + ["Decider 2B latency"], rows, ["---"] + ["--:"] * (len(present) + 1)))
    w("Cells: good pick on all 150 states / on the 100 hard states. Kev 4B is the only model that reads the raw board "
      "(93%). Laya stays below chance on the hard states with every request.\n")

    w("## What breaks the models\n")
    w("### Numbers to compare across options\n")
    w("sorrycc's options carry exact numbers, and no model does well with them when going straight is wrong (hard states: "
      "0–46%). The same facts written as a verdict in each option lift every model, and all but Laya to 72–100%. On "
      "Decider 2B, spelling the rule out in the instruction helped only partly (67% → 82% on all states); writing the "
      "comparison into each option, as words (\"moves closer to the food\") or as before→after numbers (\"distance changes "
      "from 9 to 8\"), reached 98–99%.\n")
    w("### Direction words in the state\n")
    w("Judged options with `heading: up` and \"the food is 5 down and 5 right\" in the state, against the same options with "
      "no state (hard states):\n")
    w(table(["Heading in the state?", "Decider 2B", "Decider 4B", "Kev 4B", "CLM 8B", "GLiNER 340M", "GLiNER 1B", "Laya"], [
        ["yes", "57%", "100%", "100%", "89%", "28%", "0%", "25%"],
        ["**no**", "**100%**", "**100%**", "**100%**", "**89%**", "**86%**", "**72%**", "**39%**"],
    ], ["---"] + ["--:"] * 7))
    w("The two 4B models and CLM ignore the heading; for the smaller models it pulls hard toward going straight, even when "
      "that option reads \"moves away from the food\". On Decider 2B, renaming the options from `up/down/left/right` to "
      "`move 1/2/3` changed nothing: it's the context that pulls.\n")
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
    w("Decider scores the logits of the letters `A`, `B`, `C` right after the final `(` and applies its temperature (1.3); "
      "nothing is generated. Code has done the geometry: which moves survive, distance before and after, flood-fill "
      "room, dead ends. The model weighs the verdicts against the instruction and the player's strategy text, the only "
      "step that responds to natural language.\n")
    w("### The word \"eats\"\n")
    w("Two models almost never pick an option that says \"eats the food\", so with judged options they circle next to the "
      "food until they starve:\n")
    w(table(["Food per game", "Decider 2B", "Decider 4B", "Kev 4B", "CLM 8B", "GLiNER 340M", "GLiNER 1B"], [
        ["\"eats the food\"", "36.9", "29.3", "29.5", "0.0", "2.7", "15.3"],
        ["\"moves closer to the food\"", "34.9", "30.8", "25.3", "**36.2**", "**26.3**", "13.7"],
    ], ["---"] + ["--:"] * 6))
    w("Both are models that score option text by matching it. CLM embeds each option on its own, so an option can't see "
      "the others: two options with identical text get identical probabilities. On 80 states where one move eats the food, "
      "CLM picked it 0% of the time with every wording tried (\"eats the food\", \"reaches the food\", \"moves onto the "
      "food\", \"moves closer to the food and eats it\"), and 97% once it read \"moves closer to the food; keeps the most "
      "room\", which is true, since the distance drops to 0. CLM's own game demo, "
      "[T-Rex runner vs Jev](https://github.com/Contrastive-LM/CLM/tree/main/examples/t_rex), also labels every action for "
      "the model (`jump: Safe. Clears the 2 large cacti. Best.`) and lets a shield replace unsafe answers; there CLM "
      "agreed with the planner on 66% of decisions and Jev on 99%.\n")

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
    w("### Better single moves, shorter games\n")
    w("On the probe, Decider 4B and Kev 4B match Decider 2B and are more decisive (84–91% of the probability on good moves, "
      "against 71%). In games they die far more. Replaying their judged games shows why: they follow \"closer to the food\" "
      "and skip \"unless it leaves much less room\".\n")
    w(table(["Judged options", "Took \"leaves much less room\" when a roomier move existed",
             "Took \"moves away\" when closer was on offer", "Died"], [
        ["**Decider 2B**", "6% (4 of 70)", "4.6%", "2 of 10"],
        ["Decider 4B", "26% (11 of 43)", "0.5%", "9 of 10"],
        ["Kev 4B", "58% (22 of 38)", "0.2%", "10 of 10"],
    ], ["---", "--:", "--:", "--:"]))
    w("### Speed\n")
    w("CLM is nearly free once warm: with judged options the state is a fixed sentence and the verdicts come from a handful "
      "of strings, so after the first ticks every vector is in its cache (~4 ms per move, 10 games in 16 s). With texts "
      "that change every tick (facts in the options) a call costs ~300 ms, mostly the 8B encoder. Its latency medians in "
      "the table mostly measure cache hits. The other models spend the same time on every move: GLiNER 70–80 ms, Kev "
      "~110 ms, Decider 2B ~145 ms, Decider 4B ~260 ms.\n")
    w("### Composed questions: who actually moves\n")
    w("ximing's gate hands the move to code when the model is under 0.55 confident, and switches to \"most room\" when "
      "the model reports danger. The flatter a model's probabilities, the more of the game code plays:\n")
    rows = [[LABEL.get(r["engine"], r["engine"]), f"{r['score_mean']:.1f}"] + [f"{r['split'][k]:.0%}" for k in ("model", "low", "surv", "code1")]
            for r in sorted((r for r in data["rows"] if "split" in r), key=lambda r: -r["score_mean"])]
    w(table(["Composed questions", "Food / game", "Model's choice", "Code: model unsure", "Code: survival mode",
             "Code: one safe move"], rows, ["---"] + ["--:"] * 5))
    w("GLiNER 340M's 39.4 food is the best model row, but code chose two moves in three, close to what code alone scores "
      "(41.1). CLM answers the danger and survival questions as if the snake were always in trouble, so the gate stays in "
      "survival mode, takes the roomiest move, and never eats; composed also uses the \"eats\" wording. CLM's best is "
      "judged, plain wording: 36.2 food at ~4 ms per move.\n")

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

    w("## Without a model: a keyword scorer\n")
    w("The judged options are code's facts written in a small, fixed vocabulary, so the words can be read back without a model. `KeywordEngine` (`snake/engine.py`) answers the same `{state, questions}` request: it adds up points for the phrases each option contains, then takes the top score (random tie-break) or samples from a softmax over the scores. The weights were written once and not tuned; matching ignores case." "\n")
    w(table(["Phrase in the option", "Points"], [['`eats the food`, `moves closer to the food`', '+3'], ['`moves away from the food`', '−1'], ['`keeps the most room` / `keeps almost as much room`', '+2 / +1'], ['`leaves much less room (N of M cells)`', '−2 − 2·(1 − N/M)'], ['`dead end`', '−100']], ["---", "--:"]))
    kw, kw_other = keyword_rows(data)
    w(table(["Controller", "Food / game", "Best", "Died", "Probe, hard states"],
            [[f"**{r['who']}**" if r.get("win") else f"*{r['who']}*" if r.get("ref") else r["who"],
              r["food"], r["best"], r["died"], r["probe"]] for r in kw], ["---", "--:", "--:", "--:", "--:"]))
    w('On the other requests there is nothing to match, so it plays at random among the offered moves, which is no worse than most models there. Food per game, top score: KEYWORD_OTHER.'.replace("KEYWORD_OTHER", kw_other) + "\n")
    w("### What this says\n")
    w("a) **The models don't need to be smart here.** " 'Choosing between "moves closer to the food; keeps the most room" and "moves away from the food; DEAD END" takes a few string lookups. The best billion-parameter models only match the table, and the smaller ones fall short of it for reasons that have nothing to do with Snake: the word "eats", or a heading in the state.' "\n")
    w("b) **This is how the models worked anyway.** " 'Every request that worked is one where code had already reduced the choice to reading back its own verdicts. Every request that asked for more (read a board, compare numbers across options, ignore a heading) failed. The failures look like text matching: CLM and GLiNER 340M avoid "eats" even when eating is right, and the small models follow `heading: up` towards going straight. The published demos that play well are built the same way: the geometry is done in code before the model is called.' "\n")
    w("c) **If code has to describe the world, it can often decide too.** " 'To write "moves closer to the food; keeps the most room", code already needs the distances, the flood fill and the dead-end test. The last step, from those facts to a move, is a few lines: exact, testable, and well under a millisecond. Greedy + dead-end check (41.1) is that step written directly. What a model adds is what the table ignores: the player\'s strategy text, and any wording nobody wrote a phrase for.' "\n")
    w("> " "Snake is a small closed world with a handful of cases, and code writes every word of every option, so a phrase table covers them all. Where the description is open (free text from people, many interacting factors, options nobody listed in advance), a table would not keep up, and that is where a System One model could earn its place. This test doesn't cover such cases." "\n")

    w("## Limits of this test\n")
    w("We had no TypeSafe API key, so hosted Jev is represented only by nadeem4's published run (10 games, 10×10, relative "
      "phrasing, starvation after 60 steps without food). That setup differs from ours (12×12, 144 steps), so compare the "
      "1.8 with our rows only loosely. Every model runs zero-shot, as released. The probe's \"good move\" only checks food "
      "distance and dead ends, not room, which is why it misses the 4B models' habit of chasing food into tight spaces. "
      "Some diagnostics were run on one model only: the instruction-rule and option-renaming tests (Decider 2B), the "
      "80-state \"eats\" test (CLM) and the tight-space replay (the three models shown). Ten seeds per row give wide "
      "intervals, so read differences of a few food as noise, and most of the best games hit the 500-step cap."
      " The keyword scorer shows only that Snake's judged options can be read back by rules, not that the same holds for tasks whose descriptions aren't generated by code from a fixed vocabulary." "\n")
    w("---\n")
    w("Code: `snake/`, `08_snake_server.py` (live demo with the decision panel), `09_snake_benchmark.py`, "
      "`10_snake_probe.py`, `adapters/gliner_systemone_server.py`, `adapters/mlx_embed_server.py`; write-up in "
      "[docs/5-snake.md](5-snake.md). All on an Apple M5 with 32 GB.")
    OUT_MD.write_text("\n".join(md) + "\n")
    print("wrote", OUT_MD, "and", OUT_SVG)
