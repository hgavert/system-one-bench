"""Test 3 data: four Finnish datasets, 300 seeded items each -> data/finnish/<dataset>.jsonl

  uv run python adapters/export_finnish.py

Three are parallel, the same items in English and Finnish (human-translated), so English vs Finnish on identical
items isolates the language from the task; one is native Finnish:

  sib        SIB-200 topic classification (FLORES sentences), 7 topics       Davlan/sib200 eng_Latn / fin_Latn
  belebele   Belebele reading comprehension, 4 answers                        facebook/belebele eng_Latn / fin_Latn
  massive    MASSIVE voice-assistant intents, 10 intents x 30 utterances      mteb/amazon_massive_intent en / fi
  scandisent ScandiSent-fi, native Finnish Trustpilot reviews, pos / neg      TurkuNLP/finbenchv2-scandisent-fi-mini

One line per item: {"id", "gold", "en": {...} | null, "fi": {...}} with "text" (and for Belebele "question" and
"answers"). Gold labels are the canonical ids in finnish_questions.py. The text is not redistributed (data/ is
gitignored); results refer to items by id.
"""
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from datasets import concatenate_datasets, load_dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from finnish_questions import MASSIVE_INTENTS

N, SEED = 300, 17
OUT = Path("data/finnish")
OUT.mkdir(parents=True, exist_ok=True)


def write(name, items):
    with open(OUT / f"{name}.jsonl", "w") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"{name}: {len(items)} items")


def sib():
    def all_splits(cfg):
        d = load_dataset("Davlan/sib200", cfg)
        return {r["index_id"]: r for r in concatenate_datasets([d[s] for s in d])}
    en, fi = all_splits("eng_Latn"), all_splits("fin_Latn")
    ids = sorted(set(en) & set(fi), key=int)
    assert all(en[i]["category"] == fi[i]["category"] for i in ids)
    ids = random.Random(SEED).sample(ids, N)          # zero-shot, so all 1,004 items are fair game; natural class mix
    return [{"id": f"sib{i}", "gold": en[i]["category"], "en": {"text": en[i]["text"]}, "fi": {"text": fi[i]["text"]}}
            for i in ids]


def belebele():
    def rows(cfg):
        return {(r["link"], r["question_number"]): r for r in load_dataset("facebook/belebele", cfg, split="test")}
    en, fi = rows("eng_Latn"), rows("fin_Latn")
    keys = sorted(set(en) & set(fi))
    assert all(en[k]["correct_answer_num"] == fi[k]["correct_answer_num"] for k in keys)
    keys = random.Random(SEED).sample(keys, N)
    side = lambda r: {"text": r["flores_passage"], "question": r["question"],
                      "answers": [r[f"mc_answer{n}"] for n in range(1, 5)]}
    return [{"id": f"bb{n:03d}", "source": list(k), "gold": "ABCD"[int(en[k]["correct_answer_num"]) - 1],
             "en": side(en[k]), "fi": side(fi[k])} for n, k in enumerate(keys)]


def massive():
    def rows(cfg):
        return {r["id"]: r for r in load_dataset("mteb/amazon_massive_intent", cfg, split="test")}
    en, fi = rows("en"), rows("fi")
    by_intent = defaultdict(list)
    for i in sorted(set(en) & set(fi), key=int):
        if en[i]["label"] in MASSIVE_INTENTS:
            assert en[i]["label"] == fi[i]["label"]
            by_intent[en[i]["label"]].append(i)
    rng, per = random.Random(SEED), N // len(MASSIVE_INTENTS)
    ids = [i for intent in MASSIVE_INTENTS for i in rng.sample(by_intent[intent], per)]
    rng.shuffle(ids)
    return [{"id": f"ms{i}", "gold": en[i]["label"], "en": {"text": en[i]["text"]}, "fi": {"text": fi[i]["text"]}}
            for i in ids]


def scandisent():
    d = load_dataset("TurkuNLP/finbenchv2-scandisent-fi-mini", split="test")
    rng, items = random.Random(SEED), []
    for label in ("negative", "positive"):                # balanced, like the tweets
        idx = rng.sample([n for n, r in enumerate(d) if r["label"] == label], N // 2)
        items += [{"id": f"ss{n:04d}", "gold": label, "en": None, "fi": {"text": d[n]["text"]}} for n in idx]
    rng.shuffle(items)
    return items


for name, fn in [("sib", sib), ("belebele", belebele), ("massive", massive), ("scandisent", scandisent)]:
    write(name, fn())
