# Sentiment benchmark - TweetEval, 300 balanced test tweets

## Zero-shot

| System | Accuracy | Macro-F1 | p50 latency | p95 latency | Msgs/s | ECE |
|---|---|---|---|---|---|---|
| decider-4b-v2 | 0.750 | 0.751 | 258 ms | 296 ms | 3.8 | 0.056 |
| decider-2b | 0.740 | 0.745 | 143 ms | 163 ms | 6.9 | 0.032 |
| llm-google_gemma-4-26b-a4b-qat | 0.740 | 0.736 | 660 ms | 894 ms | 1.5 | 0.260 |
| jev | 0.737 | 0.723 | 260 ms | 355 ms | 3.6 | 0.154 |
| semif-9b | 0.730 | 0.707 | 320 ms | 349 ms | 3.1 | 0.080 |
| llm-google_gemma-4-26b-a4b-qat-simple | 0.723 | 0.715 | 388 ms | 447 ms | 2.6 | 0.277 |
| semif | 0.717 | 0.698 | 189 ms | 349 ms | 4.9 | 0.054 |
| llm-google_gemma-4-12b-qat | 0.713 | 0.714 | 2322 ms | 2841 ms | 0.4 | 0.287 |
| llm-qwen_qwen3.8-27b-simple | 0.710 | 0.694 | 2914 ms | 4689 ms | 0.3 | 0.290 |
| llm-google_gemma-4-12b-qat-simple | 0.697 | 0.695 | 1340 ms | 1482 ms | 0.7 | 0.303 |
| kev-9b | 0.690 | 0.695 | 448 ms | 498 ms | 2.2 | 0.052 |
| openvons | 0.687 | 0.617 | 301 ms | 307 ms | 3.3 | 0.305 |
| llm-qwen_qwen3.8-27b | 0.663 | 0.656 | 3309 ms | 3693 ms | 0.3 | 0.337 |
| gliner-decide | 0.637 | 0.635 | 62 ms | 72 ms | 15.7 | 0.061 |
| kev-4b | 0.637 | 0.646 | 261 ms | 307 ms | 3.8 | 0.107 |
| laya | 0.633 | 0.639 | 49 ms | 59 ms | 20.5 | 0.071 |
| gliner-decide-1b | 0.630 | 0.632 | 73 ms | 82 ms | 13.6 | 0.081 |
| laya-multilingual | 0.630 | 0.634 | 20 ms | 29 ms | 38.0 | 0.112 |
| clef-flash | 0.597 | 0.594 | 477 ms | 526 ms | 1.8 | 0.205 |
| kev-0.8b | 0.587 | 0.597 | 45 ms | 58 ms | 21.5 | 0.128 |
| embed-nomic | 0.567 | 0.537 | 13 ms | 16 ms | 74.2 | 0.071 |
| clm-8b | 0.517 | 0.451 | 167 ms | 186 ms | 5.9 | 0.271 |
| clm-raw | 0.343 | 0.193 | 166 ms | 178 ms | 6.0 | 0.213 |

## Fine-tuned on 3,000 training tweets (reference)

| System | Accuracy | Macro-F1 | p50 latency | p95 latency | Msgs/s | ECE |
|---|---|---|---|---|---|---|
| kev-4b-tweets | 0.740 | 0.739 | 185 ms | 189 ms | 5.5 | 0.040 |
| laya-finetuned | 0.717 | 0.711 | 49 ms | 66 ms | 19.7 | 0.048 |
| kev-0.8b-tweets | 0.710 | 0.701 | 43 ms | 47 ms | 23.3 | 0.057 |

ECE = expected calibration error of the top-class confidence (lower is better). LLM answers carry no probabilities, so their confidence is always 1.0. `-simple` = LLM with the bare instruction prompt; `embed-nomic` = nearest label description by embedding cosine.
