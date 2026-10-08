"""Download every model this repo benchmarks, at the exact revision that was measured, and verify it.

  uv run python scripts/download_models.py --list                 # what, where, how big
  uv run python scripts/download_models.py                        # everything (~76 GB)
  uv run python scripts/download_models.py --only decider-2b,gliner-decide
  uv run python scripts/download_models.py --verify               # check what is on disk, no downloads
  uv run python scripts/download_models.py --verify --quick       # sizes only, no hashing

Models go where the code expects them: the Hugging Face cache (loaded by repo id + revision) or a
folder under models/ or third_party/ (loaded by path). Downloads use plain HTTPS (Xet off; it stalled
here) unless --xet. If huggingface.co is slow from your network:
  --parallel     large files of models/ folders via scripts/fetch_hf_parallel.sh (32 byte ranges)
  --modelscope   Qwen3-4B-Instruct-2507 from the ModelScope mirror (scripts/fetch_modelscope.sh)
Verification compares every file's SHA-256 with the Hub's LFS metadata at the pinned revision.

Not handled here: the LLMs and nomic-embed-text (managed in LM Studio), and the reference fine-tunes
(produced by 03_finetune_laya.py / run_kev_finetune.sh).
"""
import argparse
import fnmatch
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# key -> repo, revision, destination ("cache" or a folder relative to the repo), file patterns, size, used by
MODELS = {
    "laya": dict(repo="convaiinnovations/laya", rev="5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b", dest="cache",
                 patterns=["rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*",
                           "multilingual/rl_agent_config.json", "multilingual/model.safetensors",
                           "multilingual/tokenizer/*", "multilingual/encoder/*"],
                 gb=1.5, used="Laya + Laya multilingual (laya.load)"),
    "kev-0.8b": dict(repo="jaredpalmer/kev-0.8b", rev="54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8", dest="cache",
                     gb=0.07, used="Kev 0.8B adapter + head", needs=["qwen3.5-0.8b-base"]),
    "kev-4b": dict(repo="jaredpalmer/kev-4b", rev="485ace8703592fcf405488b262449990824cfed1", dest="cache",
                   gb=0.16, used="Kev 4B adapter + head (sentiment runs and fine-tune)", needs=["qwen3.5-4b-base"]),
    "kev-4b-snake": dict(repo="jaredpalmer/kev-4b", rev="139fdd94f1b6a6ad80cc15e08fcb99cac885a101", dest="cache",
                         gb=0.16, used="Kev 4B, newer upstream release used by the Snake runs", needs=["qwen3.5-4b-base"],
                         optional=True),
    "kev-9b": dict(repo="jaredpalmer/kev-9b", rev="2629c06a5aeb0feb3b9783bafed17ed8f39ecf5c", dest="cache",
                   gb=0.2, used="Kev 9B adapter + head", needs=["qwen3.5-9b-base"]),
    "qwen3.5-0.8b-base": dict(repo="Qwen/Qwen3.5-0.8B-Base", rev="dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68",
                              dest="cache", gb=1.8, used="Kev 0.8B base"),
    "qwen3.5-4b-base": dict(repo="Qwen/Qwen3.5-4B-Base", rev="1001bb4d826a52d1f399e183466143f4da7b741b",
                            dest="cache", gb=9.3, used="Kev 4B base; SemIf 4B"),
    "qwen3.5-9b-base": dict(repo="Qwen/Qwen3.5-9B-Base", rev="68c46c4b3498877f3ef123c856ecfde50c39f404",
                            dest="cache", gb=19.3, used="Kev 9B base; SemIf 9B variant"),
    "decider-2b": dict(repo="Mapika/decider-2b", rev="fa996cea58e1c1d8d1ab4d7124154f303b017f95",
                       dest="models/decider-2b", gb=3.8, used="Decider 2B (weights + its decider/ package)"),
    "decider-4b-v2": dict(repo="Mapika/decider-4b", rev="49564ddcfccafb6db563eb757c1d41e6c78dcb56",
                          dest="models/decider-4b-v2", gb=8.4, used="Decider 4B v2 (Hub tag v2)"),
    "gliner-decide": dict(repo="fastino/GLiNER2.5-Decide", rev="7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6",
                          dest="cache", gb=1.95, used="GLiNER2.5-Decide 340M"),
    "gliner-decide-1b": dict(repo="fastino/GLiNER2.5-Decide-1B", rev="52c94d3b698bf6d2619df9d898bdc1523ea3f1ca",
                             dest="cache", gb=4.8, used="GLiNER2.5-Decide-1B"),
    "qwen3-4b-instruct": dict(repo="Qwen/Qwen3-4B-Instruct-2507", rev="cdbee75f17c01a7cc42f958dc650907174af0554",
                              dest="models/Qwen3-4B-Instruct-2507", gb=8.1,
                              patterns=["*.json", "*.safetensors", "merges.txt", "vocab.json"],
                              used="openvons (served by mlx_lm.server)"),
    "qwen3-8b": dict(repo="Qwen/Qwen3-8B", rev="b968826d9c46dd6066d109eabc6255188de91218", dest="cache",
                     gb=16.4, used="CLM encoder (adapters/mlx_embed_server.py)"),
    "clm-head": dict(repo="Contrastive-LM/CLM-v0.1-8B", rev="e939398d4556fcd9400c76fa8c5a513202f42b0a",
                     dest="third_party/clm/checkpoints", patterns=["CLM_v0.1-8B.pt"], gb=0.08,
                     used="CLM projection heads"),
    "clef-flash": dict(repo="Cloudflare/clef-flash", rev="17f0b0ad64efb65d273590632833508766b2aae6", dest="cache",
                       gb=19.1, used="Clef-flash 9B (adapters/clef_server.py, clef env)"),
}


