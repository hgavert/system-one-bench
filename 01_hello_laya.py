"""Step 1 - Hello world: ask Laya one typed question about a few chat messages.

Run:  uv run python 01_hello_laya.py
"""
import laya

# Load the English checkpoint (421M ModernBERT-large encoder + decision head).
# First run downloads ~1.7 GB from Hugging Face; afterwards it is cached.
agent = laya.load("convaiinnovations/laya")
print(f"Laya loaded on device: {agent.device}\n")

# A Jev-style "typed question": we declare the answer space up front.
# The model can only ever return one of these three labels - there is no text to parse.
questions = {
    "sentiment": {
        "type": "choice",
        "instructions": "What is the overall sentiment of this message?",
        "criteria": {
            "negative": "unhappy, angry, disappointed or critical",
            "neutral": "factual or mixed, no clear feeling",
            "positive": "happy, grateful, excited or praising",
        },
    },
}

messages = [
    "omg just got tickets for the show tonight!!! best day ever",
    "the bus to campus leaves at 7:40 tomorrow",
    "my flight got cancelled AGAIN, three hours on hold with support. never flying with them again",
]

for msg in messages:
    result = agent.predict(msg, questions)
    answer = result["answers"]["sentiment"]
    probs = ", ".join(f"{k}={v:.2f}" for k, v in answer["probabilities"].items())
    print(f"{answer['choice']:>8}  ({probs})  <- {msg}")
