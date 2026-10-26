"""Write a repeatable audit-control report; exit nonzero on a mismatch."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.evaluation import evaluate_audits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("docs/evaluation"))
    args = parser.parse_args()
    result = evaluate_audits()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "audit-evaluation.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    lines = [
        "# Audit control evaluation",
        "",
        result["scope"],
        "",
        result["limitations"],
        "",
        f"Matched: {result['summary']['passed']} / {result['summary']['total']} expected outcomes.",
        "",
        "| Case | Rule | Expected | Observed | Matched |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += [
        f"| {c['case_id']} | {c['check_id']} | {c['expected']} | {c['actual']} | {c['passed']} |"
        for c in result["cases"]
    ]
    lines += [
        "",
        "Generated with `python scripts/evaluate_audit.py`. Full source/data fingerprints and detection counts are in audit-evaluation.json.",
    ]
    (args.output_dir / "README.md").write_text("\n".join(lines) + "\n", "utf-8")
    print(json.dumps(result["summary"]))
    if result["summary"]["passed"] != result["summary"]["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
