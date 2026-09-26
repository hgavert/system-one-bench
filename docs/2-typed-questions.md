# 2 · Key code: how a typed question gets answered (worked example: Laya)

Every reproduction takes the same question dict. This doc follows one request end to end through the
simplest of them, Laya (an encoder with a small head), because its internals fit on one page.
[Doc 4](4-zero-shot-reproductions.md) shows how the other families (letter logits, pointer heads) differ.

Files: [`01_hello_laya.py`](../01_hello_laya.py), [`laya_classifier.py`](../laya_classifier.py).
Internals quoted from the installed `laya==0.3.7` package (`laya/agent.py`, `laya/common.py`).

## 2.1 The question is the schema

```python
SENTIMENT_QUESTION = {
    "type": "choice",
    "instructions": "What is the overall sentiment of this message?",
    "criteria": {
        "negative": "unhappy, angry, disappointed or critical",
        "neutral": "factual or mixed, no clear feeling",
        "positive": "happy, grateful, excited or praising",
    },
}
```

Everything the model needs is declared here: the *type* (`choice`), the *instruction*, and the
closed set of *labels* with a short description each. The descriptions are read by the model
— they are the "prompt engineering" surface. The keys are what you get back.

## 2.2 One call

```python
agent = laya.load("convaiinnovations/laya")   # downloads ~840 MB once; picks cuda > mps > cpu
result = agent.predict(tweet, {"sentiment": SENTIMENT_QUESTION})
ans = result["answers"]["sentiment"]
ans["choice"]          # "positive"
ans["probabilities"]   # {"negative": 0.01, "neutral": 0.04, "positive": 0.95}
ans["confidence"]      # 1 - normalised entropy of the distribution
result["usage"]        # {"input_tokens": 57, "output_tokens": 0}   <- nothing is generated
```

`output_tokens: 0` is the whole idea: the answer comes out of one encoder pass.

## 2.3 What the model actually sees

`laya.common.build_sequence` lays each (question, state) pair out as a single token sequence:

```
[CLS] choice question: What is the overall sentiment… [SEP]
      [MASK] negative: unhappy, angry…  [MASK] neutral: factual…  [MASK] positive: happy… [SEP]
      <the tweet> [SEP]
```

Each option is prefixed with a `[MASK]` token; their positions are remembered as **markers**.
The instruction+options block is capped at 192 tokens (`head_max_len`), the whole sequence at 512.

## 2.4 The decision head

`laya.common.DecisionModel.forward`, simplified:

```python
h = encoder(input_ids, attention_mask).last_hidden_state   # ModernBERT-large, bidirectional
h = h + type_emb(qtype)                                     # tell it: choice / score / noul
h = head(h)                                                 # 2 extra transformer layers
m = gather(h, marker_pos)                                   # one vector per [MASK] = per option
logits = scorer(m)                                          # MLP -> one scalar per option
```

So the model *points* at an option: every option gets a score from the hidden state at its own
`[MASK]` token, which has attended to the instruction, the other options and the tweet.
Nothing is decoded, and the number of options is just the number of markers — which is why the
same weights handle 2-way, 3-way or 20-way questions.

## 2.5 Any number of options, one pass

A classic classifier head is `Linear(hidden, N)`: one output row per class, so the labels live in the
weights and new labels mean retraining. A System One head is different: **its output dimension is 1**.
It is a shared function that turns *one option's vector* into *one score*, applied to every option:

```python
h      = encoder(tokens)          # [seq_len, 1024]  ONE forward pass, all options inside the sequence
m      = h[marker_positions]      # [K, 1024]        one vector per option ([MASK] marker)
logits = scorer(m).squeeze(-1)    # [K]              scorer = LayerNorm -> Linear(d,d) -> GELU -> Linear(d, 1)
```

* **5 options** -> 5 markers -> 5 scores. **15 options** -> 15 scores. Same weights; nothing to change.
* **One call, not one per option.** All options sit in the same sequence; the head is only evaluated
  K times on the pass's output (K tiny matrix products).