def files_at_revision(api, key):
    """[(path, size, sha256 or None)] for the pinned revision, filtered by the model's patterns."""
    m = MODELS[key]
    out = []
    for f in api.list_repo_tree(m["repo"], revision=m["rev"], recursive=True, expand=True):
        if not hasattr(f, "size") or f.path.startswith(".") or f.path.endswith(".gitattributes"):
            continue
        if m.get("patterns") and not any(fnmatch.fnmatch(f.path, p) for p in m["patterns"]):
            continue
        name = Path(f.path).name.upper()
        if not m.get("patterns") and (f.path.lower().endswith((".md", ".png", ".jpg", ".pdf", ".svg"))
                                      or name.startswith(("LICENSE", "NOTICE"))):
            continue              # docs, images and licence texts are not needed to run
        out.append((f.path, f.size, f.lfs.sha256 if f.lfs else None))
    return out


def local_path(key, relpath):
    m = MODELS[key]
    if m["dest"] == "cache":
        from huggingface_hub import constants
        repo_dir = Path(constants.HF_HUB_CACHE) / f"models--{m['repo'].replace('/', '--')}"
        return repo_dir / "snapshots" / m["rev"] / relpath
    return ROOT / m["dest"] / relpath


def sha256(path, chunk=1 << 24):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def verify(api, key, quick=False):
    problems = []
    for path, size, digest in files_at_revision(api, key):
        p = local_path(key, path)
        if not p.exists():
            problems.append(f"missing {path}")
        elif p.stat().st_size != size:
            problems.append(f"size {path}: {p.stat().st_size} != {size}")
        elif digest and not quick and sha256(p) != digest:
            problems.append(f"sha256 mismatch {path}")
    return problems


def download(api, key, args):
    from huggingface_hub import snapshot_download
    m = MODELS[key]
    local_dir = None if m["dest"] == "cache" else str(ROOT / m["dest"])
    if key == "qwen3-4b-instruct" and args.modelscope:
        subprocess.run([str(ROOT / "scripts/fetch_modelscope.sh")], cwd=ROOT, check=True)
        return
    skip = []
    if args.parallel and local_dir:
        for path, size, _ in files_at_revision(api, key):
            if size > 200_000_000 and not verify_file(key, path, size):
                subprocess.run([str(ROOT / "scripts/fetch_hf_parallel.sh"), m["repo"], m["rev"], path,
                                local_dir, "32"], cwd=ROOT, check=True)
            if size > 200_000_000:
                skip.append(path)
    snapshot_download(m["repo"], revision=m["rev"], local_dir=local_dir,
                      allow_patterns=m.get("patterns"), ignore_patterns=skip or None)


def verify_file(key, path, size):
    p = local_path(key, path)
    return p.exists() and p.stat().st_size == size


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show the models, where they go and their size")
    ap.add_argument("--only", help="comma-separated keys (see --list); dependencies are added")
    ap.add_argument("--all", action="store_true", help="include optional models (kev-4b-snake)")
    ap.add_argument("--verify", action="store_true", help="check files on disk against the Hub; no downloads")
    ap.add_argument("--quick", action="store_true", help="with --verify: compare sizes only, skip hashing")
    ap.add_argument("--xet", action="store_true", help="allow the Xet transfer backend")
    ap.add_argument("--parallel", action="store_true", help="large files of models/ folders via 32 byte ranges")
    ap.add_argument("--modelscope", action="store_true", help="Qwen3-4B-Instruct-2507 from ModelScope")
    args = ap.parse_args()

    if not args.xet:
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    from huggingface_hub import HfApi
    api = HfApi()

    if args.list:
        print(f"{'key':<20} {'size':>7}  {'destination':<34} used for")
        for k, m in MODELS.items():
            dest = "HF cache" if m["dest"] == "cache" else m["dest"]
            print(f"{k:<20} {m['gb']:>5.1f}GB  {dest:<34} {m['used']}{'  (optional)' if m.get('optional') else ''}")
        print(f"{'':<20} {sum(m['gb'] for m in MODELS.values() if not m.get('optional')):>5.1f}GB  total (without optional)")
        return

    keys = [k.strip() for k in args.only.split(",")] if args.only else \
        [k for k, m in MODELS.items() if args.all or not m.get("optional")]
    unknown = [k for k in keys if k not in MODELS]
    if unknown:
        sys.exit(f"unknown model(s) {unknown}; see --list")
    for k in list(keys):                          # pull in bases (Kev needs its Qwen3.5 base)
        for dep in MODELS[k].get("needs", []):
            if dep not in keys:
                keys.append(dep)

    failed = []
    for k in keys:
        m = MODELS[k]
        if not args.verify:
            problems = verify(api, k, quick=True)
            if problems:
                print(f"== {k}: downloading {m['repo']}@{m['rev'][:8]} (~{m['gb']} GB)", flush=True)
                download(api, k, args)
            else:
                print(f"== {k}: already present", flush=True)
        problems = verify(api, k, quick=args.quick)
        status = "OK" if not problems else "PROBLEM: " + "; ".join(problems[:4])
        print(f"   {k:<20} {m['repo']}@{m['rev'][:8]}  {status}", flush=True)
        if problems:
            failed.append(k)
    if failed:
        sys.exit(f"\n{len(failed)} model(s) incomplete or changed: {', '.join(failed)}")
    print(f"\nall {len(keys)} verified")


if __name__ == "__main__":
    main()
