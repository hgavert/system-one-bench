# Open-source Jev reproductions, zero-shot on real sentiment

A hands-on tutorial. **Jev** (TypeSafe AI, released 15 Sept 2026) is a "System One" model: it
answers typed questions with probabilities instead of generating text. Within a week, dozens of
open reproductions appeared. This repo takes the best-ranked ones that run on a 32 GB Apple M5,
asks each the **same** sentiment question about 300 human-labelled tweets, and benchmarks them
against local LLMs in LM Studio. **Zero-shot, with no training for the task.**

* **Reproductions run:** [Laya](https://huggingface.co/convaiinnovations/laya) (+ multilingual),
  [Kev](https://github.com/jaredpalmer/kev) 0.8B / 4B / 9B, [SemIf](https://github.com/TheoLeeCJ/openjev),
  [openvons](https://github.com/genai-craft/openvons), [Decider 2B](https://huggingface.co/Mapika/decider-2b),
  plus the newly released [Decider 4B v2](https://huggingface.co/Mapika/decider-4b/tree/v2),
  [GLiNER2.5-Decide](https://huggingface.co/fastino/GLiNER2.5-Decide) (340M and 1B) and [CLM 8B](https://github.com/Contrastive-LM/CLM) (contrastive bi-encoder).
  Chosen from the [Jev Decision Index](https://huggingface.co/spaces/multimodalart/jev-decision-index);
  why the top five don't fit a 32 GB Mac: [docs/1-landscape.md](docs/1-landscape.md)
* **LLM baselines:** Gemma 4 26B-A4B, Gemma 4 12B and Qwen 3.8 27B in LM Studio, with JSON-schema output
* **Dataset:** [TweetEval sentiment](https://huggingface.co/datasets/cardiffnlp/tweet_eval)
  (SemEval-2017 Task 4A): tweets labelled negative / neutral / positive by human annotators,
  a class-balanced sample of 300 from the test split

**Report:** [docs/sentiment-report.md](docs/sentiment-report.md) · interactive version:
[docs/page/index.html](docs/page/index.html).
Both are generated from `results/` by `uv run python docs/page/build.py`.

## Zero-shot results (Apple M5, 32 GB)

300 balanced test tweets, one per call, nothing trained on tweets. ±5 points of sampling noise.

| System | Family | Index # | Accuracy | Macro-F1 | p50 | ECE |
|---|---|---|---|---|---|---|
| **Decider 4B v2** | full fine-tune, letter logits | new | **0.750** | **0.751** | 258 ms | 0.056 |
| **Decider 2B** | full fine-tune, letter logits | 13 | 0.740 | 0.745 | 143 ms | **0.032** |
| LLM Gemma 4 26B-A4B | LLM, class descriptions | – | **0.740** | 0.736 | 660 ms | 0.260 |
| SemIf · Qwen3.5-9B-Base *(variant)* | inference technique | – | 0.730 | 0.707 | 320 ms | 0.080 |
| LLM Gemma 4 26B-A4B | LLM, bare prompt | – | 0.723 | 0.715 | 388 ms | 0.277 |
| **SemIf** · Qwen3.5-4B-Base | inference technique | 11 | 0.717 | 0.698 | 189 ms | 0.054 |
| LLM Gemma 4 12B | LLM, class descriptions | – | 0.713 | 0.714 | 2.3 s | 0.287 |
| LLM Qwen 3.8 27B | LLM, bare prompt | – | 0.710 | 0.694 | 2.9 s | 0.290 |
| Kev 9B | LoRA + pointer | 6 | 0.690 | 0.695 | 448 ms | 0.052 |
| **openvons** · Qwen3-4B-Instruct | inference technique | 10 | 0.687 | 0.617 | 301 ms | 0.305 |
| LLM Qwen 3.8 27B | LLM, class descriptions | – | 0.663 | 0.656 | 3.3 s | 0.337 |
| Kev 4B | LoRA + pointer | 7 | 0.637 | 0.646 | 261 ms | 0.107 |
| **GLiNER2.5-Decide** (340M) | encoder + head | new | 0.637 | 0.635 | 62 ms | 0.061 |
| Laya | encoder + head | 30 | 0.633 | 0.639 | 49 ms | 0.071 |
| **GLiNER2.5-Decide-1B** | encoder + head | new | 0.630 | 0.632 | 73 ms | 0.081 |
| Laya multilingual | encoder + head | – | 0.630 | 0.634 | 20 ms | 0.112 |
| Kev 0.8B | LoRA + pointer | – | 0.587 | 0.597 | 45 ms | 0.128 |
| *Nearest description by embedding* | *bi-encoder baseline* | – | *0.567* | *0.537* | *13 ms* | *0.071* |
| **CLM 8B** | contrastive bi-encoder | new | 0.517 | 0.451 | 167 ms | 0.271 |
| *Qwen3-8B raw embeddings* | *bi-encoder baseline* | – | *0.343* | *0.193* | *166 ms* | *0.213* |

(Gemma 4 12B with the bare prompt: 0.697. Full table: [results/REPORT.md](results/REPORT.md).)

* **The Decider models tie the best local LLM zero-shot**: Decider 4B v2 0.750 and Decider 2B 0.740 vs
  Gemma 26B 0.740 (paired p ≈ 0.8), with honest probabilities. The 2B is the better deal: as accurate, 4.6× faster
  than the LLM and 1.8× faster than the 4B.
* **Bigger isn't automatically better within a family**: GLiNER2.5-Decide-1B (0.630) doesn't beat the 340M
  model (0.637).
* **Letter-logit readouts lead**; even a stock base model read that way (SemIf) beats Kev's and
  Laya's trained heads here. On an *instruct* model (openvons) the same trick almost never says
  "neutral" and is over-confident.
* **Embeddings aren't enough, even trained ones**: nearest label description by cosine gets 0.567, and CLM's
  trained contrastive heads on Qwen3-8B get 0.517 (0.43–0.55 depending on how the options are worded).
* **Label descriptions are a model-specific lever**: no effect on Gemma, +4.7 points for Qwen 27B
  without them (paired test p = 0.013).
* **Option order**: rerunning with all 6 option orders, Laya favours whichever option is listed first
  (accuracy 0.69 when the answer is first vs 0.59 when last), SemIf flips 19% of answers without a
  consistent direction, and Decider is nearly order-blind (5.7% flips; its training shuffles options).
* **Cascade**: accept Decider's answer at ≥ 0.5 confidence, else ask Gemma 26B → 0.753 with only 6% of tweets
  sent to the LLM.

## Setup

```bash
./scripts/setup_engines.sh                         # main env + each engine at the benchmarked commit, own env each
uv run python scripts/download_models.py --list    # the models, where they go, sizes (~76 GB in total)
uv run python scripts/download_models.py           # download all at the benchmarked revisions and SHA-256-verify
```

- `setup_engines.sh` takes engine names to set up only some: `main kev semif openvons clm gliner`.
- `download_models.py --only decider-2b,gliner-decide` fetches a subset (Kev's Qwen3.5 bases are added
  automatically); `--verify` checks what is on disk without downloading. If huggingface.co is slow from your
  network, `--parallel` splits large files into 32 byte ranges and `--modelscope` fetches Qwen3-4B-Instruct from
  the ModelScope mirror.
- LLM baselines and `nomic-embed-text`: [LM Studio](https://lmstudio.ai) serving on `localhost:1234`.

## The tutorial, step by step

| Step | Run | What you learn |
|---|---|---|
| 1 | `uv run python 01_hello_laya.py` | Declare a typed `choice` question, classify three messages with the simplest reproduction |
| 2 | `uv run python 02_benchmark.py laya` | Score 300 labelled tweets: accuracy, macro-F1, latency, calibration |
| 2b | `./run_kev.sh kev-9b` | The same question over Kev's TypeSafe-compatible HTTP API |
| 2c | `uv run python 02_benchmark.py llm:google/gemma-4-26b-a4b-qat` | The same tweets through a local LLM |
| 3 | `uv run python adapters/export_test_tweets.py`, then an adapter, then `07_import_predictions.py` | Engines that need their own environment: SemIf, openvons, Decider |
| 4 | `uv run python 04_report.py` | Every run in one table: `results/REPORT.md` |
| 5 | `uv run python 05_cascade.py --fast decider-2b` | Route only low-confidence answers to the LLM |
| 6 | `uv run python adapters/embedding_baseline.py` | Contrast: nearest label description by embedding |
| 8 | `uv run python 08_snake_server.py` → http://127.0.0.1:8765 | A System One model plays Snake; every request, prompt and probability on the side |
| 9 | `uv run python 09_snake_benchmark.py` | Ten games per way of asking, next to code-only baselines: `results/snake/SUMMARY.md` |
| 10 | `uv run python 10_snake_probe.py` | Single moves with a known right answer: which phrasing a model can actually use |
| 11 | `adapters/position_bias.py <engine>`, then `uv run python 11_position_bias.py` | Does option order change the answer? |

Adapters (each file's docstring has the exact command):

```bash
third_party/openjev/.venv/bin/python adapters/semif_adapter.py 4b > results/raw/semif.jsonl
third_party/kev/.venv/bin/python -m mlx_lm.server --model models/Qwen3-4B-Instruct-2507 --port 8300 &
uv run python adapters/openvons_adapter.py > results/raw/openvons.jsonl
uv run python adapters/decider_adapter.py > results/raw/decider-2b.jsonl
uv run python adapters/decider_adapter.py models/decider-4b-v2 > results/raw/decider-4b-v2.jsonl
third_party/gliner2-env/.venv/bin/python adapters/gliner_adapter.py fastino/GLiNER2.5-Decide > results/raw/gliner-decide.jsonl
third_party/kev/.venv/bin/python adapters/mlx_embed_server.py --model Qwen/Qwen3-8B --port 8090 &   # CLM's encoder
(cd third_party/clm && CLM_DEVICE=cpu .venv/bin/clm-serve --port 8700 --emb-url http://127.0.0.1:8090/v1/embeddings --ckpt checkpoints/CLM_v0.1-8B.pt) &
uv run python 02_benchmark.py s1:clm-latest --url http://127.0.0.1:8700 --name clm-8b
uv run python 07_import_predictions.py semif results/raw/semif.jsonl       # likewise for the others
uv run python 02_benchmark.py llm:google/gemma-4-26b-a4b-qat --prompt simple --name llm-google_gemma-4-26b-a4b-qat-simple
```

### For reference: task fine-tuning

Fine-tuning a general decision model on 3,000 tweets defeats its purpose (you could train a
classifier head on embeddings instead), but it shows the ceiling. It was done once and isn't
part of the main comparison: `03_finetune_laya.py`, `06_export_kev_data.py` + `run_kev_finetune.sh`.

All three trained on the same 3,000 training tweets (1,000 per class), one epoch, same question dict,
then had their temperature refitted on 300 validation tweets. Evaluated on the same 300 test tweets.

| Model | What was trained | Trainable params | Training on M5 | Saved size | Accuracy zero-shot → trained | Macro-F1 | p50 / p95 | msg/s | ECE |
|---|---|---|---|---|---|---|---|---|---|
| Laya | full model | 421M | ~10 min | 1.6 GB | 0.633 → **0.717** | 0.711 | 49 / 66 ms | 19.7 (23 batched) | 0.048 |
| Kev 0.8B | LoRA + pointer head | 11.3M | ~40 min | 62 MB | 0.587 → **0.710** | 0.701 | 43 / 47 ms | 23.3 | 0.057 |
| Kev 4B | LoRA + pointer head | 33.8M | ~90 min | 148 MB | 0.637 → **0.740** | 0.739 | 185 / 189 ms | 5.5 | 0.040 |
| *Decider 2B, zero-shot* | – | – | – | – | *0.740* | *0.745* | *143 / 163 ms* | *6.9* | *0.032* |
| *Gemma 4 26B-A4B LLM* | – | – | – | – | *0.740* | *0.736* | *660 / 894 ms* | *1.5* | *0.260* |

Training adds 8–12 points to every architecture, mainly by rescuing negative and positive tweets that
the zero-shot models hedged as neutral (at some cost on neutral tweets). Trained Kev 4B matches the best LLM and the best zero-shot
model. Trained Laya is the fastest route to ~72% (49 ms, 10 minutes of training). Kev's training times
are Mac-specific (no Apple GPU kernels for Qwen3.5's DeltaNet layers in training); on an NVIDIA GPU both
take minutes. Models are saved in `models/laya-tweet-sentiment`, `models/kev-0.8b-tweets`,
`models/kev-4b-tweets`. Details: [docs/reference/](docs/reference).

## Key-code docs

1. [docs/1-landscape.md](docs/1-landscape.md): what Jev is, the four families of reproductions, the Decision Index and what runs on a Mac
2. [docs/2-typed-questions.md](docs/2-typed-questions.md): how one typed question gets answered, end to end (worked example: Laya), why a head handles any number of options in one pass, why option order can matter
3. [docs/3-benchmark-method.md](docs/3-benchmark-method.md): benchmark method, the LLM prompts and the Kev HTTP client
4. [docs/4-zero-shot-reproductions.md](docs/4-zero-shot-reproductions.md): SemIf, openvons, Decider 2B / 4B v2 (and its letter-slot head), GLiNER2.5-Decide and CLM (with an MLX encoder), position bias, letter-logit readouts, adapters, **all results**, "isn't this just embeddings?"
5. [docs/5-snake.md](docs/5-snake.md): Snake. How six published Jev demos ask for a move, why the simple way fails
   (for Jev too), and the phrasing that works, tested on seven open models (Decider 2B/4B, Kev 4B, CLM 8B, GLiNER 340M/1B, Laya).
   Report page: `docs/snake-report/`
6. Reference only: [docs/reference/finetune-laya.md](docs/reference/finetune-laya.md), [docs/reference/finetune-kev.md](docs/reference/finetune-kev.md)

## Files

```
01_hello_laya.py            step 1: hello world
data.py                     TweetEval loader (balanced, seeded sample)
laya_classifier.py          Laya wrapper: classify() and batched classify_batch(); SENTIMENT_QUESTION
systemone_classifier.py     client for any System One HTTP server (Kev, or TypeSafe's hosted Jev)
llm_classifier.py           LM Studio wrapper (OpenAI API + JSON-schema enum, thinking off)
02_benchmark.py             one system -> results/runs/<name>.json
adapters/                   export_test_tweets.py, one adapter per engine, download helpers
07_import_predictions.py    adapter output -> results/runs/<name>.json (same metrics)
04_report.py                all runs -> results/REPORT.md
05_cascade.py               System One -> LLM confidence cascade -> results/cascades/
11_position_bias.py         option-order test analysis -> results/position_bias.json
run_kev.sh                  start a Kev server, benchmark it, stop it
scripts/                    setup_engines.sh, download_models.py (pinned revisions + SHA-256 check), fetch helpers
03_finetune_laya.py, 06_export_kev_data.py, run_kev_finetune.sh    reference fine-tunes
08_snake_server.py          step 8: Snake demo server (stdlib HTTP; snake/static/index.html)
09_snake_benchmark.py       step 9: Snake games per formulation and model
10_snake_probe.py           step 10: single-decision probe per formulation and model
snake/                      game + flood fill, the five formulations, engines (Decider, Laya, any /v1/systemone)
docs/page/                  tutorial page (template + build.py -> index.html)
docs/snake-report/          Snake report page (template + build.py -> index.html)
results/                    logs, raw adapter output, per-run JSON with every prediction, report
```

## Data and license

The tweets come from [TweetEval](https://huggingface.co/datasets/cardiffnlp/tweet_eval) (SemEval-2017 Task 4A).
Their text is not included in this repository: results refer to tweets by position (`t000`…) and by row in the
TweetEval test split, and `data/` is regenerated on demand (`uv run python adapters/export_test_tweets.py`,
`uv run python 06_export_kev_data.py`). Models and third-party engines are fetched by the scripts in `scripts/`
and keep their own licenses.

Code and documentation in this repository: [MIT](LICENSE).
