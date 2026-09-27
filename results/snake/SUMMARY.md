10 seeds, 12x12 board, max 500 steps.

| Controller | Food eaten (mean / best) | Steps | Died | Starved | Model calls | Code-only ticks | Latency p50 / mean | Tokens/call |
|---|---|---|---|---|---|---|---|---|
| Decider 2B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 357 / 358 ms | 361 |
| Decider 2B · Relative, in words | 0.1 / 1 | 145 | 0% | 10 | 1446 | 0 | 185 / 185 ms | 160 |
| Decider 2B · Facts in the options | 1.2 / 4 | 175 | 0% | 10 | 1603 | 144 | 448 / 456 ms | 477 |
| Decider 2B · Judged options | 36.9 / 46 | 477 | 20% | 0 | 4419 | 348 | 141 / 145 ms | 120 |
| Decider 2B · Judged, plain wording | 34.9 / 46 | 459 | 50% | 0 | 4247 | 346 | 140 / 141 ms | 121 |
| Decider 2B · Composed questions | 38.3 / 44 | 486 | 20% | 0 | 4535 | 326 | 308 / 311 ms | 303 |
| Decider 4B · Raw board | 0.1 / 1 | 9 | 100% | 0 | 86 | 0 | 557 / 556 ms | 360 |
| Decider 4B · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 310 / 312 ms | 160 |
| Decider 4B · Facts in the options | 3.6 / 7 | 211 | 0% | 10 | 2057 | 55 | 813 / 773 ms | 524 |
| Decider 4B · Judged options | 29.3 / 43 | 312 | 90% | 0 | 2944 | 177 | 257 / 259 ms | 121 |
| Decider 4B · Judged, plain wording | 30.8 / 43 | 332 | 90% | 0 | 3111 | 211 | 261 / 260 ms | 121 |
| Decider 4B · Composed questions | 32.7 / 40 | 380 | 70% | 0 | 3527 | 272 | 502 / 504 ms | 304 |
| Kev 4B · Raw board | 9.0 / 17 | 92 | 100% | 0 | 920 | 0 | 265 / 268 ms | 243 |
| Kev 4B · Relative, in words | 13.1 / 22 | 166 | 100% | 0 | 1664 | 0 | 207 / 208 ms | 138 |
| Kev 4B · Facts in the options | 17.2 / 25 | 411 | 0% | 4 | 3884 | 230 | 332 / 334 ms | 371 |
| Kev 4B · Judged options | 29.5 / 41 | 321 | 100% | 0 | 2990 | 218 | 108 / 108 ms | 108 |
| Kev 4B · Judged, plain wording | 25.3 / 34 | 251 | 100% | 0 | 2334 | 175 | 108 / 110 ms | 108 |
| CLM 8B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 284 / 254 ms | 183 |
| CLM 8B · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 0 / 5 ms | – |
| CLM 8B · Facts in the options | 1.8 / 6 | 167 | 10% | 9 | 1604 | 67 | 0 / 295 ms | – |
| CLM 8B · Judged options | 0.0 / 0 | 144 | 0% | 10 | 1397 | 43 | 0 / 0 ms | – |
| CLM 8B · Judged, plain wording | 36.2 / 44 | 461 | 50% | 0 | 4305 | 308 | 0 / 4 ms | – |
| CLM 8B · Composed questions | 0.0 / 0 | 144 | 0% | 10 | 1397 | 43 | 0 / 0 ms | – |
| GLiNER2.5-Decide · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 256 / 256 ms | – |
| GLiNER2.5-Decide · Relative, in words | 0.0 / 0 | 144 | 0% | 10 | 1440 | 0 | 102 / 103 ms | – |
| GLiNER2.5-Decide · Facts in the options | 0.4 / 2 | 153 | 0% | 10 | 1400 | 130 | 373 / 375 ms | – |
| GLiNER2.5-Decide · Judged options | 2.7 / 15 | 181 | 0% | 10 | 1748 | 66 | 72 / 71 ms | – |
| GLiNER2.5-Decide · Judged, plain wording | 26.3 / 37 | 371 | 50% | 1 | 3440 | 273 | 71 / 70 ms | – |
| GLiNER2.5-Decide · Composed questions | 39.4 / 44 | 497 | 10% | 0 | 4606 | 368 | 169 / 166 ms | – |
| GLiNER2.5-Decide-1B · Raw board | 0.0 / 0 | 7 | 100% | 0 | 70 | 0 | 268 / 273 ms | – |
| GLiNER2.5-Decide-1B · Relative, in words | 1.7 / 6 | 121 | 30% | 7 | 1211 | 0 | 123 / 123 ms | – |
| GLiNER2.5-Decide-1B · Facts in the options | 0.3 / 1 | 151 | 0% | 10 | 1398 | 115 | 317 / 320 ms | – |
| GLiNER2.5-Decide-1B · Judged options | 15.3 / 25 | 315 | 40% | 4 | 2837 | 317 | 84 / 82 ms | – |
| GLiNER2.5-Decide-1B · Judged, plain wording | 13.7 / 24 | 324 | 30% | 6 | 2849 | 387 | 81 / 82 ms | – |
| GLiNER2.5-Decide-1B · Composed questions | 3.8 / 8 | 235 | 0% | 10 | 2242 | 106 | 196 / 196 ms | – |
| Laya · Facts in the options | 0.5 / 2 | 155 | 0% | 10 | 1442 | 111 | 100 / 100 ms | 336 |
| Laya · Judged options | 0.0 / 0 | 144 | 0% | 10 | 1305 | 135 | 38 / 39 ms | 99 |
| Keyword scorer (no model) · Raw board | 0.2 / 1 | 28 | 100% | 0 | 275 | 0 | 0 / 0 ms | – |
| Keyword scorer (no model) · Relative, in words | 0.2 / 1 | 23 | 100% | 0 | 232 | 0 | 0 / 0 ms | – |
| Keyword scorer (no model) · Facts in the options | 1.3 / 4 | 207 | 0% | 10 | 2012 | 59 | 0 / 0 ms | – |
| Keyword scorer (no model) · Judged options | 39.0 / 45 | 499 | 0% | 1 | 4533 | 458 | 0 / 0 ms | – |
| Keyword scorer (no model) · Judged, plain wording | 38.3 / 42 | 477 | 20% | 0 | 4329 | 443 | 0 / 0 ms | – |
| Keyword scorer (no model) · Composed questions | 37.4 / 44 | 484 | 20% | 0 | 4533 | 310 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Raw board | 0.0 / 0 | 31 | 100% | 0 | 311 | 0 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Relative, in words | 0.3 / 1 | 40 | 100% | 0 | 401 | 0 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Facts in the options | 1.7 / 5 | 236 | 0% | 9 | 2315 | 47 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Judged options | 39.1 / 44 | 499 | 10% | 0 | 4499 | 493 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Judged, plain wording | 35.3 / 42 | 456 | 20% | 0 | 4131 | 425 | 0 / 0 ms | – |
| Keyword scorer, sampled T=0.5 · Composed questions | 37.6 / 44 | 484 | 20% | 0 | 4530 | 313 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Raw board | 0.0 / 0 | 31 | 100% | 0 | 311 | 0 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Relative, in words | 0.3 / 1 | 40 | 100% | 0 | 401 | 0 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Facts in the options | 2.5 / 7 | 265 | 0% | 9 | 2556 | 91 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Judged options | 37.0 / 42 | 496 | 10% | 0 | 4474 | 489 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Judged, plain wording | 33.7 / 44 | 407 | 50% | 0 | 3738 | 335 | 0 / 0 ms | – |
| Keyword scorer, sampled T=1 · Composed questions | 39.5 / 44 | 484 | 20% | 0 | 4520 | 323 | 0 / 0 ms | – |
| *random (code only)* | 0.5 / 2 | 175 | 0% | 10 | 0 | 0 | – | – |
| *greedy (code only)* | 21.0 / 32 | 213 | 100% | 0 | 0 | 0 | – | – |
| *greedy-safe (code only)* | 41.1 / 44 | 484 | 20% | 0 | 0 | 0 | – | – |
