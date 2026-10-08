"""Finnish report: docs/finnish-report/template.html -> docs/finnish-report/index.html, plus the markdown twin
docs/finnish-report.md (+ docs/finnish-report/accuracy.svg) via build_md.py. Both render the same data and the same
prose (defined once, below).

  uv run python 13_finnish_report.py            # results/finnish/runs/ -> results/finnish/summary.json
  uv run python docs/finnish-report/build.py

Data: results/finnish/summary.json (13_finnish_report.py) and results/position_bias.json (11_position_bias.py).
"""
import html as H
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
SUMMARY = Path("results/finnish/summary.json")
POSBIAS = Path("results/position_bias.json")

# run name, label, page colour (CSS), SVG colour (fixed, light card)
MODELS = [("clef-flash", "Clef-flash", "var(--clef)", "#0f7b8a"),
          ("decider-4b-v2", "Decider 4B v2", "var(--d4)", "#174a26"),
          ("decider", "Decider 2B", "var(--accent)", "#2d6a3e"),
          ("kev-9b", "Kev 9B", "var(--code)", "#3450a1"),
          ("kev-4b", "Kev 4B", "color-mix(in srgb, var(--code) 60%, var(--surface))", "#7f93cf"),
          ("kev-0.8b", "Kev 0.8B", "color-mix(in srgb, var(--code) 30%, var(--surface))", "#b9c4e6"),
          ("gliner-multi-decide", "GLiNER multi", "var(--gl)", "#8a3f8c"),
          ("clm-8b", "CLM 8B", "var(--clm)", "#a8761b"),
          ("llm-qwen3.8-27b", "Qwen 3.8 27B (LLM)", "var(--muted)", "#8b9585")]
LABEL = {m: l for m, l, _, _ in MODELS}
DATASETS = [("sib", "SIB-200 topic", "7 topics", 1 / 7), ("belebele", "Belebele reading", "4 answers", 0.25),
            ("massive", "MASSIVE intent", "10 intents", 0.10), ("scandisent", "ScandiSent-fi reviews", "positive / negative", 0.5)]
PARALLEL = ["sib", "belebele", "massive"]
BIAS_LABEL = {"clef-flash": "Clef-flash", "decider": "Decider 2B", "decider-4b-v2": "Decider 4B v2", "kev-0.8b": "Kev 0.8B", "kev-4b": "Kev 4B",
              "kev-9b": "Kev 9B", "gliner-decide": "GLiNER 340M", "gliner-decide-1b": "GLiNER 1B",
              "gliner-multi-decide": "GLiNER multi", "clm-8b": "CLM 8B", "laya": "Laya", "semif": "SemIf"}

# ---- prose (markdown-lite: **bold**, *italic*, `code`, [text](url)); rendered to both versions -------------------
TITLE = "Reading Finnish"
EYEBROW = "Jev reproductions · third test · September 2026"
LEDE = ("Can the open System One models be used on Finnish text? We asked eight of them, plus Qwen 3.8 27B as a "
        "reference, the same typed questions on four datasets, 300 items each: three where the same items exist in "
        "English and Finnish, and one written in Finnish. **Cloudflare's Clef-flash (9B) is the best model in "
        "Finnish, ahead of the 27B LLM, and three more order-blind models keep their English level close to the "
        "LLM.** The worst case, that none of them understands Finnish, did not happen.")
