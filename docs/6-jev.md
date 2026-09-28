# 6 · Hosted Jev on the same three tests

*Run 28 September 2026 against `jev-latest`, served as `jev-1.13.0`.*

The first three tests compared open reproductions of Jev without Jev itself: we had no TypeSafe API key. With one,
hosted Jev answers exactly the requests the open models answered: the same 300 tweets, Snake seeds, probe states
and Finnish items, and the same question dicts. Nothing was tuned for Jev.

About 26,600 requests in all, roughly 13M input tokens (about $0.55 at the list price of $0.042 per million; 10M of them in the Snake games). Jev
answered the same request identically when repeated, so each test was run once.

| Test | Requests | Result files |
|---|--:|---|
| Sentiment, 300 tweets | 300 | `results/runs/jev.json`, `results/REPORT.md` |
| Option order, 6 orders | 1,800 | `results/raw/posbias_jev.jsonl`, `results/position_bias.json` |
| Cascade to Gemma 26B | 0 (reuses the sentiment run) | `results/cascades/jev.json` |
| Finnish, 4 datasets × 3 conditions | 3,300 | `results/finnish/runs/jev.jsonl`, `results/finnish/REPORT.md` |
| Snake probe, 250 states × 6 requests | 1,500 | `results/snake/probe-jev.json` |
| Snake games, 6 requests × 10 seeds | 19,683 | `results/snake/SUMMARY-jev.md` |

## Summary

* **Sentiment: Jev is tied with the best open models, not ahead.** 0.737 vs Decider 2B 0.740 and Gemma 4 26B 0.740
  (paired p = 1.0 for both). It gets negative tweets right more often (93/100) but neutral ones least often
  (47/100) and is less well calibrated (ECE 0.154 vs 0.032 for Decider 2B).
* **Option order barely matters to Jev**: its answer flips on 5.0% of tweets with nothing but the order changed,
  with no favoured position. Of the models that read the options together, this is the lowest.
* **Finnish is where Jev leads.** Jev is best or tied-best on all four datasets. In reading comprehension, fully in
  Finnish, it scores 0.950 against 0.903 for Decider 4B v2 and 0.863 for the 27B LLM. It also loses the least from
  English to Finnish (−1.3 points). This holds although TypeSafe's own docs call non-English "less reliable".
* **Snake: Jev can read a board, but the published requests still fail in play.** On single moves from the raw
  board Jev picks a good move on 97% of hard states (open models: 0–79%). In games it still hits its own body every
  time (8.6 food). The "relative, in words" request makes it turn right on 82% of moves and starve in every game,
  as in nadeem4's published Jev run.
* **With judged options Jev plays as well as the best code**: 40.6 food per game, died in none of 10 games (Decider
  2B 36.9, greedy-safe code 41.1). With sorrycc's "facts in the options", which defeated every open model
  (0.5–17.2), Jev eats 37.3.

## 6.1 Sentiment

Same 300 balanced TweetEval test tweets, same `SENTIMENT_QUESTION`. `uv run python 02_benchmark.py jev`.

| System | Accuracy | Macro-F1 | Recall neg / neu / pos | ECE |
|---|--:|--:|---|--:|
| Decider 4B v2 | 0.750 | 0.751 | 86 / 78 / 61 | 0.056 |
| Decider 2B | 0.740 | 0.745 | 75 / 73 / 74 | 0.032 |
| LLM Gemma 4 26B-A4B | 0.740 | 0.736 | 91 / 56 / 75 | 0.260 |
| **Jev** | **0.737** | **0.723** | **93 / 47 / 81** | **0.154** |
| SemIf · Qwen3.5-9B-Base | 0.730 | 0.707 | 91 / 39 / 89 | 0.080 |
| Kev 9B | 0.690 | 0.695 | 74 / 63 / 70 | 0.052 |
| Laya | 0.633 | 0.639 | 65 / 62 / 63 | 0.071 |

