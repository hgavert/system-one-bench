# Reference · fine-tuning Kev on the tweets

> **Not part of the main comparison.** Training a general decision model on the task defeats its purpose
> (you could train a classifier on embeddings instead). Kept to show the ceiling. The main results are zero-shot:
> [doc 4](../4-zero-shot-reproductions.md).

Files: [`06_export_kev_data.py`](../../06_export_kev_data.py), [`run_kev_finetune.sh`](../../run_kev_finetune.sh).
Logs: `results/logs/kev-*-tweets-*.log`. Calibration rows: `results/kev-finetune/`.

Laya gained 8 points from 10 minutes of fine-tuning ([doc 3](finetune-laya.md)). Does the same
work for Kev, a different architecture (a causal Qwen3.5 backbone with LoRA and a pointer head)?
For a fair comparison, both models get **the same 3,000 training tweets, the same 300
validation tweets, the same question definition and one epoch each**.

## 1 Data: an API request plus a label

Kev's trainer reads JSONL in the same shape as a `/v1/systemone` request, with a `label` added to
each question. `06_export_kev_data.py` writes the Laya training tweets in that format:

```python
{"state": ex.text,
 "questions": {"sentiment": {**SENTIMENT_QUESTION, "label": ex.label}}}
```

```json
{"state": "finally got my new phone today, the camera is unreal ^_^",
 "questions": {"sentiment": {"type": "choice", "instructions": "What is the overall sentiment of this message?",
   "criteria": {"negative": "unhappy, angry, …", "neutral": "factual or mixed, …", "positive": "happy, grateful, …"},
   "label": "positive"}}}
```

Because the training format *is* the request format, the model is trained on exactly what it
will be asked at serving time. That's the same principle as reusing `build_sequence` for Laya.

## 2 Train: warm-start from the released model

```bash
python -m kev.train --data data/kev/train.jsonl \
    --base Qwen/Qwen3.5-4B-Base --init_from jaredpalmer/kev-4b \
    --epochs 1 --lr 2e-5 --batch 1 --accum 8 \
    --device mps --weights_dtype bf16 --checkpointing 1 \
    --out models/kev-4b-tweets
```

* **`--init_from`** loads the released LoRA adapter and pointer head first, so Kev keeps its general
  decision skills and adds tweets on top. Kev's README reports that training from the bare base
  instead collapses its general accuracy (0.84 → 0.33).
* **`lr 2e-5`, batch 1 × 8 accumulation** is Kev's recommended fine-tuning recipe. Only the LoRA
  adapter and head train: 11.3M parameters for 0.8B, 33.8M for 4B.
* **`--weights_dtype bf16 --checkpointing 1`** keeps the frozen 4B backbone in half precision with
  gradient checkpointing, so it fits comfortably in 32 GB of unified memory.
* **Built-in augmentation.** Every training record's options are shuffled. About 10% have the
  true option replaced by a "none of the above" choice, about 12% get "none of the above" as a
  wrong extra option, and about 15% get an irrelevant distractor option. So Kev learns the
  *labels*, not their position. Laya's fine-tune used a fixed option order.

**Speed on an Apple M5:** Qwen3.5's DeltaNet layers have no MPS kernels, so training runs through
the slow reference PyTorch path (serving uses MLX and is fast). That works out to 0.79 s per
tweet for 0.8B (≈ 40 min) and 1.8 s per tweet for 4B (≈ 90 min). On a CUDA GPU with
`flash-linear-attention`, it takes minutes. 9B would need ~3–4 hours and most of the RAM, so it
wasn't run here.

## 3 Calibrate: fit one temperature on held-out tweets

```bash
KEV_TEMPERATURE=1.0 python -m kev.serve --run models/kev-4b-tweets --port 8010 &   # raw logits
python -m kev.benchmark --remote http://127.0.0.1:8010 --data data/kev/val.jsonl --out results/kev-finetune/kev-4b/val
python scripts/calibrate_checkpoint.py --run models/kev-4b-tweets --rows results/kev-finetune/kev-4b/val/rows.json
```

The validation tweets are scored with raw logits, then Kev's own calibration script fits one
temperature and writes it into `head.pt`, so every later load serves calibrated probabilities.
The script also reports an out-of-fold estimate, so you can see whether the fit generalises:

```
kev-0.8b  T=1.52  acc 0.707 -> 0.707 | ece 0.094 -> 0.033 | OOF ece 0.034
```

As with Laya, the temperature never changes which answer wins. It only changes how confident the
model claims to be.

## 4 Benchmark: same harness, same 300 test tweets

```bash
./run_kev.sh models/kev-4b-tweets      # serve the local checkpoint, run 02_benchmark.py against it
```

## 5 Results

Same 300 test tweets as every other system ([doc 4](../3-benchmark-method.md)):

| Model | Zero-shot accuracy | Fine-tuned accuracy | Macro-F1 | p50 latency | ECE | Training time (M5) |
|---|---|---|---|---|---|---|
| Kev 0.8B | 0.587 | **0.710** (+12.3) | 0.701 | 43 ms | 0.057 | ~40 min |
| Kev 4B | 0.637 | **0.740** (+10.3) | 0.739 | 185 ms | 0.040 | ~90 min |
| *Laya (for reference)* | *0.633* | *0.717 (+8.4)* | *0.711* | *49 ms* | *0.048* | *~10 min* |
| *Gemma 4 26B-A4B, LLM, no fine-tune* | *0.740* | – | *0.736* | *660 ms* | *0.260* | – |

Validation accuracy (used only to fit the temperature): 0.707 for 0.8B (T = 1.52) and 0.723 for 4B (T = 1.23).

Confusion matrix, fine-tuned Kev 4B (rows = truth, 100 each; columns = predicted negative / neutral / positive):

```
negative [87, 13,  0]
 neutral [26, 61, 13]
positive [ 3, 23, 74]
```

**What this shows**

* **Fine-tuning works for Kev too, and it helps more than for Laya.** Kev gains 10–12 points; Laya gains 8.
* **Fine-tuned Kev 4B ties the best LLM** (0.740 vs 0.740), at 3.6× lower latency and with honest
  probabilities (ECE 0.040 vs 0.260). The fine-tuned 4B also beats the *zero-shot* 9B (0.690).
* **Fine-tuned Kev 0.8B ≈ fine-tuned Laya**: 0.710 vs 0.717 at ~45 ms each. Laya trains 4× faster
  on a Mac (a plain encoder with MPS kernels), while Kev's training cost is a Mac-specific penalty.
* **Better confidence makes a better router.** Kev-4B fine-tuned → Gemma 26B at a 0.5 confidence
  threshold scores 0.763 while sending only 7% of tweets to the LLM
  (`uv run python 05_cascade.py --fast kev-4b-tweets`). That gain is within sampling noise, but
  cutting LLM calls by 93% is not.
* Its latency (185 ms) is lower than the zero-shot Kev 4B run (261 ms). The model and backend are
  the same, but the zero-shot run most likely shared the machine with the 18 GB Kev-9B download, so
  treat Kev latencies as ±30%.

## 6 Reproduce

```bash
uv run python 06_export_kev_data.py        # data/kev/train.jsonl, val.jsonl
./run_kev_finetune.sh kev-0.8b              # ~45 min on an M5, including calibration and benchmark
./run_kev_finetune.sh kev-4b                # ~100 min
uv run python 04_report.py
```