* **Masking** appears only when questions with different option counts share a padded batch: the
  padded slots get -10,000 before the softmax (`logits.masked_fill(~marker_mask, -1e4)`).
* **Limits are practical:** Laya's options must fit in 192 tokens; Kev/Decider/Jev accept up to 255.

The head is trained once, on many decision tasks with varied questions and option sets, and often
with shuffled options and inserted "none of the above"/distractor options, so the only way to score
well is to read each option against the state. At request time the options are just input text.

How the other families produce "one score per option":

| Family | What represents an option | Head | Width |
|---|---|---|---|
| Laya (encoder) | hidden state of a `[MASK]` before each option | 2 transformer layers + MLP -> 1 number | any number of options |
| GLiNER2.5-Decide (encoder) | each label and its description packed before the text (`[DESC] negative: …`) | scorer on each label's token -> 1 number | any number of options |
| Kev (LoRA + pointer) | hidden state at each option's `</opt>` token | pointer: `(W_k h_opt) . (W_q h_decide)`, 256-d projections | any, up to 255 by API |
| Decider 2B / 4B v2 (full fine-tune) | options labelled A, B, C in the prompt | **no new head**: the LM's own output rows for the label tokens ([doc 4](4-zero-shot-reproductions.md#44-decider-2b-a-full-fine-tune-that-answers-in-a-letter)) | fixed 255, unused letters masked |
| SemIf / openvons (stock LM) | options labelled A, B, C in the prompt | same letter logits, untrained for the task | 16 letters / top-5 logprobs |
| CLM (bi-encoder) | embedding of the option text **alone** | two projection MLPs -> cosine | any number |

## 2.6 Why option order can matter

"One score per option" does not mean options are scored in isolation. In every cross-encoder the
option's vector is computed while reading the whole sequence, so order leaks in through:

1. **position encodings**: the same option text at position 1 and at position 3 is a different input;
2. **causal attention** (Kev, Decider, SemIf): later options see earlier ones, not the reverse;
3. **letter priors** (letter-logit models): base LMs prefer some label tokens, famously "A";
4. **training shortcuts**, if correct answers were often first or last.

Only the bi-encoder (CLM) is order-blind by construction, at the price of never letting the tweet
and the options interact. Measured on our tweets: [doc 4, position bias](4-zero-shot-reproductions.md#48-position-bias).

## 2.7 Calibration

Back in `Agent.system_one`:

```python
t_scale = self.temperature_by_options.get(temp_bucket(qt, k), self.temperature[qt])
z = logits[r, :k] / t_scale
p = softmax(z)
```

The checkpoint ships temperatures fitted per question type and option count (`choice:3-5` =
1.76 for the base model). Dividing by it doesn't change *which* answer wins — it makes the
probabilities honest, so "0.8" means right about 80% of the time. That's what the **ECE**
(expected calibration error) column in the benchmark measures, and why Laya can be used with a
confidence threshold ("auto-accept above 0.8, send the rest to a human or an LLM").

## 2.8 Batching many messages (`LayaSentiment.classify_batch`)

`agent.predict` batches the *questions* for one state. For a dataset we want the opposite: one
question, many states. We reuse Laya's own helpers so the input is byte-identical:

```python
q = a._to_internal(SENTIMENT_QUESTION)
items = [{"ids": ids, "markers": m, "qtype": QTYPES["choice"]}
         for ids, m in (build_sequence(a.tok, text, q, max_len, head_max_len) for text in texts)]
b = collate_items([items], a.tok.pad_token_id)              # pad to the longest in the batch
logits, _ = a.model(b["input_ids"], b["attention_mask"], b["marker_pos"], b["marker_mask"], b["qtype"])
p = softmax(logits[:, :3] / temperature)                     # same calibration as predict()
```

The benchmark checks that batched and single-call predictions agree (they do, 100%).
Speed-up on Apple MPS is modest (1.2–1.7×) because tweets are short and the per-call overhead is
already small; on a CUDA GPU batching is where Laya's "7 ms per query" figure comes from.
