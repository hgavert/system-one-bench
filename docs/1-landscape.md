# 1 · Jev and its open-source reproductions

*Researched 23 September 2026. The ecosystem is about a week old and changes daily.*

## What Jev is

Jev is a proprietary model from **TypeSafe AI**, released on 15 September 2026. It is a *System One*
model: instead of generating text, it takes

* a **state** (a string, a JSON document, or a list of conversation turns), and
* a set of **typed questions** declared up front,

and returns a typed answer with probabilities for every question, in one pass:

| Type     | You declare                             | You get back                                  |
|----------|-----------------------------------------|-----------------------------------------------|
| `choice` | a closed set of labels (+ descriptions) | the label, and a probability per label        |
| `score`  | an ordered list of levels               | expected level (float), probability per level |
| `noul`   | a yes/no statement                      | P(true)                                       |

The API is a single endpoint, `POST /v1/systemone` with `{"state", "questions"}`. Because the answer
space is fixed in advance, there is nothing to parse and nothing to hallucinate. Sentiment analysis
is the textbook `choice` question.

## How the reproductions differ

Dozens of open reproductions appeared within days. They fall into five families, and this tutorial
runs at least one of each:

| Family | How it answers | Trains weights? | Examples run here |
|---|---|---|---|
| **Encoder + head** | A BERT-style encoder reads question + options + state; a small head scores one marker token per option | yes, whole model | Laya, Laya-multilingual, GLiNER2.5-Decide (340M, 1B) |
| **LoRA + pointer head** | A causal LLM with a LoRA adapter; a `<decide>` token's state is dotted with each option's end-token state | adapter + head | Kev 0.8B / 4B / 9B |
| **Full fine-tune, letter logits** | A causal LLM fine-tuned to put its answer in the logit of an option letter | whole model | Decider 2B, Decider 4B v2 |
| **Inference technique** | A *stock* LLM; the prompt lists lettered options and the answer is read from the next-token logits of the letters | **nothing** | SemIf, openvons |
| **Contrastive bi-encoder** | A frozen LLM embeds state+question and each option *separately*; small trained heads align the two spaces; answer = softmax of cosine | projection heads | CLM 8B |

The last family is the purest zero-shot baseline: it shows how much of "Jev" is just careful
prompting plus reading logits instead of sampling text.

## The Decision Index

