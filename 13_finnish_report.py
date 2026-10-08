"""Step 13 - Test 3 report: results/finnish/runs/*.jsonl -> results/finnish/REPORT.md and summary.json

  uv run python 13_finnish_report.py

Per model, dataset and condition: accuracy, macro-F1, ECE. For the parallel sets, the change from English to
Finnish on the same items (fi-en - en, fi - en) with a paired bootstrap 95% interval. For Belebele, accuracy by
where the correct answer is listed (A-D): an option-order check in Finnish, for free.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

DATASETS = {"sib": "SIB-200 topic (7)", "belebele": "Belebele reading (4)", "massive": "MASSIVE intent (10)",
            "scandisent": "ScandiSent-fi (2)"}
CONDS = ["en", "fi-en", "fi"]
COND_NAME = {"en": "EN text, EN question", "fi-en": "FI text, EN question", "fi": "FI text, FI question"}
NAMES = {"jev": "Jev (hosted, jev-1.13.0)", "clef-flash": "Clef-flash", "decider-4b-v2": "Decider 4B v2", "decider": "Decider 2B", "kev-9b": "Kev 9B", "kev-4b": "Kev 4B",
         "kev-0.8b": "Kev 0.8B", "gliner-multi-decide": "GLiNER2.5-multi-Decide", "gliner-decide": "GLiNER2.5-Decide (340M)",
         "gliner-decide-1b": "GLiNER2.5-Decide-1B", "laya": "Laya", "clm-8b": "CLM 8B",
         "llm-qwen3.8-27b": "LLM Qwen 3.8 27B (Leviathan)"}


def macro_f1(rows):
    labels = {r["gold"] for r in rows}
    f1s = []
    for l in labels:
        tp = sum(r["pred"] == l and r["gold"] == l for r in rows)
        fp = sum(r["pred"] == l and r["gold"] != l for r in rows)
        fn = sum(r["pred"] != l and r["gold"] == l for r in rows)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1s) / len(f1s)


def ece(rows, bins=10):
    b = defaultdict(list)
    for r in rows:
        conf = max(r["probs"].values())
        b[min(int(conf * bins), bins - 1)].append((conf, r["pred"] == r["gold"]))
    return sum(abs(sum(c for c, _ in v) / len(v) - sum(h for _, h in v) / len(v)) * len(v) for v in b.values()) / len(rows)


def paired_delta(a, b, n_boot=2000, seed=0):
    """a, b: {id: correct} on the same items -> (b - a, low, high)"""
    ids = sorted(set(a) & set(b))
    d = [b[i] - a[i] for i in ids]
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n_boot))
    return sum(d) / len(d), boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot)]


runs = {}
order = list(NAMES)                                       # table order: as listed in NAMES, unknown runs last
for path in sorted(Path("results/finnish/runs").glob("*.jsonl"),
                   key=lambda p: (order.index(p.stem) if p.stem in order else len(order), p.stem)):
    rows = [json.loads(l) for l in path.open()]
    by = defaultdict(list)
    for r in rows:
        by[(r["dataset"], r["condition"])].append(r)
    runs[path.stem] = by

summary, md = {}, ["# Test 3: Finnish", "",
                   "300 items per dataset, zero-shot. SIB-200, Belebele and MASSIVE are parallel: the same items in "
                   "English and in Finnish. ScandiSent-fi is native Finnish (no English version). Accuracy; ±5 points "
                   "of sampling noise on 300 items, much less on the paired English → Finnish differences.", ""]

# accuracy table
head = "| Model | " + " | ".join(f"{DATASETS[d].split(' (')[0]} {c}" for d in DATASETS for c in CONDS if not (d == "scandisent" and c == "en")) + " |"
md += ["## Accuracy", "", "Conditions: " + "; ".join(f"**{c}** = {COND_NAME[c]}" for c in CONDS) + ".", "", head,
       "|---|" + "--:|" * (head.count("|") - 2)]
for name, by in runs.items():
    summary[name] = {}
    cells = []
    for d in DATASETS:
        for c in CONDS:
            if d == "scandisent" and c == "en":
                continue
            rows = by.get((d, c))
            if not rows:
                cells.append("–")
                continue
            acc = sum(r["pred"] == r["gold"] for r in rows) / len(rows)
            summary[name][f"{d}/{c}"] = {"n": len(rows), "accuracy": acc, "macro_f1": macro_f1(rows), "ece": ece(rows)}
            cells.append(f"{acc:.3f}")
    md.append(f"| {NAMES.get(name, name)} | " + " | ".join(cells) + " |")
md += ["", "Chance: SIB 0.14 (most frequent topic 0.24), Belebele 0.25, MASSIVE 0.10, ScandiSent 0.50.", "",
       "**Training data.** Decider 4B v2's card lists \"MASSIVE (multilingual)\" in its training mixture (train split; "
       "our items are from the test split, and the card says evaluation rows were de-duplicated against training rows), "
       "and marks massive-en-US as trained for the Decider family: for Decider, MASSIVE is a trained task, not "
       "zero-shot. Belebele is on the card's list of datasets kept out of training. SIB-200 (FLORES) and ScandiSent "
       "are not listed.", ""]

# English -> Finnish on the same items
md += ["## English → Finnish on the same items", "",
       "Accuracy change from the English condition, paired by item, with a bootstrap 95% interval.", "",
       "| Model | Dataset | FI text, EN question | FI text, FI question |", "|---|---|--:|--:|"]
for name, by in runs.items():
    for d in ("sib", "belebele", "massive"):
        if not by.get((d, "en")):
            continue
        base = {r["id"]: r["pred"] == r["gold"] for r in by[(d, "en")]}
        cells = []
        for c in ("fi-en", "fi"):
            if not by.get((d, c)):
                cells.append("–")
                continue
            delta, lo, hi = paired_delta(base, {r["id"]: r["pred"] == r["gold"] for r in by[(d, c)]})
            summary[name][f"{d}/{c}"]["delta_vs_en"] = [delta, lo, hi]
            cells.append(f"{delta:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        md.append(f"| {NAMES.get(name, name)} | {DATASETS[d]} | " + " | ".join(cells) + " |")

# macro-F1 / ECE
md += ["", "## Macro-F1 and calibration (ECE)", "", "ECE is not meaningful for the LLM (one label, all probability on it).", "",
       "| Model | Dataset | Condition | Accuracy | Macro-F1 | ECE |", "|---|---|---|--:|--:|--:|"]
for name, s in summary.items():
    for key, v in s.items():
        d, c = key.split("/")
        md.append(f"| {NAMES.get(name, name)} | {DATASETS[d]} | {c} | {v['accuracy']:.3f} | {v['macro_f1']:.3f} | {v['ece']:.3f} |")

# Belebele: accuracy by the position of the correct answer
md += ["", "## Option order in Finnish (Belebele)", "",
       "Accuracy by where the correct answer is listed. An order-blind model is level across A-D (±~10 points of noise "
       "with ~75 items per position).", "", "| Model | Condition | A | B | C | D |", "|---|---|--:|--:|--:|--:|"]
for name, by in runs.items():
    for c in CONDS:
        rows = by.get(("belebele", c))
        if not rows:
            continue
        pos = {p: [r["pred"] == r["gold"] for r in rows if r["gold"] == p] for p in "ABCD"}
        summary[name].setdefault("belebele_by_position", {})[c] = {p: sum(v) / len(v) for p, v in pos.items()}
        md.append(f"| {NAMES.get(name, name)} | {c} | " + " | ".join(f"{sum(v) / len(v):.2f}" for v in pos.values()) + " |")

Path("results/finnish/REPORT.md").write_text("\n".join(md) + "\n")
Path("results/finnish/summary.json").write_text(json.dumps(summary, indent=1))
print("\n".join(md[:len(runs) + 14]))
print("\nsaved results/finnish/REPORT.md, results/finnish/summary.json")
