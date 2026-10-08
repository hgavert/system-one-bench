"""Markdown twin of the report page: docs/sentiment-report.md + docs/page/accuracy.svg.

Built from the same results/ files as docs/page/index.html (docs/page/build.py calls this), so the two
never disagree.
"""
import json
from pathlib import Path

ROOT = Path(".")
OUT_MD = ROOT / "docs/sentiment-report.md"
OUT_SVG = ROOT / "docs/page/accuracy.svg"

S = {s["name"]: s for s in json.loads(Path("results/summary.json").read_text())}
POS = json.loads(Path("results/position_bias.json").read_text()) if Path("results/position_bias.json").exists() else {}
CAS = {n: json.loads(Path(f"results/cascades/{n}.json").read_text())["rows"]
       for n in ("decider-2b", "semif") if Path(f"results/cascades/{n}.json").exists()}

FAMILY = {"laya": "enc", "laya-multilingual": "enc", "gliner-decide": "enc", "gliner-decide-1b": "enc",
          "kev-0.8b": "kev", "kev-4b": "kev", "kev-9b": "kev", "semif": "tech", "semif-9b": "tech", "openvons": "tech",
          "decider-2b": "dec", "decider-4b-v2": "dec", "clm-8b": "clm", "embed-nomic": "emb", "clm-raw": "emb",
          "clef-flash": "clef"}
FAMNAME = {"enc": "Encoder + head", "kev": "LoRA + pointer", "dec": "Full fine-tune", "tech": "Inference technique",
           "clm": "Contrastive bi-encoder", "clef": "Backbone + joint head", "emb": "Embedding baseline", "llm": "LLM (LM Studio)"}
COLOR = {"enc": "#1D5E8C", "kev": "#B7791F", "dec": "#B5536B", "tech": "#2E8C82", "clm": "#8A6D3B", "clef": "#C2570C",
         "emb": "#6F7C8C", "llm": "#7A4E9E"}
PRETTY = {"laya": "Laya", "laya-multilingual": "Laya multilingual", "kev-0.8b": "Kev 0.8B", "kev-4b": "Kev 4B",
          "kev-9b": "Kev 9B", "semif": "SemIf · Qwen3.5-4B", "semif-9b": "SemIf · Qwen3.5-9B (variant)",
          "openvons": "openvons · Qwen3-4B", "decider-2b": "Decider 2B", "decider-4b-v2": "Decider 4B v2",
          "gliner-decide": "GLiNER2.5-Decide", "gliner-decide-1b": "GLiNER2.5-Decide-1B", "clm-8b": "CLM 8B", "clef-flash": "Clef-flash",
          "clm-raw": "Qwen3-8B raw embeddings", "embed-nomic": "Embeddings (nomic)",
          "llm-google_gemma-4-26b-a4b-qat": "Gemma 4 26B-A4B", "llm-google_gemma-4-12b-qat": "Gemma 4 12B",
          "llm-qwen_qwen3.8-27b": "Qwen 3.8 27B", "llm-google_gemma-4-26b-a4b-qat-simple": "Gemma 4 26B · bare prompt",
          "llm-google_gemma-4-12b-qat-simple": "Gemma 4 12B · bare prompt",
          "llm-qwen_qwen3.8-27b-simple": "Qwen 3.8 27B · bare prompt"}
fam = lambda n: FAMILY.get(n, "llm" if n.startswith("llm-") else "enc")
pretty = lambda n: PRETTY.get(n, n)
fine_tuned = lambda n: n == "laya-finetuned" or n.endswith("-tweets")
pct = lambda x: f"{x * 100:.1f}%"
ms = lambda x: f"{x / 1000:.1f} s" if x >= 1000 else f"{x:.0f} ms"

ZS = sorted((s for n, s in S.items() if not fine_tuned(n)), key=lambda s: -s["accuracy"])
S1 = [s for s in ZS if fam(s["name"]) in ("enc", "kev", "dec", "tech", "clm", "clef")]
LLM = [s for s in ZS if fam(s["name"]) == "llm"]
best, llm = S1[0], LLM[0]