[multimodalart's Jev Decision Index](https://huggingface.co/spaces/multimodalart/jev-decision-index)
(edition 0.1, 22 September 2026) scores 31 reproductions against real Jev on 37 public benchmarks
(132k requests), each on one NVIDIA RTX PRO 6000 (96 GB). Its harness is open:
[apolinario/decision-index](https://github.com/apolinario/decision-index). The ranking, and whether
each entrant could run on this tutorial's Apple M5 with 32 GB:

| # | Reproduction | Family | Base | Index score | Run here? |
|---|---|---|---|---|---|
| 1 | Jevfire | inference technique | Qwen3.8-27B | 40.9 | ❌ CUDA + vLLM sidecar only |
| 2 | JoshuaSP diffusiongemma (open-jev) | inference technique | diffusiongemma-26B-A4B | 40.8 | ❌ CUDA / Modal only |
| 3 | Decider 35B-A3B | full fine-tune | Qwen3.5-35B-A3B | 39.4 | ❌ 65 GB bf16, or NVFP4 (Blackwell only) |
| 4 | razorback16 diffusiongemma NVFP4 | inference technique | diffusiongemma-26B-A4B | 35.6 | ❌ NVFP4 / vLLM |
| 5 | Solomon v1.1 | head / adapter | Qwen3.8-27B | 34.9 | ❌ its MLX build needs ~60 GB of memory |
| 6 | **Kev 9B** | LoRA + head | Qwen3.5-9B-Base | 33.0 | ✅ MLX |
| 7 | **Kev 4B** | LoRA + head | Qwen3.5-4B-Base | 28.9 | ✅ MLX |
| 9 | open-jev (pngwn) | LoRA | Qwen3.5-4B-Base | 27.1 | ❌ weights only, no inference code |
| 10 | **openvons** | inference technique | Qwen3-4B-Instruct-2507 | 26.5 | ✅ via `mlx_lm.server` |
| 11 | **SemIf** | inference technique | Qwen3.5-4B-Base | 26.0 | ✅ native MLX backend |
| 12 | Decision-1.0-Nox | head / adapter | Qwen3.5-4B | 25.4 | ❌ runtime pinned to AMD ROCm + Triton |
| 13 | **Decider 2B** | full fine-tune | Qwen3.5-2B-Base | 24.8 | ✅ PyTorch MPS (without its CUDA graphs) |
| 14 | mini-jev | inference technique | Qwen3-4B-Instruct-2507 | 24.3 | ⏭ same base and method as openvons |
| 17 | **Kev 0.6B** *(we ran the newer Kev 0.8B)* | LoRA + head | Qwen3-0.6B-Base | 7.6 | ✅ |
| 30 | **Laya** | encoder + head | ModernBERT-large | 1.5 | ✅ PyTorch MPS |
| – | **Decider 4B v2** (24 Sept, after index 0.1) | full fine-tune + LoRA stage | Qwen3.5-4B-Base | – | ✅ PyTorch MPS |
| (21, 27) | **GLiNER2.5-Decide** 340M / 1B (the index ran the older GLiNER 2.5 base/small) | encoder + head | DeBERTa-v3-large / ~1B encoder | – | ✅ PyTorch MPS |
| – | **CLM 8B** (released 24 Sept, after index 0.1) | contrastive bi-encoder | Qwen3-8B | – | ✅ vLLM encoder replaced by an MLX one |

The index is a broad test: knowledge, retrieval, tool use, agent games. A model near the bottom of
it, such as Laya, can still be perfectly usable for one narrow task like sentiment, and vice versa.
That is why this tutorial measures every runnable entrant on **one** task with **one** harness.

## Why the tutorial starts with Laya

Laya is not the strongest reproduction, but it is the simplest one to learn from: one
`pip install laya`, one `laya.load(...)`, no server, and 421M parameters that run in ~45 ms on a
laptop GPU. The hello world ([`01_hello_laya.py`](../01_hello_laya.py)) uses it, and every other
engine then receives the *same* question dict.

## Sources

* [Jev Decision Index](https://huggingface.co/spaces/multimodalart/jev-decision-index) · [harness](https://github.com/apolinario/decision-index)
* [Jev (AI model), Wikipedia](https://en.wikipedia.org/wiki/Jev_(AI_model)) · [TechCrunch](https://techcrunch.com/2026/09/18/a-new-kind-of-ai-model-from-a-chatgpt-inventor-is-thrilling-developers/)
* [Laya](https://huggingface.co/convaiinnovations/laya) · [Kev](https://github.com/jaredpalmer/kev) · [SemIf](https://github.com/TheoLeeCJ/openjev) · [openvons](https://github.com/genai-craft/openvons) · [Decider 2B](https://huggingface.co/Mapika/decider-2b)
* [Decider 4B v2](https://huggingface.co/Mapika/decider-4b/tree/v2) · [GLiNER2.5-Decide](https://huggingface.co/fastino/GLiNER2.5-Decide) · [GLiNER2.5-Decide-1B](https://huggingface.co/fastino/GLiNER2.5-Decide-1B)
* [CLM](https://github.com/Contrastive-LM/CLM) · [CLM-v0.1-8B](https://huggingface.co/Contrastive-LM/CLM-v0.1-8B)
* [Jevfire](https://github.com/kikoncuo/jevfire) · [JoshuaSP open-jev](https://github.com/JoshuaSP/open-jev) · [Decider 35B-A3B](https://huggingface.co/Mapika/decider-35b-a3b-nvfp4) · [Solomon](https://huggingface.co/DoccyHealth/Solomon) · [Decision-1.0-Nox](https://huggingface.co/llm-semantic-router/Decision-1.0-Nox-4B) · [mini-jev](https://github.com/r-ms/mini-jev)
