# 3 · The benchmark: method and baselines

Files: [`02_benchmark.py`](../02_benchmark.py), [`llm_classifier.py`](../llm_classifier.py),
[`systemone_classifier.py`](../systemone_classifier.py), [`run_kev.sh`](../run_kev.sh),
[`04_report.py`](../04_report.py), [`05_cascade.py`](../05_cascade.py).
Raw numbers: [`results/REPORT.md`](../results/REPORT.md); every prediction is in `results/runs/*.json`.

## 3.1 Method

* **Same 300 tweets for every system.** Class-balanced (100 per class), seed 42, TweetEval **test** split.
* **One message per call**, sequentially, after one warm-up call, so model loading isn't timed.
  Latency is measured client-side around the call (for Kev and the LLMs it includes the local HTTP round trip).
* **Metrics:** accuracy, macro-F1, p50/p95 latency, throughput, and **ECE** (expected calibration
  error of the top-class probability; 15 bins, using `laya.ece_score`).
* **Hardware:** Apple M5, 32 GB. Laya (fp32) and Decider (bf16) on PyTorch MPS; Kev and SemIf on MLX;
  openvons over `mlx_lm.server`; LLMs and the embedding model in LM Studio (QAT builds).
  One system at a time, with LM Studio models unloaded while the others ran.

## 3.2 The LLM baseline (`llm_classifier.py`)

```python
client.chat.completions.create(
    model="google/gemma-4-26b-a4b-qat", temperature=0,
    messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": tweet}],
    response_format={"type": "json_schema", "json_schema": {... "enum": ["negative", "neutral", "positive"]}},
    reasoning_effort="none",
)
```

Two choices make the comparison fair:

1. **A JSON-schema `enum`** constrains decoding, so the LLM can only emit one of the three labels.
   The comparison is then about the model, not about parsing free text.
2. **`reasoning_effort="none"`.** Gemma 4 and Qwen 3.x think by default. With thinking on, Gemma 4 12B
   spent ~150 reasoning tokens and ~15 s per tweet; with it off, ~20 tokens and ~2.3 s.
   Pass `--reasoning default` to benchmark with thinking on.

The same class descriptions go into the system prompt that Laya gets as `criteria`.

**Bare-prompt variant** (`--prompt simple`): no system prompt, one user message:
`Classify the following text to be either negative, neutral or positive.`, a blank line, then the tweet,
with the same enum schema.

| LLM | With class descriptions | Bare prompt | Same label | Paired McNemar |
|---|---|---|---|---|
| Gemma 4 26B-A4B | 0.740 · 660 ms | 0.723 · 388 ms | 277/300 | p = 0.38 |
| Gemma 4 12B | 0.713 · 2.3 s | 0.697 · 1.3 s | 275/300 | p = 0.41 |
| Qwen 3.8 27B | 0.663 · 3.3 s | **0.710** · 2.9 s | 264/300 | **p = 0.013** |

Only Qwen's difference is real. With the descriptions it filed 25 positive tweets as neutral (reading
"mixed" broadly); without them, 14.

## 3.3 The Kev baseline (`systemone_classifier.py`, `run_kev.sh`)

Kev serves TypeSafe's System One API, so the client just POSTs the **same question dict**:

```python
httpx.post("/v1/systemone", json={"model": "kev-latest", "state": tweet,
                                  "questions": {"sentiment": SENTIMENT_QUESTION}})
```

`run_kev.sh kev-4b` starts `python -m kev.serve --run jaredpalmer/kev-4b`, waits for `/v1/models`,
runs the benchmark and stops the server. On a Mac, Kev runs its Qwen3.5 backbone through MLX
(there are no PyTorch MPS kernels for Qwen3.5's DeltaNet layers).

## 3.4 Engines in their own environment

SemIf, openvons and Decider pin their own torch / MLX builds, so they run through small adapters
that read the same 300 tweets and write one prediction per line; `07_import_predictions.py` scores
them with the same `summarize()`. See [doc 4](4-zero-shot-reproductions.md).

## 3.5 Results

All zero-shot results (System One reproductions, LLMs with both prompts, the embedding baseline)
and how to read them are in [doc 4, section 4.8](4-zero-shot-reproductions.md#48-results) and
[`results/REPORT.md`](../results/REPORT.md). The fine-tuned runs are listed separately there, as
reference only ([Laya](reference/finetune-laya.md), [Kev](reference/finetune-kev.md)).

With n = 300, the 95% interval on an accuracy near 0.7 is about ±5 points. Read gaps smaller than
that as ties, or use a paired test on the same tweets, as in the prompt comparison above.

## 3.6 Caveats

* TweetEval test tweets are from 2016–2017 and public; any model may have seen them in pre-training.
* Laya's published benchmarks run on CUDA; on Apple MPS the per-call overhead dominates, so batching helps
  only 1.2–1.7×. Expect bigger batching gains on an NVIDIA GPU.
* The LLM prompts weren't tuned beyond the two variants above. Few-shot examples would likely raise the LLM numbers.
* Latency is one tweet at a time on a laptop GPU; several engines (Decider, Kev, SemIf) batch and cache far better on CUDA.
