"""Fill docs/snake-report/template.html from results/snake/ -> docs/snake-report/index.html

  uv run python docs/snake-report/build.py
"""
import json
from pathlib import Path

R = Path("results/snake")
HERE = Path(__file__).parent
MODELS = [("decider", "Decider 2B", "var(--accent)"), ("decider-4b-v2", "Decider 4B", "var(--d4)"),
          ("kev-4b", "Kev 4B", "var(--code)"), ("clm-latest", "CLM 8B", "var(--clm)"),
          ("gliner-decide", "GLiNER 340M", "var(--gl)"), ("gliner-decide-1b", "GLiNER 1B", "color-mix(in srgb, var(--gl) 55%, var(--muted))"),
          ("laya", "Laya", "var(--muted)")]
REQS = [("grid", "Raw board"), ("relative", "Relative, in words"), ("facts", "Facts in the options (sorrycc)"),
        ("judged+state", "Judged options + heading in state"), ("judged", "Judged options, verdicts only"),
        ("judged-plain", "Judged, eating worded as 'closer'")]
NAMES = {"grid": "Raw board", "relative": "Relative, in words", "facts": "Facts in the options", "judged": "Judged options",
         "judged-plain": "Judged, plain wording", "composed": "Composed questions", "random": "random safe move", "greedy": "greedy", "greedy-safe": "greedy + dead-end check"}

probe = {m: json.load(open(R / f"probe-{m}.json"))["results"] for m, _, _ in MODELS if (R / f"probe-{m}.json").exists()}

bars, rows = [], []
for key, label in REQS:
    b = []
    for m, _, color in MODELS:
        if m in probe:
            if key not in probe[m]:
                continue
            v = probe[m][key]["hard"]["good"]
            b.append(f'<div class="bar" style="--c:{color}"><div class="track"><div class="fill" style="width:{v*100:.0f}%"></div>'
                     f'<div class="chance"></div></div><div class="val">{v*100:.0f}%</div></div>')
    bars.append(f'<div class="grp"><div class="name">{label}</div><div class="bars">{"".join(b)}</div></div>')
    cells = "".join(f'<td class="num">{probe[m][key]["all"]["good"]:.2f} / {probe[m][key]["hard"]["good"]:.2f}</td>'
                    if key in probe.get(m, {}) else "<td class='num'>–</td>" for m, _, _ in MODELS if m in probe)
    lat = probe.get("decider", {}).get(key, {}).get("all", {}).get("p50_ms")
    rows.append(f'<tr class="{"win" if key.startswith("judged") and key != "judged+state" else ""}"><td>{label}</td>{cells}'
                f'<td class="num">{f"{lat:.0f} ms" if lat else "–"}</td></tr>')

games = [json.load(open(p)) for p in sorted((R / "games").glob("*.json"))]
order = {m: i for i, (m, _, _) in enumerate(MODELS)} | {"code": 9}
fo = {k: i for i, k in enumerate(NAMES)}
games.sort(key=lambda d: (order.get(d["summary"]["engine"], 8), fo.get(d["summary"]["name"], 99)))
label = {m: l for m, l, _ in MODELS}
grows = []
for d in games:
    s = d["summary"]
    ends = {}
    for g in d["games"]:
        c = g["cause"]
        c = "starved" if c.startswith("starved") else "step cap (500)" if c == "max steps" else "died" if c.startswith(("hit", "rev")) else c
        ends[c] = ends.get(c, 0) + 1
    ended = ", ".join(f"{k} {v}" for k, v in sorted(ends.items(), key=lambda x: -x[1]))
    who = (f"{label.get(s['engine'], s['engine'])} · {NAMES[s['name']]}" if s["engine"] != "code"
           else f"code only: {NAMES[s['name']]}")
    cls = "base" if s["engine"] == "code" else "win" if s["name"] in ("judged", "judged-plain") and s["score_mean"] >= 29 else ""
    ms = [x["latency_ms"] for g in d["games"] for x in g["decisions"] if x["source"] == "model"]
    lat = f"{s['latency_p50_ms']:.0f} / {sum(ms) / len(ms):.0f} ms" if ms else "–"
    grows.append(f'<tr class="{cls}"><td>{who}</td><td class="num">{s["score_mean"]:.1f}</td><td class="num">{s["score_max"]}</td>'
                 f'<td class="num">{s["steps_mean"]:.0f}</td><td>{ended}</td><td class="num">{lat}</td></tr>')

