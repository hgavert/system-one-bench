"""Step 12 - Test 3, Finnish: every item of data/finnish/ under each condition -> results/finnish/runs/<name>.jsonl

  uv run python adapters/export_finnish.py                                       # once: the four datasets
  uv run python 12_finnish_benchmark.py --engine decider
  uv run python 12_finnish_benchmark.py --engine decider:models/decider-4b-v2
  uv run python 12_finnish_benchmark.py --engine http:http://127.0.0.1:8712,gliner-multi-decide
  zsh -ic 'uv run python 12_finnish_benchmark.py --engine llm --workers 8'        # Leviathan, key from the shell env
  uv run python 13_finnish_report.py

Conditions (finnish_questions.py): en = English text and question (parallel sets only), fi-en = Finnish text with the
English question, fi = all Finnish. One line per (dataset, condition, item); an interrupted run resumes where it
stopped. Latency is recorded but not a result here (the laptop GPU may be shared, and the LLM runs on another
machine): Test 3 compares accuracy.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from finnish_questions import CONDITIONS, conditions_for, request
from snake.engine import engine_tag, make_engine

DATASETS = ["sib", "belebele", "massive", "scandisent"]

ap = argparse.ArgumentParser()
ap.add_argument("--engine", required=True, help="decider | decider:<dir> | laya | http:<url>,<model> | llm")
ap.add_argument("--name", help="result name (default: from the engine)")
ap.add_argument("--only", help="comma-separated datasets")
ap.add_argument("--conditions", default=",".join(CONDITIONS), help="comma-separated: en,fi-en,fi")
ap.add_argument("--workers", type=int, default=1, help="parallel requests (the LLM; local engines run one at a time)")
args = ap.parse_args()

if args.engine == "llm":
    from llm_choice import LLMChoiceEngine
    engine = LLMChoiceEngine()
    name = args.name or "llm-" + engine.model.replace("/", "_")
else:
    engine = make_engine(args.engine)
    name = args.name or engine_tag(args.engine)
out_path = Path(f"results/finnish/runs/{name}.jsonl")
out_path.parent.mkdir(parents=True, exist_ok=True)
done = set()
if out_path.exists():
    done = {(r["dataset"], r["condition"], r["id"]) for r in map(json.loads, out_path.open())}

jobs = []
for ds in args.only.split(",") if args.only else DATASETS:
    for item in map(json.loads, open(f"data/finnish/{ds}.jsonl")):
        for cond in conditions_for(item):
            if cond in args.conditions.split(",") and (ds, cond, item["id"]) not in done:
                jobs.append((ds, cond, item))
print(f"{engine.name}: {len(jobs)} requests to go ({len(done)} done) -> {out_path}", file=sys.stderr)


def run(job):
    ds, cond, item = job
    req, back = request(ds, item, cond)
    q_lang = CONDITIONS[cond][1]
    answers, ms, _ = engine.ask(req, lang=q_lang) if args.engine == "llm" else engine.ask(req)
    probs = {back[k]: float(v) for k, v in answers["q"]["probabilities"].items()}
    return {"dataset": ds, "condition": cond, "id": item["id"], "gold": item["gold"],
            "pred": max(probs, key=probs.get), "probs": probs, "latency_ms": round(ms, 1)}


with out_path.open("a") as out, ThreadPoolExecutor(args.workers) as pool:
    for n, row in enumerate(pool.map(run, jobs), 1):
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        if n % 100 == 0 or n == len(jobs):
            out.flush()
            print(f"  {name}: {n}/{len(jobs)}", file=sys.stderr, flush=True)
