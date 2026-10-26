"""Deterministic, portable research reports derived only from saved artifacts."""

import html
import json
from decimal import Decimal, localcontext


def text(value):
    return html.escape(str(value)).replace("|", "\\|").replace("\n", " ")


def json_block(value):
    # Escape markup even when a downloaded report is rendered by another tool.
    body = json.dumps(value, indent=2, ensure_ascii=True).replace("<", "\\u003c").replace("`", "\\u0060")
    return ["```json", body, "```"]


def metric(value, name):
    if value is None:
        return "N/A"
    with localcontext() as context:
        context.prec = 34
        if name in {"total_return", "max_drawdown", "exposure_fraction"}:
            return f"{Decimal(str(value)) * 100:.4f}%"
        if name == "ending_nav":
            return f"USD {Decimal(str(value)):.2f}"
        if name == "turnover":
            return f"{Decimal(str(value)):.4f} x initial NAV"
    return str(value)


def research_report(artifact):
    spec, dataset = artifact["spec"], artifact["dataset"]
    lines = [
        "# QuantForge Research Report",
        "",
        "Report format: 2",
        "",
        f"Admissibility: {artifact['admissibility']}",
        f"Execution mode: {artifact['mode']}",
        f"Dataset: {dataset['kind']}",
        "",
        "Research simulation only. No investment recommendation or guarantee of performance.",
        "",
    ]
    if artifact["mode"] == "DIAGNOSTIC_INVALID":
        lines += ["INTENTIONALLY FLAWED DIAGNOSTIC: future information was used; results are invalid.", ""]
    lines += [
        "## Research hypothesis",
        "",
        (
            f"After a session closes, if its {text(spec['lookback_sessions'])}-session trailing return is strictly "
            f"greater than {text(spec['threshold_pct'])}%, allocate {text(spec['allocation_fraction'])} of NAV at "
            "the next explicit session's open and exit at that session's close."
        ),
        "",
        f"Symbol: {text(spec['symbol'])}. Sample: {text(spec['sample_start'])} to {text(spec['sample_end'])}.",
        (
            f"Initial NAV: USD {text(spec['initial_nav'])}. Commission: {text(spec['fee_bps_each_side'])} bps per side; "
            f"slippage: {text(spec['slippage_bps_each_side'])} bps per side."
        ),
        "",
        "The diagnostic warning overrides the lawful hypothesis above when mode is DIAGNOSTIC_INVALID.",
        "",
        "## Exact strategy specification",
        "",
        *json_block(spec),
        "",
        "## Planning and correction provenance",
        "",
        *json_block(artifact.get("planning", {"source": "LEGACY_TEMPLATE"})),
        "",
        "## Dataset provenance",
        "",
        *json_block(dataset),
        "",
        "## Computed results",
        "",
    ]
    result = artifact["result"]
    if result is None:
        lines += ["No simulation result is available. No performance metrics are claimed.", ""]
    else:
        lines += ["| Metric | Display value | Exact engine value |", "| --- | --- | --- |"]
        lines += [
            f"| {text(k)} | {text(metric(v, k))} | {text(v) if v is not None else 'N/A'} |"
            for k, v in result["metrics"].items()
        ]
        lines += [
            "",
            "Returns and exposure serialize as fractions: 0.01 means 1%. Costs are bps per side: 1 bp = 0.01%.",
            "Turnover is entry-plus-exit notional divided by initial NAV, not annualized. Sharpe is not estimated.",
            "",
            "### Trade ledger",
            "",
            "| Entry UTC | Exit UTC | Entry price | Exit price | Net trade return |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {text(t['entry_at'])} | {text(t['exit_at'])} | {text(t['entry_price'])} | "
            f"{text(t['exit_price'])} | {metric(t['net_return'], 'total_return')} |"
            for t in result["trades"][:100]
        ]
        if not result["trades"]:
            lines += ["No trades. The flat NAV is a computed outcome."]
        if len(result["trades"]) > 100:
            lines += [f"Showing 100 of {len(result['trades'])} trades; the scientific JSON contains the full ledger."]
        lines += [
            "",
            "### Skips and modeling assumptions",
            "",
            *json_block({"skips": result["skips"], "assumptions": result["assumptions"]}),
            "",
        ]
    lines += ["## Audit coverage and source evidence", ""]
    for finding in artifact["findings"]:
        lines += [
            f"### {text(finding['check_id'])}: {text(finding['status'])}",
            "",
            (
                f"Rule version: {text(finding['rule_version'])}. Severity: {text(finding['severity'])}. "
                f"Execution effect: {text(finding['execution_effect'])}."
            ),
            "",
            text(finding["explanation"]),
            "",
        ]
        if finding["evidence"]:
            lines += json_block(finding["evidence"][:100]) + [""]
            if len(finding["evidence"]) > 100:
                lines += [
                    f"Showing 100 of {len(finding['evidence'])} evidence records; see the full scientific JSON.",
                    "",
                ]
    lines += [
        "## Reproduction fingerprints",
        "",
        *json_block(artifact["versions"]),
        "",
        f"Scientific artifact hash: {artifact['scientific_hash']}",
        "",
        (
            "Use the pinned dataset and exact specification above with the matching implementation and dependency lock. "
            "Download the scientific JSON alongside this report to retain full decisions, trades and audit evidence. "
            "A hash alone is not an independent attestation."
        ),
        "",
        "## Limitations",
        "",
        *[text(item) for item in dataset["limitations"]],
        "",
        "Unverified rules do not establish absence of bias. Costs and fills are simplified assumptions.",
    ]
    return "\n".join(lines) + "\n"


def comparison_report(comparison, left, right):
    before, after = comparison["left"]["metrics"] or {}, comparison["right"]["metrics"] or {}
    lines = [
        "# QuantForge Experiment Comparison",
        "",
        f"Classification: {comparison['classification']}",
        f"Original run: {comparison['left_run_id']}",
        f"New run: {comparison['right_run_id']}",
        "",
        "Synthetic research simulation. This is not evidence of market profitability or statistical significance.",
        "A methodology correction changes information usage; it is not a controlled estimate of performance improvement.",
        "",
        "## Metric comparison",
        "",
        "| Metric | Original | New experiment |",
        "| --- | --- | --- |",
        *[
            f"| {text(key)} | {text(metric(before.get(key), key))} | {text(metric(after.get(key), key))} |"
            for key in sorted(set(before) | set(after))
        ],
        "",
        "## Recorded differences",
        "",
        *json_block({"specification": comparison["spec_diff"], "execution_mode": comparison["mode_diff"]}),
        "",
        "## Changed entry decisions",
        "",
        *json_block(comparison["decision_changes"]),
        "",
        "## Original experiment",
        "",
        left["report"],
        "## New experiment",
        "",
        right["report"],
    ]
    return "\n".join(lines) + "\n"