def svg_chart(rows) -> str:
    """Horizontal accuracy bars, family colours, latency column, dashed line at the best LLM. White card."""
    W, rh, top, left, right_col = 760, 24, 40, 230, 90
    bar_w = W - left - right_col - 16
    lo, hi = 0.3, 0.8
    x = lambda v: left + max(0.0, (v - lo) / (hi - lo)) * bar_w
    H = top + rh * len(rows) + 76                     # room for a two-row legend
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
           f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
           f'<rect width="{W}" height="{H}" rx="10" fill="#ffffff" stroke="#d9dee5"/>',
           f'<text x="{left}" y="24" font-size="13" font-weight="700" fill="#141a21">Zero-shot accuracy on 300 tweets'
           f' (axis from 30%)</text>',
           f'<text x="{W - 16}" y="24" font-size="11" fill="#5a6573" text-anchor="end">median per tweet</text>']
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 6}" y2="{top + rh * len(rows)}" stroke="#eef1f5"/>')
        out.append(f'<text x="{x(t):.1f}" y="{top + rh * len(rows) + 16}" font-size="10" fill="#5a6573" '
                   f'text-anchor="middle">{int(t * 100)}%</text>')
    for i, s in enumerate(rows):
        y = top + i * rh
        f = fam(s["name"])
        op = "0.5" if f == "llm" else "0.92"
        out.append(f'<text x="{left - 8}" y="{y + 15}" font-size="12" fill="{"#5a6573" if f == "llm" else "#141a21"}" '
                   f'text-anchor="end">{pretty(s["name"])}</text>')
        out.append(f'<rect x="{left}" y="{y + 3}" width="{x(s["accuracy"]) - left:.1f}" height="17" rx="3" '
                   f'fill="{COLOR[f]}" fill-opacity="{op}"/>')
        out.append(f'<text x="{x(s["accuracy"]) + 5:.1f}" y="{y + 15}" font-size="11" font-weight="600" '
                   f'fill="#141a21">{pct(s["accuracy"])}</text>')
        out.append(f'<text x="{W - 16}" y="{y + 15}" font-size="11" fill="#5a6573" text-anchor="end">'
                   f'{ms(s["latency_ms_p50"])}</text>')
    xr = x(llm["accuracy"])
    out.append(f'<line x1="{xr:.1f}" x2="{xr:.1f}" y1="{top - 4}" y2="{top + rh * len(rows)}" stroke="#5a6573" '
               f'stroke-dasharray="4 3" stroke-opacity="0.7"/>')
    lx, ly = 24, top + rh * len(rows) + 38
    for f in ("dec", "tech", "kev", "enc", "clm", "clef", "emb", "llm"):
        item_w = 14 + int(6.2 * len(FAMNAME[f])) + 18
        if lx + item_w > W - 16:                      # wrap to a second row
            lx, ly = 24, ly + 18
        out.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{COLOR[f]}"/>'
                   f'<text x="{lx + 14}" y="{ly}" font-size="11" fill="#5a6573">{FAMNAME[f]}</text>')
        lx += item_w
    out.append("</svg>")
    return "\n".join(out)


def table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
                     + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def cm(name):
    m = S[name]["confusion_matrix"]
    return table([f"**{pretty(name)}**", "→ neg", "→ neu", "→ pos"],
                 [[lab, *row] for lab, row in zip(["negative", "neutral", "positive"], m)])


