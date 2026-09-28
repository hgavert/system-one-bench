10 seeds, 12x12 board, max 500 steps.

| Controller | Food eaten (mean / best) | Steps | Died | Starved | Model calls | Code-only ticks | Latency p50 / mean | Tokens/call |
|---|---|---|---|---|---|---|---|---|
| Jev (hosted) · Raw board | 8.6 / 14 | 76 | 100% | 0 | 762 | 0 | 269 / 275 ms | 547 |
| Jev (hosted) · Relative, in words | 0.2 / 1 | 152 | 0% | 10 | 1523 | 0 | 266 / 273 ms | 450 |
| Jev (hosted) · Facts in the options | 37.3 / 44 | 467 | 20% | 0 | 4264 | 405 | 268 / 277 ms | 713 |
| Jev (hosted) · Judged options | 40.6 / 51 | 500 | 0% | 0 | 4510 | 490 | 268 / 276 ms | 402 |
| Jev (hosted) · Judged, plain wording | 38.9 / 47 | 446 | 40% | 0 | 4082 | 382 | 267 / 276 ms | 402 |
| Jev (hosted) · Composed questions | 40.9 / 44 | 484 | 20% | 0 | 4542 | 301 | 271 / 280 ms | 579 |
| *random (code only)* | 0.5 / 2 | 175 | 0% | 10 | 0 | 0 | – | – |
| *greedy (code only)* | 21.0 / 32 | 213 | 100% | 0 | 0 | 0 | – | – |
| *greedy-safe (code only)* | 41.1 / 44 | 484 | 20% | 0 | 0 | 0 | – | – |
