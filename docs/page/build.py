"""Fill the report page with the numbers in results/ -> docs/page/index.html, and write its Markdown twin
(docs/sentiment-report.md + docs/page/accuracy.svg, via build_md.py) for reading on GitHub."""
import json
from pathlib import Path

here = Path(__file__).parent
summary = json.loads(Path("results/summary.json").read_text())
slim = [{k: s[k] for k in ("name", "accuracy", "macro_f1", "latency_ms_p50", "latency_ms_p95",
                           "throughput_msgs_per_s", "ece", "confusion_matrix")} for s in summary]
# zero-shot cascades shown on the page: System One model -> best LLM
SHOW = ["decider-2b", "semif"]
cascades = {n: json.loads(Path(f"results/cascades/{n}.json").read_text())["rows"]
            for n in SHOW if Path(f"results/cascades/{n}.json").exists()}
html = (here / "template.html").read_text()
posbias = json.loads(Path("results/position_bias.json").read_text()) if Path("results/position_bias.json").exists() else {}
html = html.replace("/*DATA*/", "const SUMMARY = %s;\nconst CASCADES = %s;\nconst POSBIAS = %s;" % (
    json.dumps(slim), json.dumps(cascades), json.dumps(posbias)))
(here / "index.html").write_text(html)
print("wrote", here / "index.html", "with cascades", list(cascades))

import build_md  # noqa: E402  (same folder)
build_md.main()