def main():
    OUT_SVG.write_text(svg_chart(ZS))
    d2, emb, laya = S["decider-2b"], S["embed-nomic"], S["laya"]
    md = []
    w = md.append
    w("# Open-source Jev reproductions, zero-shot on real sentiment\n")
    w("> Generated from the same data as the interactive version, [`docs/page/index.html`](page/index.html), "
      "by `docs/page/build.py`.\n")
    w("Jev (TypeSafe AI, 15 Sept 2026) answers typed questions with probabilities instead of generating text. "
      "Within a week, dozens of open reproductions appeared. We take every well-ranked one that runs on a 32 GB "
      "Apple M5, plus newly released ones (Decider 4B v2, GLiNER2.5-Decide, CLM, Cloudflare's Clef-flash), ask each the **same sentiment question** about **300 human-labelled "
      "tweets**, and race them against local LLMs in LM Studio. The main comparison is **zero-shot**; a reference "
      "section documents three models we also trained on tweets.\n")
    w(table(["", ""], [
        [f"**{pct(best['accuracy'])}**", f"best zero-shot System One: {pretty(best['name'])}, {ms(best['latency_ms_p50'])} per tweet"],
        [f"**{pct(llm['accuracy'])}**", f"best local LLM: {pretty(llm['name'])}, {ms(llm['latency_ms_p50'])} per tweet"],
        [f"**{best['ece']:.3f} vs {llm['ece']:.3f}**", f"calibration error, {pretty(best['name'])} vs the LLM (lower = honest probabilities)"],
        [f"**{pct(emb['accuracy'])}**", "nearest label description by embeddings, for contrast"]]) + "\n")

    w("## What a System One model does\n")
    w("You send a **state** (here, a tweet) and **typed questions** whose answer space you declare up front. You get "
      "back one answer per question with a probability for every option, from a single forward pass. Nothing is "
      "generated, so there is nothing to parse.\n")
    w('```python\nSENTIMENT_QUESTION = {\n    "type": "choice",\n    "instructions": "What is the overall sentiment of this message?",\n'
      '    "criteria": {\n        "negative": "unhappy, angry, disappointed or critical",\n'
      '        "neutral":  "factual or mixed, no clear feeling",\n        "positive": "happy, grateful, excited or praising",\n'
      '    },\n}\n# every engine receives exactly this dict, and returns e.g.\n'
      '{"choice": "positive", "probabilities": {"negative": 0.01, "neutral": 0.04, "positive": 0.95}}\n```\n')

    w("## The reproductions\n")
    w("They differ mainly in *how* they turn a language model into a chooser. Six families, at least one of each run here:\n")
    w(table(["Family", "How it answers", "Trains weights?", "Run here"], [
        ["Encoder + head", "encoder reads question + options + text; one marker per option is scored", "whole model", "Laya, Laya multilingual, GLiNER2.5-Decide (340M, 1B)"],
        ["LoRA + pointer", "causal LLM + LoRA; a decide token points at an option", "adapter + head", "Kev 0.8B / 4B / 9B"],
        ["Full fine-tune", "causal LLM trained to answer in an option letter", "whole model", "Decider 2B, Decider 4B v2"],
        ["Inference technique", "**stock** LLM; lettered options, answer read from letter logits", "nothing", "SemIf, openvons"],
        ["Contrastive bi-encoder", "frozen LLM embeds text and each option **separately**; heads align them; softmax of cosine", "projection heads", "CLM 8B"],
        ["Backbone + joint head", "post-trained LLM; a small transformer head reads its final hidden states and scores all options of all questions **jointly**", "whole model + head", "Clef-flash (Cloudflare)"]]) + "\n")
    w("Chosen from the [Jev Decision Index](https://huggingface.co/spaces/multimodalart/jev-decision-index) (31 "
      "reproductions, 37 benchmarks, run on a 96 GB NVIDIA card): the best-ranked ones that fit this laptop.\n")
    w(table(["Index #", "Reproduction", "Base model", "On a 32 GB Mac"], [
        ["1–4", "Jevfire, diffusiongemma open-jevs, Decider 35B-A3B", "26–36B", "✗ CUDA / vLLM, or Blackwell-only NVFP4"],
        ["5", "Solomon v1.1", "Qwen3.8-27B", "✗ its MLX build needs ~60 GB"],
        ["6–7", "**Kev 9B, Kev 4B**", "Qwen3.5-9B / 4B", "✓ MLX"],
        ["9", "open-jev (pngwn)", "Qwen3.5-4B", "✗ weights without inference code"],
        ["10", "**openvons**", "Qwen3-4B-Instruct", "✓ via mlx_lm.server"],
        ["11", "**SemIf**", "Qwen3.5-4B-Base", "✓ native MLX"],
        ["12", "Decision-1.0-Nox", "Qwen3.5-4B", "✗ AMD ROCm runtime"],
        ["13", "**Decider 2B**", "Qwen3.5-2B", "✓ PyTorch MPS"],
        ["30", "**Laya**", "ModernBERT-large", "✓ PyTorch MPS"],
        ["new", "**Decider 4B v2** (24 Sept)", "Qwen3.5-4B", "✓ PyTorch MPS"],
        ["new", "**GLiNER2.5-Decide** 340M / 1B (the index ran older GLiNER 2.5)", "DeBERTa-v3-large / 1B", "✓ PyTorch MPS"],
        ["new", "**CLM 8B** (24 Sept)", "Qwen3-8B", "✓ vLLM encoder replaced by MLX (parity 0.9998)"],
        ["new", "**Clef-flash** 9B (Cloudflare, 1 Oct; the 27B Clef needs ~55 GB)", "Qwen3.5-9B", "✓ PyTorch MPS, Cloudflare's own inference code"]]) + "\n")

    w("## The dataset\n")
    w("[TweetEval sentiment](https://huggingface.co/datasets/cardiffnlp/tweet_eval) (SemEval-2017 Task 4A): short, "
      "noisy social-media messages labelled negative / neutral / positive by human annotators. A seeded, "
      "class-balanced sample of 100 per class from the **test** split, so always answering \"neutral\" scores 33%.\n")

    w("## Zero-shot results\n")
    w("Same 300 tweets, one per call, after a warm-up call. The LLMs get the same label descriptions in a system "
      "prompt and a JSON-schema `enum`, with thinking off. Nothing below was trained on tweets.\n")
    w("![Zero-shot accuracy per model](page/accuracy.svg)\n")
    w(table(["System", "Family", "Accuracy", "Macro-F1", "p50", "p95", "ECE"],
            [[pretty(s["name"]), FAMNAME[fam(s["name"])], pct(s["accuracy"]), f"{s['macro_f1']:.3f}",
              ms(s["latency_ms_p50"]), ms(s["latency_ms_p95"]), f"{s['ece']:.3f}"] for s in ZS]) + "\n")
    w("±5 points of sampling noise at n = 300. ECE = expected calibration error of the top-class probability; an LLM "
      "returns a bare label, so its confidence is always 1.0 and its ECE equals its error rate. \"Variant\" = SemIf's "
      "technique on a 9B base, not an index configuration; \"bare prompt\" = the LLM without class descriptions.\n")
    w("> **Coverage.** Every model in the table above was run on all 300 tweets. Decider 4B v2, GLiNER2.5-Decide (340M, 1B) and CLM 8B were added later, after the option-order test and the cascade had been run, so those two sections cover only some of the models.\n")

    w("### Where the errors are\n")
    w("Rows = truth (100 each), columns = predicted.\n")
    for n in [best["name"], "semif", "kev-9b", llm["name"]]:
        w(cm(n) + "\n")
    w("Every model confuses polar tweets with neutral ones far more than negative with positive. Laya and Kev hedge "
      "towards \"neutral\"; stock-model letter techniques and LLMs push neutral tweets into a polarity; Decider is the "
      "most balanced.\n")

    if POS:
        w("### Does option order change the answer?\n")
        w("The same 300 tweets with the three options in all 6 orders (1,800 decisions per model):\n")
        eng = [(k, lab) for k, lab in (("laya", "Laya"), ("semif", "SemIf · 4B"), ("decider", "Decider 2B"), ("clef-flash", "Clef-flash")) if k in POS]
        rows = [["Accuracy, correct answer listed 1st / 2nd / 3rd",
                 *[" / ".join(f"{POS[k]['accuracy_by_correct_position'][str(p)] * 100:.0f}" for p in (1, 2, 3)) + "%" for k, _ in eng]],
                ["Picks by position 1st / 2nd / 3rd (order-blind = 33/33/33)",
                 *[" / ".join(f"{POS[k]['pick_share_by_position'][str(p)] * 100:.0f}" for p in (1, 2, 3)) + "%" for k, _ in eng]],
                ["Consistent preference? (χ² p)", *[("**yes**" if POS[k]["pick_chi2_p"] < 0.05 else "no") + f", p = {POS[k]['pick_chi2_p']:.3g}" for k, _ in eng]],
                ["Tweets whose answer changes with order alone", *[pct(POS[k]["tweets_whose_answer_flips"]) for k, _ in eng]]]
        w(table(["", *[lab for _, lab in eng]], rows) + "\n")
        w("Only Laya has a consistent pull (towards the first option). SemIf has no preferred position but flips almost a "
          "fifth of its answers. Decider, trained on shuffled options, is nearly order-blind; the bi-encoder CLM is "
          "order-blind by construction.\n")

    w("### The LLM prompt: with or without class descriptions\n")
    w("Same run with the bare instruction `Classify the following text to be either negative, neutral or positive.` "
      "followed by the tweet, same enum schema:\n")
    rows = []
    for n, lab, p in (("llm-google_gemma-4-26b-a4b-qat", "Gemma 4 26B-A4B", "0.38"), ("llm-google_gemma-4-12b-qat", "Gemma 4 12B", "0.41"),
                      ("llm-qwen_qwen3.8-27b", "Qwen 3.8 27B", "**0.013**")):
        if n in S and n + "-simple" in S:
            a, b = S[n], S[n + "-simple"]
            rows.append([lab, f"{pct(a['accuracy'])} · {ms(a['latency_ms_p50'])}", f"{pct(b['accuracy'])} · {ms(b['latency_ms_p50'])}",
                         f"{(b['accuracy'] - a['accuracy']) * 100:+.1f}", p])
    w(table(["LLM", "With class descriptions", "Bare prompt", "Difference", "Paired McNemar p"], rows) + "\n")
    w("Only Qwen's difference is real: with the descriptions it filed 25 positive tweets as neutral, without them 14.\n")

    w("### Isn't this just embeddings?\n")
    w("A natural simplification: embed each \"label: description\", embed the tweet, pick the closest. CLM is a trained "
      "version of that idea.\n")
    rows = [[lab, together, tr, pct(S[n]["accuracy"]), f"{S[n]['macro_f1']:.3f}"] for n, lab, together, tr in (
        ("clm-raw", "Qwen3-8B last-token embeddings + cosine", "no, separately", "no"),
        ("embed-nomic", "nomic-embed-text + cosine", "no, separately", "no"),
        ("clm-8b", "Qwen3-8B + CLM's trained contrastive heads", "no, separately", "yes, general"),
        (best["name"], f"best cross-encoder ({pretty(best['name'])})", "**yes, one pass**", "yes, general")) if n in S]
    w(table(["Approach", "Tweet and options read together?", "Trained?", "Accuracy", "Macro-F1"], rows) + "\n")
    w("Embeddings encode the tweet without the question: one vector per text whatever you ask, compared by a single "
      "cosine. System One cross-encoders put question, options and tweet in one sequence, so each option is scored "
      "after the model has read this tweet under this question. CLM ranges 0.433–0.550 depending on option wording.\n")

    w("## How each family picks an answer\n")
    w("**Encoder + head (Laya).** Question, options and text go into one sequence; a `[MASK]` before each option is "
      "scored:\n")
    w("```\n[CLS] choice question: What is the overall sentiment of this message? [SEP]\n"
      "[MASK] negative: unhappy, angry, disappointed or critical      -> score for \"negative\"\n"
      "[MASK] neutral: factual or mixed, no clear feeling             -> score for \"neutral\"\n"
      "[MASK] positive: happy, grateful, excited or praising          -> score for \"positive\"\n[SEP]\n"
      "omg just got tickets for the show tonight!!! best day ever [SEP]\n```\n")
    w("```python\nh = encoder(input_ids).last_hidden_state              # ModernBERT-large\n"
      "m = gather(head(h + type_emb(qtype)), marker_pos)     # one vector per option's [MASK]\n"
      "p = softmax(scorer(m) / temperature)                  # scorer: MLP -> 1 number per option\n```\n")
    w("**LoRA + pointer (Kev).** `<state> tweet` then per question `<q> instruction <opt> … </opt> … <decide>`; the "
      "`<decide>` state is dotted with each `</opt>` state: `z_i = (W_k h_opt_i) · (W_q h_decide) / sqrt(d)`.\n")
    w("**Letter logits (SemIf, openvons, Decider).** Relabel options A, B, C, run one forward pass, read the next-token "
      "logits of the letters. SemIf and openvons do it with a *stock* model; Decider is fine-tuned for it. Decider's "
      "\"head\" is the LM's own output layer restricted to the label tokens, a fixed 255 × 2048 slice (A–Z, AA, …) "
      "with unused letters masked, read at the final `(` of `… (A) … (B) … (C) … Answer: (`.\n")
    w("**One score per option, any number of options.** A classic classifier head is `Linear(hidden, N)`. A System One "
      "head outputs one number per option from a shared function, after one forward pass over the whole sequence:\n")
    w(table(["Model", "What represents an option", "Head", "Width"], [
        ["Laya", "`[MASK]` before each option", "MLP → 1 number", "any"],
        ["GLiNER2.5-Decide", "each label + description packed before the text", "scorer on each label's token", "any"],
        ["Kev", "each option's `</opt>` token", "pointer: dot product with `<decide>`", "any (≤ 255 by API)"],
        ["Decider 2B / 4B v2", "label letter in the prompt", "LM output rows for the letters, fine-tuned", "fixed 255, masked"],
        ["SemIf, openvons", "label letter in the prompt", "same letter logits, untrained", "16 / top-5"],
        ["CLM", "option text embedded **alone**", "projection MLPs → cosine", "any"],
        ["Clef-flash", "options listed in the prompt, **sorted alphabetically** first", "joint schema head over all options of all questions", "up to 64 questions"]]) + "\n")
    w("**One adapter per engine, one harness.** Engines that speak TypeSafe's `/v1/systemone` (Kev, CLM) get the question "
      "over HTTP; the others get a small adapter that reads the same `data/test_tweets.jsonl` and writes "
      "`{pred, probs, latency_ms}` per tweet, scored by the same code as everything else.\n")

    if CAS:
        w("## Using the confidence: a cascade\n")
        w("Accept the System One answer when its top probability clears a threshold, otherwise ask the LLM:\n")
        for n, rows in CAS.items():
            w(table([f"{pretty(n)} → {pretty(llm['name'])}", "Accuracy", "Sent to LLM", "Avg per tweet"],
                    [["LLM only" if r["threshold"] > 1 else ("System One only" if r["threshold"] == 0 else f"≥ {r['threshold']:.1f}"),
                      pct(r["accuracy"]), f"{r['llm_share'] * 100:.0f}%", ms(r["avg_ms"])] for r in rows]) + "\n")

    w("## For reference: the trained models\n")
    w("Not part of the main comparison (with labelled data you could train a classifier on embeddings instead), but it "
      "shows each architecture's ceiling. Same 3,000 training tweets, one epoch, temperature refitted on 300 validation "
      "tweets; test tweets unseen.\n")
    train = {"laya-finetuned": ("laya", "Laya", "full model", "421M", "~10 min", "1.6 GB"),
             "kev-0.8b-tweets": ("kev-0.8b", "Kev 0.8B", "LoRA + pointer head", "11.3M", "~40 min", "62 MB"),
             "kev-4b-tweets": ("kev-4b", "Kev 4B", "LoRA + pointer head", "33.8M", "~90 min", "148 MB")}
    w(table(["Model", "What was trained", "Trainable params", "Training on M5", "Saved", "Zero-shot → trained", "Macro-F1", "p50 / p95", "ECE"],
            [[m, what, params, t, size, f"{pct(S[b]['accuracy'])} → **{pct(S[n]['accuracy'])}**", f"{S[n]['macro_f1']:.3f}",
              f"{ms(S[n]['latency_ms_p50'])} / {ms(S[n]['latency_ms_p95'])}", f"{S[n]['ece']:.3f}"]
             for n, (b, m, what, params, t, size) in train.items() if n in S]) + "\n")

    w("## Takeaways\n")
    k9, sf, sf9, ov, g, g1, clm = (S.get(n) for n in ("kev-9b", "semif", "semif-9b", "openvons", "gliner-decide", "gliner-decide-1b", "clm-8b"))
    bullets = [
        f"**Zero-shot, the Decider models match the best local LLM.** {pretty(best['name'])} {pct(best['accuracy'])} and Decider 2B "
        f"{pct(d2['accuracy'])} vs {pretty(llm['name'])} {pct(llm['accuracy'])}: a statistical tie (paired p ≈ 0.8), at "
        f"{llm['latency_ms_p50'] / best['latency_ms_p50']:.1f}× and {llm['latency_ms_p50'] / d2['latency_ms_p50']:.1f}× lower latency, "
        f"with honest probabilities. On this task the 2B is the better deal.",
        (f"**One task is not enough to rank these models.** Cloudflare's Clef-flash is the best model in our Finnish and Snake "
         f"tests, but here scores {pct(S['clef-flash']['accuracy'])}: it calls about two thirds of the tweets neutral, whatever the "
         f"question ID or label wording (0.60–0.62). Its option order never matters: its code sorts the options first."),
        f"**Letter logits are the strongest readout here.** Even a *stock* base model read that way gets {pct(sf['accuracy'])} "
        f"(SemIf 4B) and {pct(sf9['accuracy'])} (9B); pointer and marker heads trail (Kev 9B {pct(k9['accuracy'])}, Laya {pct(laya['accuracy'])}).",
        f"**The base model matters as much as the technique.** The same idea on an instruct model (openvons) reaches "
        f"{pct(ov['accuracy'])} but almost never says \"neutral\" (macro-F1 {ov['macro_f1']:.3f}) and is over-confident (ECE {ov['ece']:.3f}).",
        f"**Bigger isn't automatically better within a family.** GLiNER2.5-Decide-1B ({pct(g1['accuracy'])}) doesn't beat the 340M "
        f"({pct(g['accuracy'])}); Decider 4B v2 only ties the 2B.",
        f"**It isn't just embeddings.** Nearest description by cosine: {pct(emb['accuracy'])}; CLM's trained contrastive heads: "
        f"{pct(clm['accuracy'])}. Reading question, options and text together is where the accuracy comes from.",
        "**Option order matters for some models.** Laya favours whatever is listed first; SemIf flips ~19% of answers; "
        "Decider flips 6%.",
        "**Label descriptions are a model-specific lever.** No effect on the Gemma models, +4.7 points for Qwen 3.8 27B without them.",
        "**One schema everywhere.** The same question dict drove every engine: in-process, over HTTP, or through a 30-line adapter."]
    w("\n".join(f"- {b}" for b in bullets) + "\n")

    w("## Run it yourself\n")
    w("See the [README](../README.md) for setup, step-by-step commands and the key-code docs "
      "([1](1-landscape.md), [2](2-typed-questions.md), [3](3-benchmark-method.md), [4](4-zero-shot-reproductions.md)).\n")
    w("---\n*Measured 23–26 Sept 2026 on an Apple M5 with 32 GB RAM. Laya, Decider and GLiNER on PyTorch MPS; Kev and "
      "SemIf on MLX; openvons on mlx_lm.server; CLM with an MLX encoder; LLMs in LM Studio. Index ranks from Decision "
      "Index edition 0.1 (22 Sept 2026). 300 tweets means roughly ±5 points of noise; read small gaps as ties.*\n")
    OUT_MD.write_text("\n".join(md))
    print("wrote", OUT_MD, "and", OUT_SVG)


if __name__ == "__main__":
    main()