FINDINGS = [
    "**Clef-flash is the best model in Finnish.** Averaged over the four datasets in Finnish it scores 0.928, ahead "
    "of the 27B LLM (0.907) and Decider 4B v2 (0.903); it loses only 1.8 points from English to Finnish on the same "
    "items, reads best (0.927 on Belebele in Finnish, LLM 0.863) and is well calibrated (ECE ≈ 0.03). Its option "
    "order never matters: Cloudflare's code sorts the options before building the input.",
    "**Decider 4B v2, Kev 9B and Kev 4B lose about 2 points from English to Finnish** on the same items, less than the "
    "27B LLM (3.6). Averaged over the four datasets in Finnish, Decider 4B v2 (0.903) is level with the LLM (0.907).",
    "**Decider 4B v2 is the strongest of the other models**, and reads well too: 0.903 on Belebele "
    "reading comprehension in Finnish, against the LLM's 0.863. Its model card lists Belebele as held out of training.",
    "**Kev 9B is the most language-neutral**: −1.7 points from English, and it ties the LLM on native Finnish "
    "reviews (0.947 vs 0.953). It is weaker than Decider 4B v2 on reading comprehension (0.803).",
    "**Decider 2B works in Finnish but loses ~7 points** (10 on reading comprehension and intents). It stays the most "
    "order-blind of the models that read the options together, with calibrated probabilities (ECE ≤ 0.06 in "
    "Finnish), so it still suits a confidence cascade.",
    "**The question language hardly matters.** A Finnish question is as good as an English one for every model "
    "except CLM, whose accuracy falls 11 points on average with Finnish option names (to chance on the reviews).",
    "**Small and encoder models fall behind.** GLiNER2.5-multi-Decide is fine on binary sentiment (0.89) but at "
    "chance on reading comprehension even in English; Kev 0.8B loses 13 points; CLM is not usable in Finnish.",
]
WHY = ("We only consider models whose answer doesn't depend on the order the options are listed in: majority-voting "
       "over shuffled orders would multiply the cost and remove the speed advantage over an LLM. Every model answered "
       "the 300 tweets of the sentiment test with the three options in all six orders.")
WHY_NOTE = ("GLiNER needed a fix before this test meant anything: gliner2's `Classifier` caches compiled schemas "
            "under a key that ignores label order, so a reordered label set reused the first order it had seen and "
            "every order looked identical. `adapters/gliner_systemone_server.py` now compiles each request itself. "
            "CLM's 0% is real: it embeds each option on its own. We ran the Finnish test on the models up to Kev 9B, "
            "plus GLiNER multi (the multilingual GLiNER; the English ones are English-only by design) and CLM.")
DATA_TEXT = ("Three of the datasets are **parallel**: the same items were translated into Finnish by people, so the "
             "difference between English and Finnish on identical items measures the language, not the task. "
             "ScandiSent-fi is **native** Finnish, a check that the models aren't only coping with translated text.")
COND_TEXT = ("Every item is asked in three ways, changing the language of the text and of the question (instructions, "
             "option names and descriptions). Answers are mapped back to the same gold labels.")
RESULT_TEXT = ("Everything in Finnish, accuracy on 300 items (±5 points of sampling noise). The tick on each bar is "
               "the same model's English accuracy on the same items; the dashed line is chance.")
DELTA_TEXT = ("Accuracy change from English to Finnish on the same items, with a paired bootstrap 95% interval: much "
              "tighter than the ±5 points of each score, because both sides answer the same items.")
LANG_TEXT = ("Finnish text either way; the question (instructions, option names, descriptions) in English or in "
             "Finnish. Mean over the four datasets, and the largest single-dataset change.")
CAL_TEXT = ("Expected calibration error in Finnish (lower is better): does a 0.8 answer turn out right 80% of the time? "
            "The LLM returns one label, not a distribution, so its ECE only reflects its error rate.")
ORDER_TEXT = ("Belebele's correct answers are spread over A–D, which gives a free option-order check in Finnish: an "
              "order-blind model is level across the four positions (±~10 points with ~75 items per position).")
TRAINING_TEXT = [
    "**Decider 4B v2** lists \"MASSIVE (multilingual)\" in its training mixture and marks massive-en-US as trained. Our "
    "items are from the test split and the card says evaluation rows were de-duplicated against training rows, but for "
    "Decider MASSIVE is a trained task, not zero-shot. **Belebele** is on its list of datasets kept out of training.",
    "**Kev**'s card names banking77, BoolQ and AG News (English) among its \"ten trained public sources\"; none of "
    "the four sets here is named. SIB-200 (FLORES sentences) and ScandiSent are not listed for any model.",
]
LIMITS = ("300 items per dataset give ±5 points per score, so read single-dataset differences of a few points as noise; "
          "the paired English → Finnish changes are tighter. The Finnish question wording is ours "
          "(`finnish_questions.py`), and three of the four datasets are translations from English, which can make them "
          "easier than native Finnish. Every model ran zero-shot, as released. Latency is not reported: the laptop GPU "
          "was shared during the runs and the LLM ran on another machine, so this test compares accuracy only. The same "
          "question dict went to every model; GLiNER does better on Belebele with the answers as option names instead of "
          "A–D (0.38–0.42 on 60 items) but stays far below the others.")
