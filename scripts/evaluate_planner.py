"""Explicitly opt in to at most ten paid provider calls on public labelled prompts."""

import argparse
import json
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.data import DatasetCatalog
from backend.errors import ResearchError
from backend.planner import ClaudePlanner
from backend.service import ResearchService
from backend.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="Authorize up to 10 billable model calls; never run automatically in CI"
    )
    parser.add_argument("--output-dir", type=Path, default=Path(".quantforge-planner-evaluation"))
    args = parser.parse_args()
    if not args.live:
        parser.error("Use --live only after configuring a provider and accepting the cost of up to ten calls")
    provider = ClaudePlanner.from_environment()
    if provider.settings is None:
        parser.error("Configure QUANTFORGE_ENABLE_PLANNER, ANTHROPIC_API_KEY and QUANTFORGE_PLANNER_MODEL first")
    controls = json.loads((ROOT / "fixtures/planner_cases.json").read_text("utf-8"))
    provider.settings = replace(provider.settings, calls_per_workspace_hour=10)
    results = []
    with TemporaryDirectory(prefix="quantforge-planner-evaluation-") as temporary:
        store = Store(Path(temporary) / "research.sqlite3")
        try:
            service = ResearchService(store, DatasetCatalog(ROOT / "fixtures"))
            for control in controls[:10]:
                try:
                    answer, provenance = provider.draft(store, "evaluation", control["hypothesis"])
                    passed = answer.status == control["expected_status"]
                    if answer.status == "PLAN":
                        spec = service.template(overrides=answer.parameters.model_dump(exclude_none=True))
                        for key, expected in control["parameters"].items():
                            proposed = getattr(answer.parameters, key)
                            passed = (
                                passed
                                and proposed is not None
                                and Decimal(str(getattr(spec, key))) == Decimal(str(expected))
                            )
                    results.append(
                        {
                            "case_id": control["case_id"],
                            "expected": control["expected_status"],
                            "actual": answer.status,
                            "passed": bool(passed),
                            "provenance": provenance,
                        }
                    )
                except ValidationError:
                    results.append(
                        {
                            "case_id": control["case_id"],
                            "expected": control["expected_status"],
                            "actual": "INVALID_SPEC",
                            "passed": False,
                        }
                    )
                except ResearchError as exc:
                    results.append(
                        {
                            "case_id": control["case_id"],
                            "expected": control["expected_status"],
                            "actual": exc.code,
                            "passed": False,
                        }
                    )
                    if exc.code == "PLANNER_UNAVAILABLE":
                        break
        finally:
            store.close()
    result = {
        "live_provider": True,
        "model": provider.settings.model,
        "scope": "Ten public labelled hypotheses, not general semantic accuracy",
        "total": len(controls),
        "attempted": len(results),
        "passed": sum(r["passed"] for r in results),
        "cases": results,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "planner-evaluation.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
    print(json.dumps({key: result[key] for key in ("total", "attempted", "passed")}))
    if result["passed"] != result["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
