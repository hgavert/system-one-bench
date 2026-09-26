"""A Mac stand-in for CLM's vLLM encoder: OpenAI-style /v1/embeddings with last-token pooling, on MLX.

CLM (github.com/Contrastive-LM/CLM) scores options with projection heads trained on Qwen3-8B
embeddings produced by
    vllm serve Qwen/Qwen3-8B --runner pooling      (last-token pooling, L2-normalised)
vLLM's pooling runner is CUDA-first. This server returns the same vector on Apple Silicon: the final,
normalised hidden state (model.norm output) at the last token of the text, tokenised like vLLM
(the tokenizer's default special tokens, which for Qwen3 means none), then L2-normalised.

Run with an environment that has mlx-lm, fastapi and uvicorn (Kev's venv does):
  third_party/kev/.venv/bin/python adapters/mlx_embed_server.py --model Qwen/Qwen3-8B --port 8090
"""
import argparse
import base64
import threading

import mlx.core as mx
import numpy as np
import uvicorn
from fastapi import FastAPI
from mlx_lm import load
from pydantic import BaseModel

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="Qwen/Qwen3-8B")
ap.add_argument("--served-name", default="qwen3-8b")
ap.add_argument("--port", type=int, default=8090)
args = ap.parse_args()

model, tokenizer = load(args.model)            # bf16 weights as published; no quantisation
lock = threading.Lock()                        # one Metal job at a time
app = FastAPI(title="mlx last-token embeddings")


class EmbeddingRequest(BaseModel):
    model: str | None = None
    input: str | list[str]
    encoding_format: str = "float"
    truncate_prompt_tokens: int | None = None


def embed_one(text: str, truncate: int | None) -> tuple[np.ndarray, int]:
    ids = tokenizer.encode(text)
    if truncate and len(ids) > truncate:
        ids = ids[-truncate:]                  # vLLM's truncate_prompt_tokens keeps the last tokens
    h = model.model(mx.array([ids]))           # [1, L, hidden], already through the final RMSNorm
    v = np.array(h[0, -1].astype(mx.float32))  # last-token pooling
    return v / (np.linalg.norm(v) + 1e-12), len(ids)


@app.post("/v1/embeddings")
def embeddings(req: EmbeddingRequest):
    texts = [req.input] if isinstance(req.input, str) else req.input
    data, total = [], 0
    with lock:
        for i, t in enumerate(texts):
            v, n = embed_one(t, req.truncate_prompt_tokens)
            total += n
            emb = base64.b64encode(v.astype(np.float32).tobytes()).decode() if req.encoding_format == "base64" \
                else v.tolist()
            data.append({"object": "embedding", "index": i, "embedding": emb})
    return {"object": "list", "model": args.served_name, "data": data,
            "usage": {"prompt_tokens": total, "total_tokens": total}}


@app.get("/v1/models")
def models():
    return {"object": "list", "data": [{"id": args.served_name, "object": "model", "backend": "mlx", "pooling": "last"}]}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