FOOTER = ("Code: `adapters/export_finnish.py` (the four datasets), `finnish_questions.py` (the questions in both "
          "languages), `12_finnish_benchmark.py`, `13_finnish_report.py`, `llm_choice.py` (the LLM reference over any "
          "OpenAI-compatible server), `adapters/position_bias.py` + `11_position_bias.py` (option order). Local models on "
          "an Apple M5 with 32 GB; Qwen 3.8 27B (FP8) on a vLLM server.")


def inline_html(s):
    s = H.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", s)


def load():
    if not SUMMARY.exists():
        sys.exit("no results/finnish/summary.json: run 13_finnish_report.py")
    summary = json.loads(SUMMARY.read_text())
    posbias = json.loads(POSBIAS.read_text()) if POSBIAS.exists() else {}
    present = [m for m in MODELS if m[0] in summary]
    return {"summary": summary, "posbias": posbias, "models": present}


# ---- the tables, as rows of plain strings (shared by both versions) ---------------------------------------------
def acc(s, m, key):
    v = s[m].get(key)
    return v["accuracy"] if v else None


def mean_delta(s, m):
    ds = [s[m][f"{d}/fi"]["delta_vs_en"][0] for d in PARALLEL if "delta_vs_en" in s[m].get(f"{d}/fi", {})]
    return sum(ds) / len(ds) if ds else None


def headline_rows(data):
    s, rows = data["summary"], []
    for m, l, _, _ in data["models"]:
        cells = [f"{acc(s, m, f'{d}/fi'):.3f}" for d, *_ in DATASETS]
        md = mean_delta(s, m)
        rows.append({"model": m, "cells": [l, *cells, f"{md * 100:+.1f}" if md is not None else "–"]})
    return rows


def bias_rows(data):
    pb = data["posbias"]
    out = []
    for m, v in sorted(pb.items(), key=lambda kv: kv[1]["tweets_whose_answer_flips"]):
        p = v["pick_share_by_position"]
        a = v["accuracy_by_correct_position"]
        pref = ("favours the first option" if v["pick_chi2_p"] < 0.05 and p["1"] > p["3"]
                else "favours the last option" if v["pick_chi2_p"] < 0.05 else "no")
        out.append({"model": m, "flip": v["tweets_whose_answer_flips"], "cells": [
            BIAS_LABEL.get(m, m), f"{v['tweets_whose_answer_flips']:.1%}",
            f"{p['1']:.0%} / {p['2']:.0%} / {p['3']:.0%}", f"{a['1']:.2f} / {a['2']:.2f} / {a['3']:.2f}",
            f"{v['pick_chi2_p']:.2g}", pref]})
    return out


def full_rows(data):
    s, rows = data["summary"], []
    for m, l, _, _ in data["models"]:
        cells = [l]
        for d, *_ in DATASETS:
            for c in ("en", "fi-en", "fi"):
                if d == "scandisent" and c == "en":
                    continue
                a = acc(s, m, f"{d}/{c}")
                cells.append(f"{a:.3f}" if a is not None else "–")
        rows.append(cells)
    return rows


def delta_rows(data):
    s, rows = data["summary"], []
    for m, l, _, _ in data["models"]:
        cells = [l]
        for d in PARALLEL:
            v = s[m].get(f"{d}/fi", {}).get("delta_vs_en")
            cells.append(f"{v[0] * 100:+.1f} [{v[1] * 100:+.1f}, {v[2] * 100:+.1f}]" if v else "–")
        rows.append(cells)
    return rows


def lang_rows(data):
    s, rows = data["summary"], []
    for m, l, _, _ in data["models"]:
        diffs = [(acc(s, m, f"{d}/fi") - acc(s, m, f"{d}/fi-en"), name) for d, name, *_ in DATASETS]
        mean = sum(x for x, _ in diffs) / len(diffs)
        big = max(diffs, key=lambda x: abs(x[0]))
        fe = sum(acc(s, m, f"{d}/fi-en") for d, *_ in DATASETS) / 4
        fi = sum(acc(s, m, f"{d}/fi") for d, *_ in DATASETS) / 4
        rows.append([l, f"{fe:.3f}", f"{fi:.3f}", f"{mean * 100:+.1f}", f"{big[0] * 100:+.1f} ({big[1]})"])
    return rows


