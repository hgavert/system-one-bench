"""Check that adapters/mlx_embed_server.py returns the vector CLM's heads were trained on.

Reference: Hugging Face transformers' Qwen3-8B, last token of last_hidden_state (after the final
RMSNorm), L2-normalised, which is what vLLM's pooling runner returns. Two phases, because both models
need ~16 GB:

  uv run python adapters/check_embed_parity.py fetch     # with the MLX server running
  (stop the server)
  uv run python adapters/check_embed_parity.py compare   # loads transformers Qwen3-8B (bf16, MPS)
"""
import base64
import json
import sys

import numpy as np
import requests
import torch
from transformers import AutoModel, AutoTokenizer

TEXTS = [
    "omg just got tickets for the show tonight!!! best day ever\n\nWhat is the overall sentiment of this message?",
    "the bus to campus leaves at 7:40 tomorrow\n\nWhat is the overall sentiment of this message?",
    "unhappy, angry, disappointed or critical",
    "factual or mixed, no clear feeling",
]

SAVED = "results/raw/embed_parity_mlx.npy"
if sys.argv[1:] == ["fetch"]:
    r = requests.post("http://127.0.0.1:8090/v1/embeddings",
                      json={"model": "qwen3-8b", "input": TEXTS, "encoding_format": "base64"}).json()
    np.save(SAVED, np.stack([np.frombuffer(base64.b64decode(d["embedding"]), dtype=np.float32) for d in r["data"]]))
    sys.exit(f"saved {SAVED}")
mlx = np.load(SAVED)

tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
model = AutoModel.from_pretrained("Qwen/Qwen3-8B", dtype=torch.bfloat16).to("mps").eval()
ref = []
with torch.no_grad():
    for t in TEXTS:
        ids = tok(t, return_tensors="pt").input_ids.to("mps")
        v = model(input_ids=ids).last_hidden_state[0, -1].float().cpu().numpy()
        ref.append(v / np.linalg.norm(v))
ref = np.stack(ref)

cos = (mlx * ref).sum(1)
print(json.dumps({"cosine_mlx_vs_transformers": cos.round(5).tolist(),
                  "pairwise_sims_mlx": (mlx @ mlx.T).round(3).tolist(),
                  "pairwise_sims_ref": (ref @ ref.T).round(3).tolist()}, indent=1))
