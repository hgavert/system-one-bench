"""Step 3 - Fine-tune Laya on TweetEval's *train* split, then re-run the benchmark.

Laya's model card is explicit: the base checkpoint is "a fast base to specialise, not a
zero-shot decision engine". Specialising it is cheap - a few thousand labelled tweets and a
few minutes on a laptop GPU. The test tweets used by 02_benchmark.py are never seen here.

Run:  uv run python 03_finetune_laya.py
      uv run python 02_benchmark.py --laya-model ./models/laya-tweet-sentiment --tag finetuned
"""
import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import save_file

import laya
from laya.common import QTYPES, build_sequence, collate_items, temp_bucket

from data import LABELS, load_sample
from laya_classifier import SENTIMENT_QUESTION

OUT = Path("models/laya-tweet-sentiment")


def encode(agent, examples):
    """Turn (text, label) pairs into Laya's input layout, with a one-hot target per option."""
    q = agent._to_internal(SENTIMENT_QUESTION)
    items = []
    for ex in examples:
        ids, markers = build_sequence(agent.tok, ex.text, q, max_len=256)
        target = [0.0] * len(LABELS)
        target[LABELS.index(ex.label)] = 1.0
        items.append({"ids": ids, "markers": markers, "qtype": QTYPES["choice"], "target": target})
    return items


def forward(agent, batch):
    keys = ("input_ids", "attention_mask", "marker_pos", "marker_mask", "qtype")
    logits, _act = agent.model(*(batch[k].to(agent.device) for k in keys))
    return logits[:, : len(LABELS)]


@torch.no_grad()
def val_logits(agent, items, bs=64):
    agent.model.eval()
    out, gold = [], []
    for i in range(0, len(items), bs):
        b = collate_items([items[i:i + bs]], agent.tok.pad_token_id)
        out.append(forward(agent, b).float().cpu())
        gold.append(b["target"].argmax(-1))
    return torch.cat(out), torch.cat(gold)


def fit_temperature(logits, gold):
    """Pick the temperature that minimises validation NLL -> calibrated probabilities."""
    grid = np.arange(0.5, 5.01, 0.05)
    nll = [F.cross_entropy(logits / t, gold).item() for t in grid]
    return float(grid[int(np.argmin(nll))])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-class", type=int, default=1000, help="training tweets per class")
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-5)
    args = ap.parse_args()
    random.seed(0); torch.manual_seed(0)

    agent = laya.load("convaiinnovations/laya")
    print(f"device: {agent.device}")
    train = encode(agent, load_sample(args.n_per_class, split="train"))
    val = encode(agent, load_sample(100, split="validation"))
    print(f"train {len(train)} / val {len(val)} examples")

    logits, gold = val_logits(agent, val)
    print(f"before: val accuracy {(logits.argmax(-1) == gold).float().mean():.3f}")

    opt = torch.optim.AdamW(agent.model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * math.ceil(len(train) / args.batch_size)
    warmup = max(1, steps // 10)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min((s + 1) / warmup, max(0.0, (steps - s) / (steps - warmup))))

    step, t0 = 0, time.time()
    for epoch in range(args.epochs):
        random.shuffle(train)
        agent.model.train()
        for i in range(0, len(train), args.batch_size):
            b = collate_items([train[i:i + args.batch_size]], agent.tok.pad_token_id)
            loss = F.cross_entropy(forward(agent, b).float(), b["target"].argmax(-1).to(agent.device))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(agent.model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1
            if step % 25 == 0 or step == steps:
                print(f"  epoch {epoch + 1} step {step}/{steps}  loss {loss.item():.3f}  "
                      f"{time.time() - t0:.0f}s", flush=True)

    logits, gold = val_logits(agent, val)
    temp = fit_temperature(logits, gold)
    print(f"after:  val accuracy {(logits.argmax(-1) == gold).float().mean():.3f}, "
          f"fitted temperature {temp:.2f}")

    # Save in the same layout as the Hugging Face checkpoint, so laya.load(OUT) just works.
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = dict(agent.cfg)
    cfg["temperature_by_options"] = {**cfg.get("temperature_by_options", {}),
                                     temp_bucket(QTYPES["choice"], len(LABELS)): temp}
    cfg["training"] = {"fine_tuned_from": "convaiinnovations/laya", "dataset": "tweet_eval/sentiment",
                       "examples": len(train), **vars(args)}
    (OUT / "rl_agent_config.json").write_text(json.dumps(cfg, indent=2))
    save_file({k: v.detach().cpu().contiguous() for k, v in agent.model.state_dict().items()},
              str(OUT / "model.safetensors"))
    agent.tok.save_pretrained(OUT / "tokenizer")
    agent.model.encoder.config.save_pretrained(OUT / "encoder")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
