"""Sentiment classification with a local LLM served by LM Studio (OpenAI-compatible API).

We use structured output (JSON schema with an enum) so the LLM, like Laya, can only
return one of the three labels. That makes the comparison about the *model*, not about
parsing free-form text.
"""
import json
import time

from openai import OpenAI

from data import LABELS
from laya_classifier import Prediction

SYSTEM_PROMPT = (
    "You are a sentiment classifier for social-media messages. "
    "Classify the overall sentiment of the user's message as negative, neutral or positive. "
    "negative = unhappy, angry, disappointed or critical; "
    "neutral = factual or mixed, no clear feeling; "
    "positive = happy, grateful, excited or praising."
)

# The minimal alternative: no system prompt and no definition of the classes, just the instruction
# followed by the text in one user message. The JSON-schema enum still fixes the answer space.
SIMPLE_INSTRUCTION = "Classify the following text to be either negative, neutral or positive."

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "sentiment",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"sentiment": {"type": "string", "enum": LABELS}},
            "required": ["sentiment"],
            "additionalProperties": False,
        },
    },
}


class LLMSentiment:
    def __init__(self, model: str = "google/gemma-4-26b-a4b-qat",
                 base_url: str = "http://localhost:1234/v1", reasoning_effort: str | None = "none",
                 prompt: str = "described"):
        self.model = model
        self.prompt = prompt          # "described" (system prompt with class descriptions) or "simple"
        # "none" switches off thinking on reasoning models (Gemma 4, Qwen 3.x): one label does
        # not need a chain of thought, and thinking costs 10-30x the latency. None = model default.
        self.extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        self.client = OpenAI(base_url=base_url, api_key="lm-studio")  # key is ignored locally

    def messages(self, text: str) -> list[dict]:
        if self.prompt == "simple":
            return [{"role": "user", "content": f"{SIMPLE_INSTRUCTION}\n\n{text}"}]
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]

    def classify(self, text: str) -> Prediction:
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=self.messages(text),
            response_format=RESPONSE_FORMAT,
            **self.extra,
        )
        latency = time.perf_counter() - t0
        try:
            label = json.loads(resp.choices[0].message.content)["sentiment"]
        except (json.JSONDecodeError, KeyError, TypeError):
            label = "neutral"  # counted as a (likely wrong) answer rather than crashing the run
        # An LLM gives us a label but no calibrated distribution: put all mass on the answer.
        return Prediction(label, {l: float(l == label) for l in LABELS}, latency)
