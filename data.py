"""Dataset loading: TweetEval sentiment (SemEval-2017 Task 4A).

Short, informal social-media messages with human-annotated sentiment:
0 = negative, 1 = neutral, 2 = positive.
https://huggingface.co/datasets/cardiffnlp/tweet_eval
"""
from dataclasses import dataclass

from datasets import load_dataset

LABELS = ["negative", "neutral", "positive"]


@dataclass
class Example:
    text: str
    label: str  # one of LABELS
    row: int = -1  # row in the TweetEval split, so results can refer to a tweet without storing its text


def load_sample(n_per_class: int = 100, split: str = "test", seed: int = 42) -> list[Example]:
    """Return a class-balanced, shuffled, reproducible sample.

    The raw test split is skewed (~48% neutral). Balancing makes accuracy easier to read:
    a model that always says "neutral" scores 33%, not 48%.
    """
    ds = load_dataset("cardiffnlp/tweet_eval", "sentiment", split=split)
    ds = ds.add_column("row", list(range(len(ds)))).shuffle(seed=seed)   # same permutation as before
    picked: list[Example] = []
    counts = {i: 0 for i in range(len(LABELS))}
    for row in ds:
        if counts[row["label"]] < n_per_class:
            counts[row["label"]] += 1
            picked.append(Example(text=row["text"], label=LABELS[row["label"]], row=row["row"]))
        if all(c == n_per_class for c in counts.values()):
            break
    return picked


if __name__ == "__main__":
    for ex in load_sample(n_per_class=3):
        print(f"{ex.label:>8}  {ex.text}")
