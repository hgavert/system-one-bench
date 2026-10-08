# 4 · Key code: the other reproductions, zero-shot, and results

Files: [`adapters/`](../adapters), [`07_import_predictions.py`](../07_import_predictions.py).
Raw per-tweet output: `results/raw/*.jsonl`.

Fine-tuning on the task defeats the point of a general decision model: with 3,000 labelled tweets
you could just as well train a classifier head on top of sentence embeddings. So this round tests
**zero-shot only**. Every model gets the same 300 test tweets and the same question, with nothing
trained or tuned for sentiment.

Candidates come from the [Jev Decision Index](https://huggingface.co/spaces/multimodalart/jev-decision-index):
the best-ranked entrants not yet tried that actually run on an Apple M5 with 32 GB
([doc 1](1-landscape.md) lists why the top five don't).

## 4.1 One question, many engines

Each reproduction pins its own torch / MLX / transformers versions, so each runs in **its own
environment** through a small adapter. The adapter reads `data/test_tweets.jsonl`, which holds the
300 tweets plus the shared `SENTIMENT_QUESTION`:

```bash
uv run python adapters/export_test_tweets.py      # same tweets, same order as 02_benchmark.py
```

It writes one line per tweet:

```json
{"id": "t000", "pred": "positive", "probs": {"negative": 0.03, "neutral": 0.21, "positive": 0.76}, "latency_ms": 181.4}
```

`07_import_predictions.py` then scores that file with the *same* `summarize()` as `02_benchmark.py`
(accuracy, macro-F1, latency percentiles, ECE, confusion matrix) and writes `results/runs/<name>.json`,
so every engine lands in the same report.

Engines that serve TypeSafe's HTTP API (Kev) need no adapter at all; `systemone_classifier.py`
sends them the question dict directly.

## 4.2 SemIf: a stock model and a careful prompt

[`adapters/semif_adapter.py`](../adapters/semif_adapter.py), in SemIf's own venv with its native MLX backend:

```python
from semif_phase1 import mlx_backend
model, tok, meta = mlx_backend.load_model("Qwen/Qwen3.5-4B-Base", "1001bb4d…")   # the index's configuration

row = {"id": t["id"], "state": tweet, "question": q["instructions"],
       "options": [{"id": k, "description": f"{k}: {v}"} for k, v in q["criteria"].items()]}
r = mlx_backend.score(model, tok, row, meta)
probs = dict(zip(r["option_ids"], r["probabilities"]))
```

What `score` does:

1. Build a chat prompt: a system instruction, then JSON with `evidence` (the tweet), `criterion`
   (the question) and options relabelled **A / B / C**. The model never sees the option keys, only
   letters and descriptions, which is why we put `"negative: unhappy, …"` into each description.
2. One forward pass. Take the logits at the **last position**, pick out the tokens for `A`, `B`, `C`,
   softmax them. No token is generated.

That's the entire technique. It needs no trained weights, and the probabilities come from the
model's own next-token distribution.

## 4.3 openvons: the same idea over an OpenAI-compatible server

[`adapters/openvons_adapter.py`](../adapters/openvons_adapter.py). openvons keeps the model behind any
OpenAI-compatible server and asks for exactly **one token with `top_logprobs`**:

```python
body = {"messages": [system, "STATE:\n<tweet>\n\nQUESTION: …\nOPTIONS:\nA. negative: …\nB. neutral: …\nC. positive: …"],
        "max_tokens": 1, "temperature": 0, "logprobs": True, "top_logprobs": 5,
        "structured_outputs": {"choice": ["A", "B", "C"]}}
# probabilities = softmax over the returned logprobs of "A", "B", "C"
```

The index served Qwen3-4B-Instruct-2507 with vLLM. On a Mac, `mlx_lm.server` returns the same
OpenAI-style `top_logprobs`, so openvons' own backend code runs unchanged:

```bash
third_party/kev/.venv/bin/python -m mlx_lm.server --model models/Qwen3-4B-Instruct-2507 --port 8300
uv run python adapters/openvons_adapter.py > results/raw/openvons.jsonl
```

(`structured_outputs` is a vLLM extension that `mlx_lm` ignores; it doesn't matter here because
openvons reads the letter logprobs directly instead of trusting the sampled token.)

## 4.4 Decider 2B: a full fine-tune that answers in a letter

[`adapters/decider_adapter.py`](../adapters/decider_adapter.py). Decider ships its own `decider/`
package inside the model repo. Its server is built around CUDA graphs, but the `Decider` class can
load the plain model on any device:

```python
from decider.infer import Decider
d = Decider("models/decider-2b", device="mps", dtype=torch.bfloat16, use_graphs=False)
a = d.system_one(tweet, {"sentiment": SENTIMENT_QUESTION})["answers"]["sentiment"]
```

`system_one` renders the state and question in Decider's trained prompt layout, runs one forward
pass, reads the option-letter logits, and applies the checkpoint's stored temperature (1.3).

**The head.** Decider has no separate head. Its "head" is a slice of the language model's own output
layer, restricted to the label tokens (`decider/model.py`):

```python
h  = self.lm.model(input_ids, attention_mask).last_hidden_state   # Qwen3.5-2B, hidden size 2048
hs = h[slot_positions]                                             # [N, 2048]  one answer slot per question
W  = self.lm.lm_head.weight[self.letters]                          # [255, 2048] rows for A..Z, AA, AB, ...
logits = hs @ W.T                                                  # [N, 255]
logits[:, n_options:] = -inf                                       # mask unused letters
p = softmax(logits / 1.3)
```

The answer slot is the last token of the prompt, so the model predicts the letter that follows `(`:

```
Context:
<tweet>

Question: What is the overall sentiment of this message?
Options:
(A) unhappy, angry, disappointed or critical
(B) factual or mixed, no clear feeling
(C) happy, grateful, excited or praising
Answer: (
```

* **Fixed width 255**, one row per label token (A-Z, then 229 two-letter strings that are single tokens
  in Qwen's vocabulary). With 3 options the other 252 are masked to -inf. That is why Decider,
  like Jev's API, caps a choice question at 255 options.
* **No new parameters.** Qwen3.5 ties its output layer to its input embeddings, so the row for "A" is the
  embedding of the token "A". Decider is a full fine-tune of all ~2B parameters to answer in that slot,
  followed by a calibration-aware RL stage (`decider_config.json`).
* **Order-shuffled training.** The training code shuffles the options for every example
  (`rng.shuffle(opts)` in `decider/prompt.py`), so a letter carries no information about the answer.
  That shows in the position test below: Decider is nearly order-blind.

**Decider 4B v2** ([Mapika/decider-4b](https://huggingface.co/Mapika/decider-4b), tag `v2`, released
24 September) is the next size up: Qwen3.5-4B-Base, 8.4 GB bf16, the v1 supervised model plus a
rank-64 LoRA stage (merged) trained on harder decision families, stored temperature 1.935. Same
`decider/` interface, now with `mps_ops.py` for Apple GPUs; the same adapter runs it:

```bash
uv run python scripts/download_models.py --only decider-4b-v2      # Mapika/decider-4b @ tag v2 -> models/decider-4b-v2
uv run python adapters/decider_adapter.py models/decider-4b-v2 > results/raw/decider-4b-v2.jsonl
```

## 4.5 GLiNER2.5-Decide: a schema-driven encoder

[GLiNER2.5-Decide](https://huggingface.co/fastino/GLiNER2.5-Decide) (Fastino, Apache-2.0) is an
**encoder + head** decision model like Laya, from the GLiNER line of extractors: 340M parameters
on DeBERTa-v3-large, plus a ~1B variant. The task name, the question and every label with its
description are packed in front of the text, and one pass scores each label:

```
( [P] sentiment: What is the overall sentiment of this message? [DESC] negative: unhappy, angry, …
  [DESC] neutral: factual or mixed, … [DESC] positive: happy, grateful, … ( <tweet>
```

[`adapters/gliner_adapter.py`](../adapters/gliner_adapter.py), in its own venv (`pip install gliner2 torch peft`):

```python
model = AutoExtractor.from_pretrained("fastino/GLiNER2.5-Decide").to("mps")
task = {"sentiment": {"labels": dict(Q["criteria"]), "prompt": Q["instructions"]}}   # same field, question, descriptions
r = model.classify_text(tweet, task, include_confidence=True)["sentiment"]          # {"label": ..., "confidence": ...}
```

`gliner2` returns only the winning label and its confidence, so the other two labels share the
remainder evenly in our output. Accuracy, ECE and the cascade use only the top probability. Note that
review sentiment is one of its 17 training domains; our tweets are still unseen.

## 4.6 CLM: a contrastive bi-encoder, with its vLLM encoder swapped for MLX

[CLM](https://github.com/Contrastive-LM/CLM) (Contrastive-LM, released 24 September, after Decision
Index 0.1) is the embedding idea done properly. A **frozen Qwen3-8B** embeds the state + question and
each option's text **separately** (last-token pooling); two small **projection heads** (trained
contrastively, InfoNCE, on ~60M QA pairs, ~30M hard negatives and ~1M agent trajectories) map both
into a shared 512-d space; the answer is `softmax(scale · cosine)`. It serves TypeSafe's
`/v1/systemone`, so our `systemone_classifier.py` talks to it directly.

The only CUDA-bound part is the encoder: `clm-serve` expects a **vLLM pooling server** at
`/v1/embeddings`. [`adapters/mlx_embed_server.py`](../adapters/mlx_embed_server.py) is a drop-in
replacement on MLX:

```python
ids = tokenizer.encode(text)                    # like vLLM: Qwen3 adds no special tokens
h = model.model(mx.array([ids]))                # [1, L, 4096], already through the final RMSNorm
v = h[0, -1] / norm(h[0, -1])                   # last-token pooling, L2-normalised
# returned in the OpenAI /v1/embeddings format (base64 float32, as CLM requests)
```

**Parity check** ([`adapters/check_embed_parity.py`](../adapters/check_embed_parity.py)): against Hugging
Face transformers' Qwen3-8B (last token of `last_hidden_state`), the MLX vectors have cosine
**0.9998–1.0000** on four test texts, which is bf16 rounding. CLM itself runs unchanged (installed without its
`vllm` dependency):

```bash
third_party/kev/.venv/bin/python adapters/mlx_embed_server.py --model Qwen/Qwen3-8B --port 8090 &
(cd third_party/clm && CLM_DEVICE=cpu .venv/bin/clm-serve --port 8700 \
    --emb-url http://127.0.0.1:8090/v1/embeddings --ckpt checkpoints/CLM_v0.1-8B.pt --no-download)
uv run python 02_benchmark.py s1:clm-latest --url http://127.0.0.1:8700 --name clm-8b
uv run python 02_benchmark.py s1:clm-raw    --url http://127.0.0.1:8700 --name clm-raw   # no heads
```

**Result: 0.517**, with most tweets called negative (216 of 300). The encoder is verified, so the
likely cause is fit: CLM embeds each option's text on its own, and its training data (QA pairs,
agent actions, verification) doesn't cover affect. It is also very sensitive to how the options are
worded ([`adapters/clm_phrasing.py`](../adapters/clm_phrasing.py), still zero-shot):

| Option text | Accuracy | Correct neg / neu / pos (of 100) | Mostly predicts |
|---|---|---|---|
| descriptions (standard, as every other model) | 0.517 | 96 / 9 / 50 | negative |
| label words only | 0.480 | 79 / 18 / 47 | negative |
| `negative: unhappy, …` | 0.550 | 88 / 3 / 74 | never neutral |
| `The sentiment of this message is negative.` | 0.433 | 18 / 22 / 90 | positive |

`clm-raw`, cosine in the raw Qwen3-8B space with no heads, scores **0.343** (chance) and calls
everything positive. Raw last-token embeddings sit in a narrow cone (two unrelated tweets have
cosine 0.95), which is why CLM trains heads at all.

## 4.7 Clef-flash: Cloudflare's decision model, with its own inference code

[Clef-flash](https://huggingface.co/Cloudflare/clef-flash) (Cloudflare, 1 October 2026, Apache-2.0) is post-trained
from Qwen3.5-9B. A **joint schema head**, a small transformer, reads the backbone's final hidden states and scores the
options of all questions together. The release ships the weights plus `joint_schema_model.py`, whose `systemone()`
turns a `/v1/systemone` request into a response, in plain PyTorch. [`adapters/clef_server.py`](../adapters/clef_server.py)
serves it on this Mac (bf16, MPS, 19 GB), so every test calls it like Kev or CLM:

```bash
third_party/clef-env/.venv/bin/python adapters/clef_server.py --port 8720      # own venv: scripts/setup_engines.sh clef
uv run python 02_benchmark.py s1:clef-flash --url http://127.0.0.1:8720 --name clef-flash
```

Two details of its input code matter for the results:

* **Options are sorted alphabetically** before encoding (`sorted(criteria.items())`), so the six option orders are the
  same input: 0% of answers flip in the position test. That is order-invariance by preprocessing, not by the head.
* **The question ID is part of the prompt** (`FIELD 1 / ID: <id> / TYPE: choice / INSTRUCTION: ...`). On the tweets,
  [`adapters/clef_question_variants.py`](../adapters/clef_question_variants.py) measured 0.597 with ID `sentiment`,
  0.620 / 0.623 with `s` / `q`, and 0.600 with label words only: within noise, and every variant calls about two
  thirds of the tweets neutral.

Results: **0.597 on the tweets** (macro-F1 0.594, ECE 0.205, 477 ms per tweet), but the **best open model in the Finnish
test** (0.928 in Finnish, ECE ≈ 0.03; hosted Jev 0.931, level) and the **best open player in Snake** (39.3 food per game
with judged options, no death in 10 games; hosted Jev 40.6; 85% good moves on the hard raw-board probe states, Jev 97%). The 27B Clef (55 GB bf16) does not fit a
32 GB Mac. Its probabilities are the head's raw softmax; the release applies no temperature.

## 4.8 Results

Same 300 test tweets, same question, nothing trained on tweets. From `results/REPORT.md`:

| System | Family | Index # | Accuracy | Macro-F1 | p50 | ECE |
|---|---|---|---|---|---|---|
| **Decider 4B v2** | full fine-tune, letter logits | new | **0.750** | **0.751** | 258 ms | 0.056 |
| **Decider 2B** | full fine-tune, letter logits | 13 | 0.740 | 0.745 | 143 ms | **0.032** |
| *Gemma 4 26B-A4B (LLM, class descriptions)* | – | – | *0.740* | *0.736* | *660 ms* | *0.260* |
| SemIf · Qwen3.5-9B-Base *(variant)* | inference technique | – | 0.730 | 0.707 | 320 ms | 0.080 |
| **SemIf** · Qwen3.5-4B-Base | inference technique | 11 | 0.717 | 0.698 | 189 ms | 0.054 |
| Kev 9B | LoRA + pointer | 6 | 0.690 | 0.695 | 448 ms | 0.052 |
| **openvons** · Qwen3-4B-Instruct | inference technique | 10 | 0.687 | 0.617 | 301 ms | 0.305 |
| Kev 4B | LoRA + pointer | 7 | 0.637 | 0.646 | 261 ms | 0.107 |
| **GLiNER2.5-Decide** (340M) | encoder + head | new | 0.637 | 0.635 | 62 ms | 0.061 |
| Laya | encoder + head | 30 | 0.633 | 0.639 | 49 ms | 0.071 |
| **GLiNER2.5-Decide-1B** | encoder + head | new | 0.630 | 0.632 | 73 ms | 0.081 |
| Laya multilingual | encoder + head | – | 0.630 | 0.634 | 20 ms | 0.112 |
| Kev 0.8B | LoRA + pointer | (17)* | 0.587 | 0.597 | 45 ms | 0.128 |
| *Nearest description by embedding (nomic-embed)* | *bi-encoder baseline* | – | *0.567* | *0.537* | *13 ms* | *0.071* |
| **Clef-flash** | backbone + joint head | new | 0.597 | 0.594 | 477 ms | 0.205 |
| **CLM 8B** | contrastive bi-encoder | new | 0.517 | 0.451 | 167 ms | 0.271 |
| *Qwen3-8B raw embeddings (`clm-raw`)* | *bi-encoder baseline* | – | *0.343* | *0.193* | *166 ms* | *0.213* |

\* the index lists the older Kev 0.6B; we ran the newer 0.8B.

Confusion matrices (rows = truth, 100 each; columns = predicted negative / neutral / positive):

```
Decider 2B   [75 25  0] [13 73 14] [ 2 24 74]     most balanced
SemIf 4B     [91  8  1] [34 41 25] [ 6 11 83]     pushes neutral into a polarity
openvons     [99  1  0] [50 16 34] [ 8  1 91]     almost never says "neutral"
Kev 9B       [74 26  0] [23 63 14] [ 3 27 70]
```

**Reading it**

* **The Decider models tie the best LLM zero-shot.** Decider 4B v2 has the top accuracy and macro-F1
  (0.750 / 0.751) and Decider 2B the best calibration (ECE 0.032), but paired tests on the same tweets
  find no real difference between them and Gemma 26B (McNemar p = 0.79 and 0.81). The 2B is the better
  deal here: as accurate, 1.8× faster than the 4B and 4.6× faster than the LLM, even on MPS without the
  CUDA graphs its server normally uses.
* **GLiNER2.5-Decide** lands with Laya and Kev 4B (0.63–0.64), fast (62–73 ms) and well calibrated. The 1B
  is no better than the 340M; they fail differently (the 1B misses negatives, the 340M positives), despite
  review sentiment being one of its training domains.
* **Letter-logit readouts lead.** A *stock* base model read this way (SemIf) beats the trained
  pointer and marker heads of Kev and Laya on this task.
* **The base model matters as much as the technique.** openvons applies the same idea to an
  *instruct* model. It is right on 99 negative and 91 positive tweets but only 16 neutral ones, and it
  puts ~100% on one letter for 269 of 300 tweets (top-5 logprobs leave the other letters at 0). So
  its probabilities carry little information (ECE 0.305, LLM-level).
* **The Decision Index ranking doesn't transfer one-to-one.** #13 beats #6 here, and #30 (Laya) is
  11 points off the top. The index averages 37 very different benchmarks.
* **Embeddings aren't enough, even trained ones.** Nearest description by cosine similarity (0.567) and
  CLM's trained contrastive heads (0.517) both trail every cross-encoder: encoding the tweet and the
  options separately loses the interaction between them.

**Trained models, for reference.** Same test tweets, after one epoch on 3,000 training tweets
([Laya](reference/finetune-laya.md), [Kev](reference/finetune-kev.md)):

| Model | Zero-shot → trained | Macro-F1 | p50 / p95 | ECE | Training on M5 |
|---|---|---|---|---|---|
| Laya | 0.633 → 0.717 | 0.711 | 49 / 66 ms | 0.048 | ~10 min, full model |
| Kev 0.8B | 0.587 → 0.710 | 0.701 | 43 / 47 ms | 0.057 | ~40 min, LoRA + head |
| Kev 4B | 0.637 → 0.740 | 0.739 | 185 / 189 ms | 0.040 | ~90 min, LoRA + head |

Zero-shot Decider 2B (0.740) already matches the best trained model here.

**Cascade.** `05_cascade.py --fast decider-2b`: accept Decider's answer when it is ≥ 0.5 confident and
ask Gemma 26B otherwise. That gives 0.753 with only 6% of tweets sent to the LLM (188 ms average),
versus 0.740 for Gemma alone (669 ms).

## 4.9 Position bias

Does the order of the options change the answer? [`adapters/position_bias.py`](../adapters/position_bias.py)
reruns the same 300 tweets with the three options in **all 6 orders** (each label in each position
equally often; 1,800 decisions per model); [`11_position_bias.py`](../11_position_bias.py) analyses them.

| | Laya | SemIf | Decider 2B |
|---|---|---|---|
| Accuracy range over the 6 orders | 0.617 - 0.643 | 0.710 - 0.730 | 0.737 - 0.747 |
| Accuracy when the correct answer is listed 1st / 2nd / 3rd | **0.69 / 0.61 / 0.59** | 0.72 / 0.71 / 0.73 | 0.75 / 0.73 / 0.75 |
| Share of picks by position 1st / 2nd / 3rd (order-blind = 33/33/33) | **36.9 / 32.3 / 30.8%** (chi-square p = 0.004) | 33.5 / 32.7 / 33.8% (p = 0.85) | 33.7 / 32.7 / 33.7% (p = 0.84) |
| Tweets whose answer changes with order alone | **22.0%** | **19.3%** | 5.7% |
| Mean largest probability swing per tweet | 0.16 | 0.19 | 0.06 |
| Neutral tweets correct when "neutral" is listed 1st / 2nd / 3rd | 0.72 / 0.65 / 0.62 | 0.45 / 0.39 / 0.47 | 0.76 / 0.72 / 0.75 |

Two different effects:

* **Position bias**, a consistent pull towards a slot: only **Laya** has it. It favours whatever is
  listed first; its accuracy drops 10 points when the correct answer moves from first to last.
* **Order sensitivity**, answers that change without a consistent direction: **SemIf**. No position is
  preferred on average, but 19% of tweets flip and its probabilities swing most. A stock model
  never trained on shuffled options reacts to the letters and layout tweet by tweet.
* **Decider** is robust: no preference, 5.7% flips, mostly borderline tweets. Its training shuffles
  options every example.

In practice, averaging a sensitive model over two or three orderings removes most of the effect,
at 2-3x the cost. Kev's benchmark has this built in (`--rotations`). Single-order results for Laya
and SemIf can be off by a point or two overall and up to ~5 points on a class.

## 4.10 Isn't this just embeddings?

A natural simplification of the question dict: embed each `"label: description"` string, embed the
tweet, pick the nearest by cosine. [`adapters/embedding_baseline.py`](../adapters/embedding_baseline.py)
does exactly that with `nomic-embed-text-v1.5` (served by LM Studio):

```python
label_vecs = embed([f"{k}: {v}" for k, v in crit.items()])   # once, independent of any tweet
choice = labels[argmax(label_vecs @ embed([tweet])[0])]      # cosine similarity (vectors are normalised)
```

It scores **0.567**, below every cross-encoder. CLM (section 4.6) is the trained version of the same
idea and scores 0.517; raw Qwen3-8B embeddings score 0.343. The difference is *where* the comparison happens:

* **Embeddings (bi-encoder).** Tweet and descriptions are encoded **separately**. The tweet's vector
  never sees the question: it is the same vector whether you ask about sentiment, urgency or refunds,
  so a cosine can't focus on the aspect you care about. Negation, sarcasm and "neutral = mixed" survive
  only as far as a single similarity score can carry them.
* **System One models (cross-encoder).** Question, options and tweet go into **one** sequence, and every
  token attends to every other. Laya's per-option `[MASK]` token, Kev's `<decide>` token and the letter
  logit are all computed *after* the model has read this tweet under this question.

The output is the same shape ("which option fits best"), but the matching happens inside the network,
in context. The flip side is cost: descriptions can be embedded once, while a System One model needs
one pass per tweet per question.

The approach that *would* compete is embeddings plus a classifier trained on labelled tweets. But
that is trained for one fixed question, which is the thing a System One model is meant to avoid.

## 4.11 Practical notes

* **Getting the models.** `scripts/download_models.py` fetches every model above at the revision that was
  measured, into the place its adapter expects, and checks each file's SHA-256 against the Hub.
  `scripts/setup_engines.sh` builds each engine's environment at the benchmarked commit.

* **Downloads.** Mid-session, the Hugging Face CDN route from this network dropped to about 25 KB
  per connection, logged in or not. Two scripts work around it:
  * [`scripts/fetch_modelscope.sh`](../scripts/fetch_modelscope.sh) fetches Qwen models from the
    ModelScope mirror in parallel byte ranges.
  * [`scripts/fetch_hf_parallel.sh`](../scripts/fetch_hf_parallel.sh) splits one Hugging Face file
    into 32 parallel ranges.
* **Latency** is measured inside each engine's process (SemIf, Decider) or client-side around
  one local HTTP call (Kev, openvons, LM Studio LLMs), one tweet at a time. Treat it as ±30%.
* **Probabilities.** Laya, Kev and Decider ship fitted temperatures. SemIf and openvons report raw
  letter softmaxes, which their authors explicitly call uncalibrated. SemIf on a base model still turns
  out reasonably calibrated here (ECE 0.054 / 0.080). openvons on an instruct model does not
  (ECE 0.305): instruct models are near-certain about their first token.