def cal_rows(data):
    s = data["summary"]
    return [[l] + [f"{s[m][f'{d}/fi']['ece']:.3f}" for d, *_ in DATASETS] for m, l, _, _ in data["models"]]


def order_rows(data):
    s, rows = data["summary"], []
    for m, l, _, _ in data["models"]:
        pos = s[m].get("belebele_by_position", {}).get("fi")
        if pos:
            rows.append([l] + [f"{pos[p]:.2f}" for p in "ABCD"])
    return rows


DATA_ROWS = [["[SIB-200](https://huggingface.co/datasets/Davlan/sib200)", "topic of a FLORES sentence", "7 topics", "parallel, human translation", "CC-BY-SA-4.0"],
             ["[Belebele](https://huggingface.co/datasets/facebook/belebele)", "reading comprehension: passage, question, four answers", "4 answers", "parallel, human translation", "CC-BY-SA-4.0"],
             ["[MASSIVE](https://huggingface.co/datasets/mteb/amazon_massive_intent)", "what a voice-assistant user wants (10 of the 60 intents, 30 each)", "10 intents", "parallel, human localisation", "CC-BY-4.0"],
             ["[ScandiSent-fi](https://huggingface.co/datasets/TurkuNLP/finbenchv2-scandisent-fi-mini)", "Trustpilot reviews written in Finnish, balanced", "positive / negative", "native Finnish", "see card"]]
COND_ROWS = [["en", "English", "English", "the English score on the same items (parallel sets only)"],
             ["fi-en", "Finnish", "English", "one English question dict for every language"],
             ["fi", "Finnish", "Finnish", "everything in Finnish"]]
EXAMPLE = """{
  "state": "Fissiopommi toimii periaatteella, että ...",
  "questions": {"q": {
    "type": "choice",
    "instructions": "Mikä on tämän tekstin aihe?",
    "criteria": {
      "tiede/teknologia": "tiede, tutkimus, teknologia tai tekniikka",
      "matkailu":         "matkustaminen, turismi, nähtävyydet ja liikkuminen matkailijana",
      "politiikka":       "hallinto, vaalit, lait ja kansainväliset suhteet",
      "urheilu":          "urheilu, urheilijat, ottelut ja kilpailut",
      "terveys":          "terveys, lääketiede, sairaudet ja keho",
      "viihde":           "elokuvat, musiikki, televisio, julkkikset, pelit ja taide",
      "maantiede":        "maat, maisemat, ilmasto, luonto ja paikat maapallolla"
    }}}
}"""


# ---- HTML ---------------------------------------------------------------------------------------------------------
def tbl(head, rows, num_from=1, classes=None):
    ths = "".join(f'<th class="{"num" if i >= num_from else ""}">{H.escape(h)}</th>' for i, h in enumerate(head))
    trs = []
    for n, r in enumerate(rows):
        cls = (classes or [""] * len(rows))[n]
        tds = "".join(f'<td class="{"num" if i >= num_from else ""}">{inline_html(str(c))}</td>' for i, c in enumerate(r))
        trs.append(f'<tr class="{cls}">{tds}</tr>')
    return f'<div class="tbl"><table><thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>'


def chart(data):
    s = data["summary"]
    groups = []
    for d, name, opts, chance in DATASETS:
        bars = []
        for m, l, c, _ in data["models"]:
            fi = acc(s, m, f"{d}/fi")
            en = acc(s, m, f"{d}/en")
            tick = f'<div class="en" style="left:{en * 100:.1f}%" title="English {en:.3f}"></div>' if en is not None else ""
            bars.append(f'<div class="bar" style="--c:{c}"><div class="track"><div class="fill" style="width:{fi * 100:.1f}%"></div>'
                        f'{tick}<div class="chance" style="left:{chance * 100:.1f}%"></div></div><div class="val">{fi * 100:.0f}%</div></div>')
        groups.append(f'<div class="grp"><div class="name">{name}<br><span class="muted">{opts}</span></div><div class="bars">{"".join(bars)}</div></div>')
    legend = "".join(f'<span style="--c: {c}">{l}</span>' for m, l, c, _ in data["models"])
    legend += '<span class="tick">English, same items</span><span class="dash">chance</span>'
    return (f'<div class="chart"><div class="legend">{legend}</div>{"".join(groups)}'
            '<div class="axis"><div></div><div><span>0%</span><span>50%</span><span>100%</span></div></div></div>')


