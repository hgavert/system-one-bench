#!/usr/bin/env bash
# Fetch Qwen/Qwen3-4B-Instruct-2507 from the ModelScope mirror (used when huggingface.co is slow from this network).
# Big shards are split into 8 byte ranges downloaded in parallel, then joined.
set -euo pipefail
OUT=models/Qwen3-4B-Instruct-2507; BASE="https://www.modelscope.cn/models/Qwen/Qwen3-4B-Instruct-2507/resolve/master"
mkdir -p "$OUT"
for f in config.json generation_config.json merges.txt model.safetensors.index.json tokenizer.json tokenizer_config.json vocab.json model-00003-of-00003.safetensors; do
  curl -sfL --retry 5 -o "$OUT/$f" "$BASE/$f"
done
fetch_split() {   # file size
  local f=$1 size=$2 n=8 part=$(( ($2 + 7) / 8 ))
  for i in $(seq 0 $((n-1))); do
    local s=$((i*part)) e=$(( (i+1)*part - 1 )); [ $e -ge $size ] && e=$((size-1))
    curl -sfL --retry 10 -C - -r $s-$e -o "$OUT/$f.part$i" "$BASE/$f" &
  done
  wait
  cat $(for i in $(seq 0 $((n-1))); do echo "$OUT/$f.part$i"; done) > "$OUT/$f" && rm "$OUT/$f".part*
  [ "$(stat -f%z "$OUT/$f")" = "$size" ] && echo "ok $f" || { echo "size mismatch $f"; exit 1; }
}
fetch_split model-00001-of-00003.safetensors 3957900840 &
fetch_split model-00002-of-00003.safetensors 3987450520 &
wait
echo done
