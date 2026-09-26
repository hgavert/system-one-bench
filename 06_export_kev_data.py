"""Step 6a - Export the Laya fine-tuning tweets as Kev training data (JSONL).

Kev's trainer reads one API request per line plus a `label` on each question. We export the
exact same tweets 03_finetune_laya.py used (3,000 train, 300 validation), with the exact same
question definition, so the Laya and Kev fine-tunes are directly comparable.

Run:  uv run python 06_export_kev_data.py   ->  data/kev/train.jsonl, data/kev/val.jsonl
"""
import json
from pathlib import Path

from data import load_sample
from laya_classifier import SENTIMENT_QUESTION

OUT = Path("data/kev")


def write(path: Path, examples) -> None:
    with path.open("w") as f:
        for ex in examples:
            f.write(json.dumps({"state": ex.text,
                                "questions": {"sentiment": {**SENTIMENT_QUESTION, "label": ex.label}}},
                               ensure_ascii=False) + "\n")
    print(f"{path}: {len(examples)} records")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "train.jsonl", load_sample(1000, split="train"))
    write(OUT / "val.jsonl", load_sample(100, split="validation"))
