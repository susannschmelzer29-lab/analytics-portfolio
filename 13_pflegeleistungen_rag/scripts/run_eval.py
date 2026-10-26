"""Run the evaluation and write reports/latest.md + reports/latest.json.

    python scripts/run_eval.py                                  # offline (CI)
    python scripts/run_eval.py --embedder st                    # real retrieval
    python scripts/run_eval.py --embedder st --generator claude # full system
    python scripts/run_eval.py --generator stub-bad             # must FAIL

Exit codes: 0 = pass, 1 = blocking failure or quality gate missed,
2 = the run itself could not start (missing key, missing package, bad case file).

The offline mode indexes the sources in memory. With --embedder st it uses
the same in-memory path, so the evaluation never depends on a stale index.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pflege_rag import SOURCE_DIR  # noqa: E402
from pflege_rag.embeddings import make_embedder  # noqa: E402
from pflege_rag.evaluation import run  # noqa: E402
from pflege_rag.generate import make_generator  # noqa: E402
from pflege_rag.pipeline import build_memory_pipeline  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--embedder", default="hashing", choices=["hashing", "st"])
    p.add_argument("--generator", default="extractive", choices=["extractive", "claude", "stub-bad"])
    p.add_argument("--cases", type=Path, default=ROOT / "cases" / "questions.json")
    p.add_argument("--out", type=Path, default=ROOT / "reports")
    args = p.parse_args(argv)

    try:
        pipeline = build_memory_pipeline(SOURCE_DIR, make_embedder(args.embedder), make_generator(args.generator))
        report = run(pipeline, args.cases)
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"evaluation could not run: {exc}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "latest.md").write_text(report.to_markdown(), encoding="utf-8")
    (args.out / "latest.json").write_text(json.dumps(report.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")

    for grader in ("retrieval_hit_at_k", "answer_correct", "in_scope_answered"):
        rate, n = report.rate(grader)
        print(f"{grader:22s} {rate:6.0%}  (n={n})")
    for cid, check in report.blocking:
        print(f"BLOCKING {cid} {check.grader}: {check.detail}")
    for gate in report.failed_gates:
        print(f"GATE MISSED {gate}")
    print("PASS" if report.exit_code == 0 else "FAIL", f"-> {args.out / 'latest.md'}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
