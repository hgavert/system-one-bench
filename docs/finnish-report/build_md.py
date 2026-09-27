"""Markdown twin of the Finnish report page: docs/finnish-report.md + docs/finnish-report/accuracy.svg.

Called by docs/finnish-report/build.py with the same data and prose as docs/finnish-report/index.html.
"""
from pathlib import Path

from build import (CAL_TEXT, COND_ROWS, COND_TEXT, DATA_ROWS, DATA_TEXT, DATASETS, DELTA_TEXT, EXAMPLE, FINDINGS,
                   FOOTER, LANG_TEXT, LEDE, LIMITS, ORDER_TEXT, PARALLEL, RESULT_TEXT, TITLE, TRAINING_TEXT, WHY,
                   WHY_NOTE, acc, bias_rows, cal_rows, delta_rows, full_rows, headline_rows, lang_rows, order_rows)

OUT_MD = Path("docs/finnish-report.md")
OUT_SVG = Path("docs/finnish-report/accuracy.svg")


def svg_chart(data):
    s, models = data["summary"], data["models"]
    bar, gap, left, width, right = 11, 3, 190, 440, 50
    group_h = len(models) * (bar + gap) + 26
    W = left + width + right
    items, x, ly = [], 16, 16                              # legend, wrapped to the card width (~7.5 px per character)
    for m, l, _, col in models + [(None, "English, same items", None, "tick"), (None, "chance", None, "dash")]:
        step = 15 + int(7.5 * len(l)) + 18
        if x + step > W - 16:
            x, ly = 16, ly + 20
        items.append((l, col, x, ly))
        x += step
    legend_h = ly + 30
    H = legend_h + len(DATASETS) * group_h + 36
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" rx="8" fill="#f9faf4" stroke="#d6dbcb"/>']
    for l, col, x, ly in items:
        if col == "tick":
            out.append(f'<rect x="{x + 4}" y="{ly - 2}" width="3" height="14" fill="#1c2419"/>')
        elif col == "dash":
            out.append(f'<line x1="{x + 5}" y1="{ly - 2}" x2="{x + 5}" y2="{ly + 12}" stroke="#5d6857" stroke-dasharray="3 2"/>')
        else:
            out.append(f'<rect x="{x}" y="{ly}" width="10" height="10" rx="2" fill="{col}"/>')
        out.append(f'<text x="{x + 15}" y="{ly + 9}" fill="#1c2419">{l}</text>')
    y = legend_h
    for d, name, opts, chance in DATASETS:
        out.append(f'<text x="16" y="{y + 14}" fill="#1c2419" font-weight="600">{name}</text>'
                   f'<text x="16" y="{y + 29}" fill="#5d6857">{opts}</text>')
        by = y + 4
        for m, l, _, col in models:
            fi, en = acc(s, m, f"{d}/fi"), acc(s, m, f"{d}/en")
            out.append(f'<rect x="{left}" y="{by}" width="{width}" height="{bar}" rx="2" fill="#e6e9df"/>'
                       f'<rect x="{left}" y="{by}" width="{max(fi * width, 1.5):.1f}" height="{bar}" rx="2" fill="{col}"/>'
                       f'<text x="{left + width + 8}" y="{by + bar - 1}" fill="#5d6857">{fi * 100:.0f}%</text>')
            if en is not None:
                out.append(f'<rect x="{left + en * width - 1.5:.1f}" y="{by - 2}" width="3" height="{bar + 4}" fill="#1c2419"/>')
            by += bar + gap
        cx = left + chance * width
        out.append(f'<line x1="{cx:.1f}" y1="{y + 1}" x2="{cx:.1f}" y2="{by}" stroke="#5d6857" stroke-dasharray="3 2"/>')
        y += group_h
    for frac, t in ((0, "0%"), (0.5, "50%"), (1, "100%")):
        out.append(f'<text x="{left + frac * width}" y="{y + 10}" fill="#5d6857" text-anchor="middle">{t}</text>')
    out.append(f'<text x="16" y="{y + 10}" fill="#5d6857">accuracy, all in Finnish</text>')
    out.append("</svg>")
    return "\n".join(out)


def table(header, rows, align=None):
    align = align or ["---"] + ["--:"] * (len(header) - 1)
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
                     + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"


