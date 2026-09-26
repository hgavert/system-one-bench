"""Step 4 - Combine every results/runs/*.json into one comparison (results/REPORT.md, results/summary.json).

Zero-shot runs form the main table; task-fine-tuned runs (names ending in -tweets, or laya-finetuned)
are listed separately for reference.
"""
import json
from pathlib import Path

runs = [json.loads(p.read_text()) for p in sorted(Path("results/runs").glob("*.json"))]
runs.sort(key=lambda r: -r["summary"]["accuracy"])
fine_tuned = lambda n: n == "laya-finetuned" or n.endswith("-tweets")


def table(rows):
    lines = ["| System | Accuracy | Macro-F1 | p50 latency | p95 latency | Msgs/s | ECE |", "|" + "---|" * 7]
    for r in rows:
        s = r["summary"]
        lines.append(f"| {r['name']} | {s['accuracy']:.3f} | {s['macro_f1']:.3f} | {s['latency_ms_p50']:.0f} ms | "
                     f"{s['latency_ms_p95']:.0f} ms | {s['throughput_msgs_per_s']:.1f} | {s['ece']:.3f} |")
    return "\n".join(lines)


zs = table([r for r in runs if not fine_tuned(r["name"])])
ft = table([r for r in runs if fine_tuned(r["name"])])
print(zs, "\n\nfine-tuned (reference):\n" + ft)
Path("results/REPORT.md").write_text(
    f"# Sentiment benchmark - TweetEval, {runs[0]['summary']['n']} balanced test tweets\n\n"
    f"## Zero-shot\n\n{zs}\n\n## Fine-tuned on 3,000 training tweets (reference)\n\n{ft}\n\n"
    "ECE = expected calibration error of the top-class confidence (lower is better). LLM answers carry "
    "no probabilities, so their confidence is always 1.0. `-simple` = LLM with the bare instruction prompt; "
    "`embed-nomic` = nearest label description by embedding cosine.\n")
Path("results/summary.json").write_text(json.dumps(
    [{"name": r["name"], "system": r["system"], **r["summary"]} for r in runs], indent=1))
print("\nsaved results/REPORT.md and results/summary.json")
