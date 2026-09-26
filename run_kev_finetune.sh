#!/usr/bin/env bash
# Step 6b - Fine-tune a released Kev model on the tweets, calibrate it, benchmark it.
#
#   ./run_kev_finetune.sh kev-0.8b     # or kev-4b
#
# 1. kev.train --init_from    LoRA + pointer head warm-started from the released checkpoint
# 2. score data/kev/val.jsonl with raw logits (KEV_TEMPERATURE=1.0) through a local server
# 3. scripts/calibrate_checkpoint.py fits one temperature on those rows, writes it into head.pt
# 4. run_kev.sh benchmarks the calibrated checkpoint on the same 300 test tweets as everything else
set -euo pipefail
MODEL=${1:-kev-0.8b}
case $MODEL in
  kev-0.8b) BASE=Qwen/Qwen3.5-0.8B-Base ;;
  kev-4b)   BASE=Qwen/Qwen3.5-4B-Base ;;
  kev-9b)   BASE=Qwen/Qwen3.5-9B-Base ;;
  *) echo "unknown model $MODEL"; exit 1 ;;
esac
ROOT=$(pwd); OUT="$ROOT/models/$MODEL-tweets"; EVAL="$ROOT/results/kev-finetune/$MODEL"; PORT=${PORT:-8010}
mkdir -p "$EVAL" results/logs
[ -f data/kev/train.jsonl ] || uv run python 06_export_kev_data.py

echo "== 1. train $MODEL on data/kev/train.jsonl -> $OUT"
[ -d "$OUT" ] && { echo "$OUT exists; delete it to retrain"; exit 1; }
# Kev's own recipe for --init_from fine-tunes: lr 2e-5, batch 1 x accum 8. One epoch, like the Laya fine-tune.
# bf16 frozen weights + gradient checkpointing keep the 4B model inside 32 GB on a Mac.
(cd third_party/kev && PYTHONWARNINGS=ignore uv run python -m kev.train \
    --data "$ROOT/data/kev/train.jsonl" --base "$BASE" --init_from "jaredpalmer/$MODEL" \
    --epochs 1 --lr 2e-5 --batch 1 --accum 8 --device mps --weights_dtype bf16 --checkpointing 1 \
    --out "$OUT") 2>&1 | grep --line-buffered -vE "Fetching|Loading weights|HF_TOKEN" | tee "results/logs/$MODEL-tweets-train.log"

echo "== 2. score validation tweets with raw logits"
(cd third_party/kev && KEV_TEMPERATURE=1.0 exec uv run --extra serve python -m kev.serve --run "$OUT" --port "$PORT") \
  > "results/logs/$MODEL-tweets-calib-server.log" 2>&1 &
SERVER=$!; trap 'kill $SERVER 2>/dev/null || true' EXIT
until curl -sf "localhost:$PORT/v1/models" > /dev/null; do kill -0 $SERVER || exit 1; sleep 2; done
(cd third_party/kev && PYTHONWARNINGS=ignore uv run python -m kev.benchmark --remote "http://127.0.0.1:$PORT" \
    --data "$ROOT/data/kev/val.jsonl" --out "$EVAL/val") 2>&1 | tail -5
kill $SERVER; wait $SERVER 2>/dev/null || true; trap - EXIT

echo "== 3. fit temperature"
(cd third_party/kev && uv run python scripts/calibrate_checkpoint.py --run "$OUT" --rows "$EVAL/val/rows.json") \
  2>&1 | tee "results/logs/$MODEL-tweets-calibrate.log" | tail -8

echo "== 4. benchmark on the test tweets"
PORT=$PORT ./run_kev.sh "models/$MODEL-tweets"
