#!/usr/bin/env bash
# Set up the third-party engines this repo benchmarks, each at the commit that was measured,
# each in its own environment (they pin different torch / MLX / transformers versions).
#
#   ./scripts/setup_engines.sh              # main env + every engine
#   ./scripts/setup_engines.sh kev clm      # only these
#
# Engines: main kev semif openvons clm gliner
# Needs git and uv (https://docs.astral.sh/uv/). Models are fetched separately:
#   uv run python scripts/download_models.py
# An existing checkout is left alone; the script only warns if it is on a different commit.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TP="$ROOT/third_party"
mkdir -p "$TP"

clone_at() {   # repo-url dir commit
    local url=$1 dir=$2 commit=$3
    if [ -d "$dir/.git" ]; then
        local have; have=$(git -C "$dir" rev-parse HEAD)
        if [ "$have" != "$commit" ]; then
            echo "   note: $dir is at ${have:0:10}, the benchmarked commit is ${commit:0:10} (left unchanged)"
        fi
    else
        git clone --quiet --filter=blob:none "$url" "$dir"
        git -C "$dir" checkout --quiet "$commit"
    fi
}

setup_main() {
    echo "== main environment (laya, datasets, openai, scikit-learn, httpx; also runs Decider)"
    (cd "$ROOT" && uv sync)
}

setup_kev() {
    echo "== Kev (jaredpalmer/kev): server + trainer, MLX backend on Apple Silicon"
    clone_at https://github.com/jaredpalmer/kev.git "$TP/kev" 557598fced1dada75dfbf36ed144dce309ac6ceb
    (cd "$TP/kev" && uv sync --extra serve)          # Python 3.13 via the repo's .python-version
}

setup_semif() {
    echo "== SemIf (TheoLeeCJ/openjev): letter-logit scorer, native MLX backend"
    clone_at https://github.com/TheoLeeCJ/openjev.git "$TP/openjev" 1f2dea3e25379f9dfc98cb83c324f00ab5deda37
    (cd "$TP/openjev" && { [ -d .venv ] || uv venv -q --python 3.12 .venv; } \
        && uv pip install -q --python .venv/bin/python -e '.[mlx]')
}

setup_openvons() {
    echo "== openvons (genai-craft/openvons): only its LLM backend is imported, from the main env"
    clone_at https://github.com/genai-craft/openvons.git "$TP/openvons" c2683c4539a78b530b7c36a1536f91fcd8fbc70c
}

setup_clm() {
    echo "== CLM (Contrastive-LM/CLM): server + heads, installed without its vLLM dependency"
    clone_at https://github.com/Contrastive-LM/CLM.git "$TP/clm" bb42c6c5bf914fd449bed2f6ca65be80602cb1f7
    (cd "$TP/clm" && { [ -d .venv ] || uv venv -q --python 3.12 .venv; } \
        && uv pip install -q --python .venv/bin/python --no-deps -e . \
        && uv pip install -q --python .venv/bin/python numpy requests torch fastapi uvicorn pydantic)
    # its encoder runs from Kev's env instead: adapters/mlx_embed_server.py (needs setup_kev)
}

setup_gliner() {
    echo "== GLiNER2.5-Decide (gliner2 package): own venv, versions as benchmarked"
    mkdir -p "$TP/gliner2-env"
    (cd "$TP/gliner2-env" && { [ -d .venv ] || uv venv -q --python 3.12 .venv; } \
        && uv pip install -q --python .venv/bin/python gliner2==2.0.0 torch==2.14.0 transformers==5.17.0 \
               peft==0.21.0 sentencepiece protobuf)
}

ALL=(main kev semif openvons clm gliner)
TARGETS=("$@")
[ ${#TARGETS[@]} -eq 0 ] && TARGETS=("${ALL[@]}")
for t in "${TARGETS[@]}"; do
    case "$t" in
        main|kev|semif|openvons|clm|gliner) "setup_$t" ;;
        *) echo "unknown engine '$t'; choose from: ${ALL[*]}"; exit 1 ;;
    esac
done
echo "done: ${TARGETS[*]}"