from collections import Counter
crow = []
for d in games:
    s_ = d["summary"]
    if s_["name"] != "composed":
        continue
    c = Counter()
    for g in d["games"]:
        for x in g["decisions"]:
            h = x["how"] or ""
            c["code1" if x["source"] == "code" else "surv" if h.startswith("survival")
              else "low" if h.startswith("low confidence") else "model"] += 1
    n = sum(c.values()) or 1
    crow.append((s_["score_mean"], f'<tr><td>{label.get(s_["engine"], s_["engine"])}</td><td class="num">{s_["score_mean"]:.1f}</td>'
                + "".join(f'<td class="num">{c[k] / n:.0%}</td>' for k in ("model", "low", "surv", "code1")) + "</tr>"))
crow = [r for _, r in sorted(crow, key=lambda x: -x[0])]

best = {}
for d in games:
    s_ = d["summary"]
    if s_["engine"] == "code" or s_["name"] == "composed":
        continue
    if s_["engine"] not in best or s_["score_mean"] > best[s_["engine"]]["summary"]["score_mean"]:
        best[s_["engine"]] = d
brows = []
for m, l, _ in MODELS:
    if m not in best:
        continue
    s_ = best[m]["summary"]
    ms = [x["latency_ms"] for g in best[m]["games"] for x in g["decisions"] if x["source"] == "model"]
    died = sum(g["cause"].startswith(("hit", "rev")) for g in best[m]["games"])
    pr = probe.get(m, {}).get(s_["name"], {}).get("hard", {}).get("good")
    brows.append((s_["score_mean"], f'<tr class="{"win" if s_["score_mean"] >= 29 else ""}"><td>{l}</td><td>{NAMES[s_["name"]]}</td>'
                 f'<td class="num">{s_["score_mean"]:.1f}</td><td class="num">{s_["score_max"]}</td><td class="num">{died} of {s_["games"]}</td>'
                 f'<td class="num">{sum(ms) / len(ms):.0f} ms</td><td class="num">{f"{pr:.0%}" if pr is not None else "–"}</td></tr>'))
code = next((d["summary"] for d in games if d["summary"]["engine"] == "code" and d["summary"]["name"] == "greedy-safe"), None)
brows = [r for _, r in sorted(brows, key=lambda x: -x[0])]
if code:
    brows.append(f'<tr class="base"><td>code only</td><td>greedy + dead-end check</td><td class="num">{code["score_mean"]:.1f}</td>'
                 f'<td class="num">{code["score_max"]}</td><td class="num">{round(code["death_rate"] * code["games"])} of {code["games"]}</td>'
                 '<td class="num">–</td><td class="num">–</td></tr>')

cfg = games[0]["config"] if games else {"seeds": 10, "size": 12, "max_steps": 500}
jd = next((d["summary"]["score_mean"] for d in games if d["summary"]["engine"] == "decider" and d["summary"]["name"] == "judged"), None)
html = (HERE / "template.html").read_text()
present = [(m, l, c) for m, l, c in MODELS if m in probe]
legend = "".join(f'<span style="--c: {c}">{l}</span>' for m, l, c in present)
head = "".join(f'<th class="num">{l}</th>' for m, l, c in present)
html = (html.replace("BEST_ROWS", "\n".join(brows)).replace("COMPOSED_ROWS", "\n".join(crow)).replace("PROBE_LEGEND", legend).replace("PROBE_HEAD", head).replace("PROBE_BARS", "\n".join(bars)).replace("PROBE_ROWS", "\n".join(rows))
        .replace("GAMES_ROWS", "\n".join(grows))
        .replace("GAMES_JUDGED_DECIDER", f"{jd:.0f}" if jd else "–")
        .replace("GAMES_INTRO", f"Same {cfg['seeds']} seeds for every row, {cfg['size']}×{cfg['size']} board. A game ends on death, "
                                f"after {cfg['size'] ** 2} steps without food (starved), or at {cfg['max_steps']} steps. "
                                "Raw board and relative phrasing let the model pick fatal moves; the other requests only offer safe ones.")
        .replace("GAMES_NOTE", "Most judged, composed and greedy + dead-end games reach the 500-step cap, so their "
                               "food counts are capped too. The code baselines use the same facts the judged options are "
                               "written from, so the judged request doesn't beat code at Snake. It matches code while the "
                               "move stays a model decision, one you can steer with the strategy text."))
(HERE / "index.html").write_text(html)
print("wrote", HERE / "index.html")
