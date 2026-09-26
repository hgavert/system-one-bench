# Reference · fine-tuning Laya on the tweets

> **Not part of the main comparison.** Training a general decision model on the task defeats its purpose
> (you could train a classifier on embeddings instead). Kept to show the ceiling. The main results are zero-shot:
> [doc 4](../4-zero-shot-reproductions.md).

File: [`03_finetune_laya.py`](../../03_finetune_laya.py). Log: [`results/finetune.log`](../../results/finetune.log).

The base Laya checkpoint is a *general* decision model. It was never taught what "neutral"
means on Twitter, and its confusion matrix shows it: most errors are positive/negative tweets
filed as neutral. Laya's model card says it plainly: it is "a fast base to specialise".

## 1 Data — never touch the test set

```python
train = encode(agent, load_sample(1000, split="train"))       # 3,000 tweets, balanced
val   = encode(agent, load_sample(100,  split="validation"))  # 300 tweets, for temperature
```

The benchmark only ever uses TweetEval's **test** split, so the fine-tuned model is scored
on tweets it has never seen.

## 2 Encoding = inference encoding + a target

```python
ids, markers = build_sequence(agent.tok, ex.text, q, max_len=256)
target = [0, 0, 0]; target[LABELS.index(ex.label)] = 1
items.append({"ids": ids, "markers": markers, "qtype": QTYPES["choice"], "target": target})
```

Training uses *exactly* the sequence layout that `agent.predict` builds at inference time — same
instruction, same option descriptions, same order. That's the single most important detail:
if you train on a different prompt than you serve, you lose most of the gain.

## 3 The loop

```python
logits = forward(agent, batch)                        # [batch, 3] option scores
loss = F.cross_entropy(logits, batch["target"].argmax(-1))
loss.backward(); clip_grad_norm_(…, 1.0); opt.step(); sched.step()
```

Plain full fine-tuning: AdamW, lr 1e-5, 10% linear warm-up then linear decay, batch 16,
one epoch = 188 steps. On an Apple M5 (MPS, fp32) this takes about 10 minutes.

## 4 Re-calibrate, then save in Laya's own format

```python
temp = fit_temperature(val_logits, val_gold)          # grid search 0.5–5.0 minimising NLL -> 1.25
cfg["temperature_by_options"]["choice:3-5"] = temp
save_file(agent.model.state_dict(), OUT / "model.safetensors")
agent.tok.save_pretrained(OUT / "tokenizer")
agent.model.encoder.config.save_pretrained(OUT / "encoder")
```

Fine-tuning changes how confident the model is, so the shipped temperature no longer fits.
Refitting it on held-out validation data keeps the probabilities honest (ECE drops from 0.071
to 0.048). Because we write the same directory layout as the Hugging Face checkpoint, the
result loads with the normal API:

```python
agent = laya.load("./models/laya-tweet-sentiment")
```

## 5 Result

| | val accuracy | test accuracy (benchmark) | ECE |
|---|---|---|---|
| Laya base (zero-shot) | 0.623 | 0.633 | 0.071 |
| Laya fine-tuned (3k tweets, 10 min) | 0.703 | 0.717 | 0.048 |

Speed and footprint on the M5 (PyTorch MPS, fp32, 300 test tweets):

| | Macro-F1 | p50 / p95 per tweet | Throughput | Saved model |
|---|---|---|---|---|
| Laya base | 0.639 | 49 / 59 ms | 20.5 msg/s (26.2 batched) | 840 MB (Hugging Face) |
| Laya fine-tuned | 0.711 | 49 / 66 ms | 19.7 msg/s (23.0 batched) | 1.6 GB (`models/laya-tweet-sentiment`, fp32) |

Fine-tuning doesn't change the architecture, so speed is unchanged. The saved copy is larger only
because it is stored in fp32. Confusion matrix after training (rows = truth, 100 each):
negative [87, 12, 1] · neutral [28, 52, 20] · positive [2, 22, 76].

Most of the gain comes from negative tweets (65 → 87 of 100 correct); the model learnt that
Twitter negativity is often sarcastic or understated.
