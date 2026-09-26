#!/usr/bin/env bash
# Download one large file from huggingface.co as N parallel byte ranges, for networks where the HF CDN
# limits each connection. Uses the token saved by `hf auth login` if present.
#   scripts/fetch_hf_parallel.sh Mapika/decider-2b fa996cea58e1c1d8d1ab4d7124154f303b017f95 model.safetensors models/decider-2b 32
set -euo pipefail
REPO=$1 REV=$2 FILE=$3 OUT=$4 N=${5:-32}
URL="https://huggingface.co/$REPO/resolve/$REV/$FILE"
AUTH=(); [ -f ~/.cache/huggingface/token ] && AUTH=(-H "Authorization: Bearer $(cat ~/.cache/huggingface/token)")
mkdir -p "$(dirname "$OUT/$FILE")"
SIZE=$(curl -sIL "${AUTH[@]}" "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
PART=$(( (SIZE + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  s=$((i*PART)); e=$(( (i+1)*PART - 1 )); [ $e -ge $SIZE ] && e=$((SIZE-1))
  ( until [ -f "$OUT/$FILE.part$i" ] && [ "$(stat -f%z "$OUT/$FILE.part$i")" = "$((e-s+1))" ]; do
      have=$( [ -f "$OUT/$FILE.part$i" ] && stat -f%z "$OUT/$FILE.part$i" || echo 0 )
      curl -sfL "${AUTH[@]}" -r $((s+have))-$e "$URL" >> "$OUT/$FILE.part$i" || sleep 2
    done ) &
done
wait
cat $(for i in $(seq 0 $((N-1))); do echo "$OUT/$FILE.part$i"; done) > "$OUT/$FILE" && rm "$OUT/$FILE".part*
[ "$(stat -f%z "$OUT/$FILE")" = "$SIZE" ] && echo "ok $OUT/$FILE ($SIZE bytes)"
