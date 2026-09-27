"""Any Jev `choice` question answered by an OpenAI-compatible LLM (Test 3's reference: Qwen 3.8 27B on Leviathan).

Like llm_classifier.py, the answer is forced with a JSON-schema enum over the option names, and thinking is off.
The prompt is built from the same question dict every System One model gets: instructions, then the options with
their descriptions, in the question's language; the text is the user message.

Endpoint from .env (see .env.example): LEVIATHAN_BASE_URL, LEVIATHAN_MODEL, LEVIATHAN_API_KEY.
"""
import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

ANSWER_WITH = {"en": "Answer with exactly one of these options:", "fi": "Vastaa täsmälleen yhdellä näistä vaihtoehdoista:"}


class LLMChoiceEngine:
    def __init__(self, base_url=None, model=None, api_key=None):
        load_dotenv()
        self.model = model or os.environ["LEVIATHAN_MODEL"]
        self.name = f"LLM {self.model}"
        self.client = OpenAI(base_url=base_url or os.environ["LEVIATHAN_BASE_URL"],
                             api_key=api_key or os.environ.get("LEVIATHAN_API_KEY") or "none", timeout=120)

    def messages(self, request, lang="en"):
        (q,) = request["questions"].values()
        opts = "\n".join(f"- {k}: {v}" if v else f"- {k}" for k, v in q["criteria"].items())
        return [{"role": "system", "content": f"{q['instructions']}\n\n{ANSWER_WITH[lang]}\n{opts}"},
                {"role": "user", "content": request["state"]}]

    def ask(self, request, lang="en"):
        (qid, q), = request["questions"].items()
        names = list(q["criteria"])
        schema = {"type": "object", "properties": {"answer": {"type": "string", "enum": names}},
                  "required": ["answer"], "additionalProperties": False}
        t0 = time.perf_counter()
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, temperature=0, messages=self.messages(request, lang),
                    response_format={"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": schema}},
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}})
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        ms = (time.perf_counter() - t0) * 1000
        try:
            label = json.loads(resp.choices[0].message.content)["answer"]
        except (json.JSONDecodeError, KeyError, TypeError):
            label = names[0]          # counted as a (likely wrong) answer rather than crashing the run
        # a label, not a calibrated distribution: all mass on the answer
        return {qid: {"choice": label, "probabilities": {n: float(n == label) for n in names}}}, ms, 0
