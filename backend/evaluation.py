"""Generated synthetic controls independent of the product's fixed demo CSVs."""

import csv
import hashlib
import io
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from . import audit
from .canonical import digest
from .data import Snapshot, validate_data
from .engine import ENGINE_VERSION, build_decisions, simulate
from .models import DatasetManifest, StrategySpec


def generated_snapshot(seed, defect=None):
    rng = random.Random(seed)
    rows, day, closing = [], date(2026, 2, 2), 100
    while len(rows) < 24:
        if day.weekday() < 5:
            opening = closing
            closing += rng.choice([-3, -1, 1, 2, 4])
            rows.append(
                [day.isoformat(), "SYNTH", opening, max(opening, closing) + 2, min(opening, closing) - 2, closing, 1000]
            )
        day += timedelta(days=1)
    if defect == "missing_open":
        rows[9][2] = ""
    elif defect == "duplicate_session":
        rows[9][0] = rows[8][0]
    elif defect == "invalid_ohlc":
        rows[9][3] = 1
    elif defect == "negative_volume":
        rows[9][6] = -1
    elif defect == "nonfinite_close":
        rows[9][5] = "NaN"
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
    writer.writerows(rows)
    content = stream.getvalue().encode()
    manifest = DatasetManifest(
        dataset_id=f"control_{seed}",
        byte_hash=hashlib.sha256(content).hexdigest(),
        row_count=len(rows),
        start_session=date.fromisoformat(rows[0][0]),
        end_session=date.fromisoformat(rows[-1][0]),
        source="Independent seeded synthetic audit controls v1; not a real exchange calendar",
    )
    return Snapshot(manifest, content)


def evaluate_audits():
    cases, input_hashes = [], []

    def record(name, finding, expected):
        cases.append(
            {
                "case_id": name,
                "check_id": finding.check_id,
                "expected": expected,
                "actual": finding.status,
                "passed": finding.status == expected,
                "evidence_count": len(finding.evidence),
                "first_evidence": finding.evidence[0] if finding.evidence else None,
            }
        )

    for seed in (104729, 130363):
        snapshot = generated_snapshot(seed)
        input_hashes.append(snapshot.manifest.byte_hash)
        spec = StrategySpec(
            dataset_id=snapshot.manifest.dataset_id,
            dataset_hash=snapshot.manifest.byte_hash,
            symbol="SYNTH",
            sample_start=snapshot.manifest.start_session,
            sample_end=snapshot.manifest.end_session,
            threshold_pct="-100",
        )
        bars, issues = validate_data(snapshot, spec)
        record(f"valid_data_seed_{seed}", audit.integrity(issues), "PASS")
        decisions, skips = build_decisions(bars, spec)
        record(f"lawful_timing_seed_{seed}", audit.timing(decisions), "PASS")
        invalid, _ = build_decisions(bars, spec, diagnostic_future=True)
        record(f"future_close_seed_{seed}", audit.timing(invalid), "FAIL")
        first = decisions[0]
        for name, timestamp in (
            ("after_decision_before_fill", first.decision_at + timedelta(seconds=1)),
            ("equal_decision_boundary", first.decision_at),
        ):
            dependencies = (
                first.dependencies[0].model_copy(update={"available_at": timestamp}),
                *first.dependencies[1:],
            )
            changed = first.model_copy(update={"dependencies": dependencies})
            record(f"{name}_seed_{seed}", audit.timing((changed,)), "FAIL")
        record(f"missing_lineage_seed_{seed}", audit.timing((first.model_copy(update={"dependencies": ()}),)), "FAIL")
        paid = simulate(bars, spec, decisions, skips)
        record(f"explicit_costs_seed_{seed}", audit.costs(spec, paid), "PASS")
        free_spec = spec.model_copy(update={"fee_bps_each_side": Decimal(0), "slippage_bps_each_side": Decimal(0)})
        free = simulate(bars, free_spec, decisions, skips)
        record(f"zero_costs_seed_{seed}", audit.costs(free_spec, free), "WARN")
        for defect in ("missing_open", "duplicate_session", "invalid_ohlc", "negative_volume", "nonfinite_close"):
            malformed = generated_snapshot(seed, defect)
            input_hashes.append(malformed.manifest.byte_hash)
            malformed_spec = spec.model_copy(update={"dataset_hash": malformed.manifest.byte_hash})
            _, errors = validate_data(malformed, malformed_spec)
            record(f"{defect}_seed_{seed}", audit.integrity(errors), "FAIL")

    detection = {}
    for check in ("A01_LOOKAHEAD", "A02_MISSING_COSTS", "A03_DATA_INTEGRITY"):
        counts = {"true_positive": 0, "false_positive": 0, "false_negative": 0, "true_negative": 0}
        for case in (c for c in cases if c["check_id"] == check):
            positive, observed = case["expected"] in {"FAIL", "WARN"}, case["actual"] in {"FAIL", "WARN"}
            key = ("true_" if positive == observed else "false_") + ("positive" if observed else "negative")
            counts[key] += 1
        detection[check] = counts
    root = Path(__file__).resolve().parent
    return {
        "schema_version": "1",
        "scope": "Generated synthetic controls for A01 timing, A02 costs and A03 data integrity.",
        "limitations": "Not an external blind benchmark or a market backtest. Constructed controls do not establish "
        "profitability, arbitrary-strategy coverage or real-world detection rates. A04-A06 remain Unverified.",
        "generation": {"version": "seeded_controls_v1", "seeds": [104729, 130363], "dataset_hashes": input_hashes},
        "versions": {
            "engine": ENGINE_VERSION,
            "rules": "1",
            "source_hash": digest({p.name: p.read_text() for p in sorted(root.glob("*.py"))}),
        },
        "summary": {"total": len(cases), "passed": sum(c["passed"] for c in cases)},
        "detection": detection,
        "cases": cases,
    }
