#!/usr/bin/env bash
# Benchmark a Kev model: start its System One server, run 02_benchmark.py against it, stop it.
#
#   ./run_kev.sh kev-4b                        # a released model: kev-0.8b, kev-4b, kev-9b
#   ./run_kev.sh models/kev-4b-tweets          # a local checkpoint (from run_kev_finetune.sh)
#
# Needs the Kev repo in third_party/kev (see README):
#   git clone https://github.com/jaredpalmer/kev third_party/kev && (cd third_party/kev && uv sync --extra serve)
set -euo pipefail
MODEL=${1:-kev-4b}
PORT=${PORT:-8009}
if [ -d "$MODEL" ]; then RUN=$(cd "$MODEL" && pwd); MODEL=$(basename "$MODEL"); else RUN="jaredpalmer/$MODEL"; fi
mkdir -p results/logs

echo "starting Kev server for $RUN on :$PORT (first run downloads the weights) ..."
(cd third_party/kev && exec uv run --extra serve python -m kev.serve --run "$RUN" --port "$PORT") \
  > "results/logs/$MODEL-server.log" 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT

until curl -sf "localhost:$PORT/v1/models" > /dev/null; do
  kill -0 $SERVER 2>/dev/null || { echo "server died:"; tail -20 "results/logs/$MODEL-server.log"; exit 1; }
  sleep 2
done
curl -s "localhost:$PORT/v1/models" | head -c 600; echo

PYTHONWARNINGS=ignore uv run python 02_benchmark.py "$MODEL" --url "http://127.0.0.1:$PORT" 2>&1 \
  | grep -v -E '^\s+[0-9]+/[0-9]+$' | tee "results/logs/$MODEL.log"