def main(data):
    OUT_SVG.write_text(svg_chart(data))
    md = []
    w = md.append
    names = [n for _, n, *_ in DATASETS]

    w(f"# {TITLE}\n")
    w("> Generated from the same data as the interactive version, [`docs/finnish-report/index.html`](finnish-report/index.html), "
      "by `docs/finnish-report/build.py`. Every number per dataset and condition: "
      "[results/finnish/REPORT.md](../results/finnish/REPORT.md).\n")
    w(LEDE + "\n")

    w("## What we found\n")
    w("\n".join(f"{i}. {f}" for i, f in enumerate(FINDINGS, 1)) + "\n")

    w("## Results at a glance\n")
    w("Everything in Finnish, accuracy on 300 items per dataset; the last column is the mean change from English to "
      "Finnish on the same SIB, Belebele and MASSIVE items, in points.\n")
    rows = []
    for r in headline_rows(data):
        c = list(r["cells"])
        if r["model"] in ("decider-4b-v2", "kev-9b", "kev-4b"):
            c[0] = f"**{c[0]}**"
        elif r["model"].startswith("llm"):
            c = [f"*{x}*" for x in c]
        rows.append(c)
    w(table(["Model", *names, "EN → FI, same items"], rows))
    w("Decider was trained on MASSIVE's training split, so that column isn't zero-shot for Decider (see "
      "[Training data](#training-data)). Chance: 0.14 / 0.25 / 0.10 / 0.50.\n")

    w("## First filter: option order\n")
    w(WHY + "\n")
    w(table(["Model", "Answers that flip", "Picks 1st / 2nd / 3rd", "Accuracy when right answer is 1st / 2nd / 3rd",
             "χ² p", "Prefers a position?"], [r["cells"] for r in bias_rows(data)],
            ["---", "--:", "--:", "--:", "--:", "---"]))
    w(f"> {WHY_NOTE}\n")

    w("## The test\n")
    w(DATA_TEXT + "\n")
    w(table(["Dataset", "What", "Options", "English / Finnish", "License"], DATA_ROWS, ["---"] * 5))
    w(COND_TEXT + "\n")
    w(table(["Condition", "Text", "Question", "What it measures"], [[f"`{r[0]}`", *r[1:]] for r in COND_ROWS], ["---"] * 4))
    w("Every engine gets the same Jev request. A SIB-200 item in the all-Finnish condition:\n")
    w(f"```json\n{EXAMPLE}\n```\n")
    w("Belebele sends the passage as the state, its question inside the instructions, and the four answers as options "
      "A–D. The reference LLM gets the same instructions and options in its system prompt, the text as the user "
      "message, and must answer with one option name (JSON-schema enum, thinking off).\n")

    w("## Finnish, dataset by dataset\n")
    w(RESULT_TEXT + "\n")
    w("![Accuracy in Finnish per dataset and model, with each model's English accuracy on the same items](finnish-report/accuracy.svg)\n")

    w("## How much Finnish costs\n")
    w(DELTA_TEXT + "\n")
    w(table(["Model"] + [n for d, n, *_ in DATASETS if d in PARALLEL], delta_rows(data)))

    w("## Does the question have to be in Finnish?\n")
    w(LANG_TEXT + "\n")
    w(table(["Model", "EN question", "FI question", "Mean change", "Largest change"], lang_rows(data)))

    w("## Calibration in Finnish\n")
    w(CAL_TEXT + "\n")
    w(table(["Model", *names], cal_rows(data)))

    w("## Option order in Finnish\n")
    w(ORDER_TEXT + "\n")
    w(table(["Model", "A", "B", "C", "D"], order_rows(data)))

    w("## Training data\n")
    w("\n\n".join(TRAINING_TEXT) + "\n")

    w("## All conditions\n")
    w("Accuracy per dataset and condition: **en** = English text and question; **fi-en** = Finnish text, English "
      "question; **fi** = everything in Finnish. Macro-F1 per cell: [results/finnish/REPORT.md](../results/finnish/REPORT.md).\n")
    head = ["Model"] + [f"{n.split()[0]} {c}" for d, n, *_ in DATASETS for c in ("en", "fi-en", "fi")
                        if not (d == "scandisent" and c == "en")]
    w(table(head, full_rows(data)))

    w("## Limits of this test\n")
    w(LIMITS + "\n")
    w("---\n")
    w(FOOTER)
    OUT_MD.write_text("\n".join(md) + "\n")
    print("wrote", OUT_MD, "and", OUT_SVG)
