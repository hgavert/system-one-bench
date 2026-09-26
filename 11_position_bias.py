"""Step 11 - Analyse the position-bias runs (adapters/position_bias.py): does option order change answers?

For every engine: accuracy per order, accuracy by where the correct answer is listed, how often a tweet's
answer flips with nothing but the order, how often each position is picked (33% each if order-blind), and
how much the probabilities move. Writes results/position_bias.json.

  uv run python 11_position_bias.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import chisquare

gold = {json.loads(l)["id"]: json.loads(l)["gold"] for l in open("data/test_tweets.jsonl")}
report = {}
for path in sorted(Path("results/raw").glob("posbias_*.jsonl")):
    engine = path.stem.removeprefix("posbias_")
    rows = [json.loads(l) for l in path.open()]
    by_order, by_tweet = defaultdict(list), defaultdict(list)
    for r in rows:
        by_order[tuple(r["order"])].append(r)
        by_tweet[r["id"]].append(r)
    if len(by_order) < 6:
        continue
    acc_order = {" / ".join(o): sum(r["pred"] == gold[r["id"]] for r in rs) / len(rs) for o, rs in by_order.items()}
    # accuracy by the position of the correct answer
    pos_hits = defaultdict(list)
    for r in rows:
        pos_hits[r["order"].index(gold[r["id"]]) + 1].append(r["pred"] == gold[r["id"]])
    acc_by_gold_pos = {p: sum(v) / len(v) for p, v in sorted(pos_hits.items())}
    # which position gets picked
    picks = Counter(r["order"].index(r["pred"]) + 1 for r in rows)
    pick_share = {p: picks[p] / len(rows) for p in (1, 2, 3)}
    chi_p = chisquare([picks[p] for p in (1, 2, 3)]).pvalue
    # stability per tweet
    flips = sum(len({r["pred"] for r in rs}) > 1 for rs in by_tweet.values())
    def largest_swing(rs):            # biggest change in any label's probability across the 6 orders
        return max(max(r["probs"][k] for r in rs) - min(r["probs"][k] for r in rs) for k in rs[0]["probs"])
    swing = sum(largest_swing(rs) for rs in by_tweet.values()) / len(by_tweet)
    report[engine] = {
        "accuracy_per_order": acc_order,
        "accuracy_min_max": [min(acc_order.values()), max(acc_order.values())],
        "accuracy_by_correct_position": acc_by_gold_pos,
        "pick_share_by_position": pick_share, "pick_chi2_p": chi_p,
        "tweets_whose_answer_flips": flips / len(by_tweet),
        "mean_max_probability_swing": swing,
    }
    r = report[engine]
    print(f"\n{engine}")
    print(f"  accuracy over the 6 orders: {r['accuracy_min_max'][0]:.3f} - {r['accuracy_min_max'][1]:.3f}")
    print("  accuracy when the correct answer is listed "
          + ", ".join(f"{['1st', '2nd', '3rd'][p - 1]}: {a:.3f}" for p, a in acc_by_gold_pos.items()))
    print("  picks by position: " + ", ".join(f"{['1st', '2nd', '3rd'][p - 1]} {s:.1%}" for p, s in pick_share.items())
          + f"   (chi-square vs 33/33/33: p = {chi_p:.2g})")
    print(f"  tweets whose answer changes with order alone: {r['tweets_whose_answer_flips']:.1%}")
    print(f"  mean largest probability swing per tweet: {r['mean_max_probability_swing']:.3f}")
Path("results/position_bias.json").write_text(json.dumps(report, indent=1))
print("\nsaved results/position_bias.json")