def html(data):
    head_rows = headline_rows(data)
    best = {"clef-flash", "decider-4b-v2", "kev-9b", "kev-4b"}
    fr = [f'<li><span class="n">{i}</span><p>{inline_html(f)}</p></li>' for i, f in enumerate(FINDINGS, 1)]
    ds_head = ["Model"] + [n for _, n, *_ in DATASETS]
    full_head = ["Model"] + [f"{n.split()[0]} {c}" for d, n, *_ in DATASETS for c in ("en", "fi-en", "fi")
                             if not (d == "scandisent" and c == "en")]
    bias = bias_rows(data)
    return ((HERE / "template.html").read_text()
            .replace("TITLE", TITLE).replace("EYEBROW", EYEBROW).replace("LEDE", inline_html(LEDE))
            .replace("FINDINGS", "\n".join(fr))
            .replace("HEADLINE_TABLE", tbl(ds_head + ["EN → FI, same items"], [r["cells"] for r in head_rows],
                                           classes=["win" if r["model"] in best else "base" if r["model"].startswith("llm") else ""
                                                    for r in head_rows]))
            .replace("WHY_TEXT", inline_html(WHY)).replace("WHY_NOTE", inline_html(WHY_NOTE))
            .replace("BIAS_TABLE", tbl(["Model", "Answers that flip", "Picks 1st / 2nd / 3rd", "Accuracy when right answer is 1st / 2nd / 3rd",
                                        "χ² p", "Prefers a position?"], [r["cells"] for r in bias],
                                       classes=["win" if r["flip"] < 0.07 else "bad" if r["cells"][-1] != "no" else "" for r in bias]))
            .replace("DATA_TEXT", inline_html(DATA_TEXT))
            .replace("DATA_TABLE", tbl(["Dataset", "What", "Options", "English / Finnish", "License"], DATA_ROWS, num_from=99))
            .replace("COND_TEXT", inline_html(COND_TEXT))
            .replace("COND_TABLE", tbl(["Condition", "Text", "Question", "What it measures"], COND_ROWS, num_from=99))
            .replace("EXAMPLE", H.escape(EXAMPLE))
            .replace("RESULT_TEXT", inline_html(RESULT_TEXT)).replace("CHART", chart(data))
            .replace("DELTA_TEXT", inline_html(DELTA_TEXT))
            .replace("DELTA_TABLE", tbl(["Model"] + [n for d, n, *_ in DATASETS if d in PARALLEL], delta_rows(data)))
            .replace("LANG_TEXT", inline_html(LANG_TEXT))
            .replace("LANG_TABLE", tbl(["Model", "EN question", "FI question", "Mean change", "Largest change"], lang_rows(data)))
            .replace("CAL_TEXT", inline_html(CAL_TEXT)).replace("CAL_TABLE", tbl(ds_head, cal_rows(data)))
            .replace("ORDER_TEXT", inline_html(ORDER_TEXT))
            .replace("ORDER_TABLE", tbl(["Model", "A", "B", "C", "D"], order_rows(data)))
            .replace("FULL_TABLE", tbl(full_head, full_rows(data)))
            .replace("TRAINING", "\n".join(f"<p>{inline_html(t)}</p>" for t in TRAINING_TEXT))
            .replace("LIMITS", inline_html(LIMITS)).replace("FOOTER", inline_html(FOOTER)))


if __name__ == "__main__":
    data = load()
    (HERE / "index.html").write_text(html(data))
    print("wrote", HERE / "index.html")
    sys.path.insert(0, str(HERE))
    import build_md
    build_md.main(data)