Paired on the same tweets (exact McNemar): Jev vs Decider 4B v2 p = 0.72, vs Decider 2B p = 1.0, vs Gemma 26B
p = 1.0, vs SemIf p = 0.39, vs Kev 9B p = 0.07, vs Laya p = 0.002. So Jev is in the top group but
not distinguishable within it.

Jev's p50 latency is 260 ms, but that includes the network round trip from the laptop to `api.typesafe.ai`, so it is
not comparable with the local rows.

**Cascade** (`05_cascade.py --fast jev`): sending Jev's low-confidence answers to Gemma 26B helps little. The best
result is 0.747 at a 0.6 threshold with 12% of tweets escalated, against 0.753 with Decider 2B at 6%. Jev is often
confidently wrong on neutral tweets: on the 53 it gets wrong, its median confidence is 0.90. A confidence
gate doesn't catch those errors.

**Option order** (`adapters/position_bias.py jev`, `11_position_bias.py`):

| | Jev |
|---|--:|
| Accuracy over the 6 orders | 0.727 – 0.740 |
| Accuracy with the right answer listed 1st / 2nd / 3rd | 0.730 / 0.747 / 0.728 |
| Picks by position | 32.7 / 34.3 / 32.9% (χ² p = 0.66) |
| Tweets whose answer flips with order alone | **5.0%** (Decider 2B 5.7%, others 10–23%, CLM 0%) |

Jev's probabilities come rounded to two decimals; the adapter lists Jev's own `choice` first so a tie is broken its way.

## 6.2 Finnish

`uv run python 12_finnish_benchmark.py --engine jev --workers 4`: the same 300 seeded items per dataset, three
conditions. Every number per condition is in `results/finnish/REPORT.md`.

Everything in Finnish, accuracy (±5 points on 300 items); last column: mean change from English to Finnish on the same
SIB, Belebele and MASSIVE items.

| Model | SIB topic | Belebele reading | MASSIVE intent* | ScandiSent-fi | EN → FI, same items |
|---|--:|--:|--:|--:|--:|
| **Jev** | **0.873** | **0.950** | 0.953 | 0.947 | **−1.3** |
| Decider 4B v2 | 0.833 | 0.903 | **0.963** | 0.913 | −2.1 |
| Kev 9B | 0.863 | 0.803 | 0.913 | 0.947 | −1.7 |
| Kev 4B | 0.860 | 0.703 | 0.937 | 0.913 | −1.9 |
| Decider 2B | 0.803 | 0.800 | 0.893 | 0.903 | −6.9 |
| *LLM Qwen 3.8 27B* | *0.857* | *0.863* | *0.957* | ***0.953*** | *−3.6* |

\*Decider was trained on MASSIVE's training split, so that column is not zero-shot for Decider.

Paired on the same items, all in Finnish:

| Jev vs | SIB | Belebele | MASSIVE | ScandiSent |
|---|---|---|---|---|
| Decider 4B v2 | 19 vs 7, p = 0.03 | 17 vs 3, **p = 0.003** | 3 vs 6, p = 0.51 | 14 vs 4, p = 0.03 |
| Qwen 3.8 27B | 13 vs 8, p = 0.38 | 28 vs 2, **p < 0.001** | 8 vs 9, p = 1.0 | 2 vs 4, p = 0.69 |

("19 vs 7" = items only Jev got right vs items only the other model got right.) The clear gap is reading
comprehension. Elsewhere Jev ranges from level with the best open models to a few points ahead of them. The question
language doesn't matter (Finnish question vs English question within ±2 points), and probabilities stay calibrated
(ECE ≤ 0.07 everywhere). On Belebele Jev does equally well whichever of the four positions holds the right answer
(0.93–0.97).

## 6.3 Snake

**Probe** (`10_snake_probe.py --engine jev`): single moves on fixed states, "good" as judged by code. The hard set
holds 100 states where going straight is legal but not good.

