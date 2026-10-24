"""Independent evidence evaluation; verdicts never depend on model prose."""

from .models import Finding


def integrity(issues):
    return Finding(
        check_id="A03_DATA_INTEGRITY",
        status="FAIL" if issues else "PASS",
        severity="HIGH" if issues else "INFO",
        execution_effect="BLOCK" if issues else "NONE",
        explanation="Dataset validation failed"
        if issues
        else "Pinned synthetic dataset passed supported integrity checks",
        evidence=tuple(issue.model_dump(mode="json") for issue in issues),
    )


def timing(decisions):
    if not decisions:
        return Finding(
            check_id="A01_LOOKAHEAD",
            status="NOT_APPLICABLE",
            explanation="No feature-bearing decisions in this sample; inspect warmup and final-session skips",
        )
    violations = []
    for d in decisions:
        if not (d.decision_at <= d.submitted_at < d.entry_at < d.exit_at):
            violations.append({"decision_id": d.decision_id, "reason": "Invalid decision/order/fill ordering"})
        if not d.dependencies:
            violations.append({"decision_id": d.decision_id, "reason": "Missing feature lineage"})
        for dep in d.dependencies:
            if dep.available_at >= d.decision_at or dep.available_at >= d.entry_at or dep.session > d.session:
                violations.append(
                    {
                        "decision_id": d.decision_id,
                        "field": dep.field,
                        "row_number": dep.row_number,
                        "source_session": dep.session.isoformat(),
                        "available_at": dep.available_at.isoformat(),
                        "decision_at": d.decision_at.isoformat(),
                        "entry_at": d.entry_at.isoformat(),
                    }
                )
    return Finding(
        check_id="A01_LOOKAHEAD",
        status="FAIL" if violations else "PASS",
        severity="HIGH" if violations else "INFO",
        execution_effect="BLOCK" if violations else "NONE",
        explanation="Information or event ordering violates causality"
        if violations
        else "All recorded dependencies precede decisions and fills",
        evidence=tuple(violations),
        requires_rerun=bool(violations),
    )


def costs(spec, result):
    if result is None:
        return Finding(
            check_id="A02_MISSING_COSTS",
            status="UNVERIFIED",
            explanation="Simulation did not produce trades to evaluate",
        )
    if not result.trades:
        return Finding(
            check_id="A02_MISSING_COSTS", status="NOT_APPLICABLE", explanation="No trades; no realized cost impact"
        )
    zero = spec.fee_bps_each_side + spec.slippage_bps_each_side == 0
    return Finding(
        check_id="A02_MISSING_COSTS",
        status="WARN" if zero else "PASS",
        severity="MEDIUM" if zero else "INFO",
        requires_rerun=zero,
        explanation="Trades were simulated with zero costs; run cost sensitivity"
        if zero
        else "Explicit nonzero modeled costs applied; realism remains unverified",
        evidence=(
            {
                "trade_count": len(result.trades),
                "fee_bps_each_side": str(spec.fee_bps_each_side),
                "slippage_bps_each_side": str(spec.slippage_bps_each_side),
            },
        ),
    )


def uncovered():
    return tuple(
        Finding(check_id=key, status="UNVERIFIED", explanation=reason)
        for key, reason in (
            ("A04_SPLIT_LEAKAGE", "No training/test selection provenance in MVP"),
            ("A05_OVERFITTING_RISK", "No complete search history or independent holdout evidence"),
            ("A06_SURVIVORSHIP", "No historical point-in-time universe or delisting coverage"),
        )
    )