| Request | Jev | Decider 2B | Decider 4B v2 | Kev 4B | CLM 8B | GLiNER 340M | Keyword scorer |
|---|--:|--:|--:|--:|--:|--:|--:|
| Raw board | **0.97** | 0.05 | 0.10 | 0.79 | 0.25 | 0.00 | 0.33 |
| Relative, in words | 0.69 | 0.46 | 0.54 | **0.93** | 0.45 | 0.59 | 0.32 |
| Facts in the options | **0.96** | 0.10 | 0.46 | 0.31 | 0.19 | 0.00 | 0.51 |
| Judged + heading in state | **1.00** | 0.57 | 1.00 | 1.00 | 0.89 | 0.28 | 1.00 |
| Judged options | **1.00** | 1.00 | 1.00 | 1.00 | 0.89 | 0.86 | 1.00 |
| Judged, plain wording | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 | 0.90 | 1.00 |

Jev is the only model that reads the raw board and the facts well. Its one weak request is the relative one.

**Games** (`09_snake_benchmark.py --engine jev --summary results/snake/SUMMARY-jev.md`): 12×12, seeds 0–9,
500-step cap, starvation after 144 steps without food. The code baselines were re-run on the same seeds and match
`results/snake/SUMMARY.md` exactly.

| Request | Jev food / game | Best | Died | Best open model with this request |
|---|--:|--:|--:|---|
| Raw board | 8.6 | 14 | 10 of 10 (own body) | Kev 4B 9.0, died 10 of 10 |
| Relative, in words | 0.2 | 1 | 0; starved 10 of 10 | Kev 4B 13.1, died 10 of 10 |
| Facts in the options | **37.3** | 44 | 2 of 10 | Kev 4B 17.2 |
| Judged options | **40.6** | **51** | **0 of 10** | Decider 2B 36.9, died 2 of 10 |
| Judged, plain wording | 38.9 | 47 | 4 of 10 | CLM 8B 36.2 |
| Composed questions | **40.9** | 44 | 2 of 10 | GLiNER 340M 39.4 |
| *code: greedy + dead-end check* | *41.1* | *44* | *2 of 10* | |
| *no model: keyword scorer, judged* | *39.0* | *45* | *0 of 10* | |

* **The published Jev result reproduces.** With the relative request (nadeem4's phrasing) Jev picked `TURN_RIGHT`
  on 82% of moves and circled until it starved in all ten games. nadeem4 reported 71% right turns and 1.8 food on a
  10×10 board.
* **Reading the board is not the same as playing from it.** Given the raw grid, Jev picks a good single move 97% of
  the time in the probe, yet every game ended with it hitting its own body after about 76 steps. The probe only checks
  food distance and dead ends, not the longer-term room a growing body needs.
* **Given code's facts (flood fill, distances), Jev plays well on its own**, which no open model did. With verdicts
  in the options it is as good as greedy code and the keyword scorer. So [§5.7](5-snake.md)'s conclusion still
  holds: once the options carry verdicts, a phrase table plays about as well as Jev.

Jev's latency was about 270 ms per move over the network, with the six requests running in parallel.

## 6.4 Notes

* Engine specs: `jev` or `jev:<model>` in `02_benchmark.py`, `adapters/position_bias.py` and every script that
  takes `--engine` (Snake, Finnish). The key is `JEV_API_KEY` in `.env`. `jev_client.py` retries 429 / 529 /
  5xx with exponential backoff, as TypeSafe asks.
* Jev rounds probabilities to 2 decimals. Answers are read from its `choice` field. ECE is computed from the
  rounded values.
* Only zero-shot results. Jev can't be fine-tuned, so the fine-tuning reference table has no Jev row.
* Not run: the CLM option-wording variants (`adapters/clm_phrasing.py`, hard-wired to CLM's server), nadeem4's
  exact arena (10×10, starving after 60 steps), and the Decision Index harness.
