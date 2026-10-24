from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from backend import audit
from backend.canonical import digest
from backend.data import validate_data
from backend.engine import build_decisions, event, simulate
from backend.errors import ResearchError
from backend.models import Bar, Decision, Dependency

D = Decimal


def bar(day, opening="100", close="102", volume="100"):
    return Bar(
        row_number=day + 2,
        session=date(2026, 1, 1) + timedelta(days=day),
        symbol="SYNTH",
        open=opening,
        close=close,
        low=min(D(opening), D(close)) / 2,
        high=max(D(opening), D(close)) + 1,
        volume=volume,
    )


def decision(previous, entry, value="0.03", triggered=True):
    return Decision(
        decision_id=f"d-{entry.row_number}",
        session=previous.session,
        decision_at=event(previous.session, 16, 0, 1),
        submitted_at=event(previous.session, 16, 0, 2),
        entry_at=event(entry.session, 9, 30),
        exit_at=event(entry.session, 16),
        entry_row=entry.row_number,
        feature_value=value,
        triggered=triggered,
        dependencies=(
            Dependency(
                row_number=previous.row_number,
                session=previous.session,
                value=previous.close,
                available_at=event(previous.session, 16),
            ),
        ),
    )


def test_hand_calculated_compounding_and_drawdown(service):
    bars = (bar(0), bar(1, close="102"), bar(2, close="99"))
    spec = service.template(overrides={"sample_start": bars[1].session, "sample_end": bars[-1].session})
    decisions = (decision(bars[0], bars[1]), decision(bars[1], bars[2]))
    result = simulate(bars, spec, decisions)
    assert result.nav_series[1].nav == D("10180")
    assert result.metrics["ending_nav"] == D("10057.84")
    assert result.metrics["max_drawdown"] == D("-0.012")
    assert result.metrics["total_return"] == D("0.005784")
    assert result.trades[0].fee_amount == D("10")
    assert result.trades[0].slippage_amount == D("10")


def test_first_loss_uses_initial_peak(service):
    bars = (bar(0), bar(1, close="99"))
    spec = service.template(overrides={"sample_start": bars[1].session, "sample_end": bars[1].session})
    result = simulate(bars, spec, (decision(*bars),))
    assert result.metrics["max_drawdown"] == D("-0.012")


def test_partial_allocation_and_flat_session(service):
    bars = (bar(0), bar(1), bar(2))
    spec = service.template(
        overrides={"sample_start": bars[1].session, "sample_end": bars[2].session, "allocation_fraction": "0.5"}
    )
    result = simulate(bars, spec, (decision(bars[0], bars[1]),))
    assert result.metrics["ending_nav"] == D("10090")
    assert result.nav_series[-1].session_return == 0
    assert result.metrics["exposure_fraction"] == D("0.5")


def test_exact_threshold_and_five_session_warmup(service):
    bars = tuple(bar(i, close="102" if i >= 5 else "100") for i in range(8))
    spec = service.template(overrides={"sample_start": bars[0].session, "sample_end": bars[-1].session})
    decisions, skips = build_decisions(bars, spec)
    assert decisions[0].feature_value == D("0.02")
    assert not decisions[0].triggered
    assert decisions[0].dependencies[0].session == bars[0].session
    assert decisions[0].dependencies[-1].session == bars[5].session
    assert sum(s["reason"] == "WARMUP" for s in skips) == 5
    assert any(s["reason"] == "NO_NEXT_SESSION" for s in skips)


def test_calendar_gap_uses_next_explicit_session(service, catalog):
    spec = service.template(overrides={"lookback_sessions": 1, "threshold_pct": "-100"})
    bars, issues = validate_data(catalog.load(spec.dataset_id), spec)
    assert not issues
    decisions, _ = build_decisions(bars, spec)
    friday = next(d for d in decisions if d.session.weekday() == 4)
    assert friday.entry_at.date().weekday() == 0
    assert audit.timing(decisions).status == "PASS"


def test_warmup_before_sample_is_allowed(service, catalog):
    full = service.template()
    bars, _ = validate_data(catalog.load(full.dataset_id), full)
    spec = service.template(overrides={"sample_start": bars[8].session})
    decisions, skips = build_decisions(bars, spec)
    assert decisions[0].entry_at.date() == bars[8].session
    assert decisions[0].dependencies[0].session < spec.sample_start
    result = simulate(bars, spec, decisions, skips)
    assert all(p.session is None or p.session >= spec.sample_start for p in result.nav_series)


def test_nontradable_session_has_no_fabricated_trade(service):
    bars = tuple(bar(i, volume="0" if i == 2 else "10") for i in range(4))
    spec = service.template(
        overrides={
            "lookback_sessions": 1,
            "threshold_pct": "-100",
            "sample_start": bars[0].session,
            "sample_end": bars[-1].session,
        }
    )
    decisions, skips = build_decisions(bars, spec)
    result = simulate(bars, spec, decisions, skips)
    assert all(t.entry_row != bars[2].row_number for t in result.trades)
    assert any(s["reason"] == "NON_TRADABLE" for s in result.skips)


def test_costs_do_not_increase_nav_for_same_gross_fills(service, catalog):
    free = service.template(overrides={"fee_bps_each_side": "0", "slippage_bps_each_side": "0"})
    paid = service.template()
    bars, _ = validate_data(catalog.load(free.dataset_id), free)
    decisions, skips = build_decisions(bars, free)
    a, b = simulate(bars, free, decisions, skips), simulate(bars, paid, decisions, skips)
    assert len(a.trades) == len(b.trades) > 0
    assert all(x.nav >= y.nav for x, y in zip(a.nav_series, b.nav_series))
    assert audit.costs(free, a).status == "WARN"


def test_no_trades_is_constant_nav_and_na_cost_check(service, catalog):
    spec = service.template(
        overrides={"threshold_pct": "10000", "fee_bps_each_side": "0", "slippage_bps_each_side": "0"}
    )
    bars, _ = validate_data(catalog.load(spec.dataset_id), spec)
    decisions, skips = build_decisions(bars, spec)
    result = simulate(bars, spec, decisions, skips)
    assert result.metrics["trade_count"] == 0
    assert result.metrics["total_return"] == 0
    assert result.metrics["sharpe"] is None
    assert all(p.nav == spec.initial_nav for p in result.nav_series)
    assert audit.costs(spec, result).status == "NOT_APPLICABLE"


def test_nonpositive_nav_rejected(service):
    bars = (bar(0), bar(1, close="0.01"))
    spec = service.template(
        overrides={"fee_bps_each_side": "1000", "sample_start": bars[1].session, "sample_end": bars[1].session}
    )
    with pytest.raises(ResearchError, match="nonpositive"):
        simulate(bars, spec, (decision(*bars),))


@pytest.mark.parametrize(
    "override",
    [
        {"lookback_sessions": 0},
        {"lookback_sessions": True},
        {"lookback_sessions": "5"},
        {"allocation_fraction": "1.1"},
        {"allocation_fraction": "0"},
        {"fee_bps_each_side": "-1"},
        {"fee_bps_each_side": None},
        {"threshold_pct": "NaN"},
        {"initial_nav": "Infinity"},
        {"sample_end": "1900-01-01"},
        {"feature_definition_id": "eval(user_code)"},
        {"execution_mode": "DIAGNOSTIC_INVALID"},
        {"initial_nav": "1e-1000000"},
        {"allocation_fraction": "1e-1000000"},
        {"fee_bps_each_side": "0.0000001"},
        {"threshold_pct": "1e-1000000"},
    ],
)
def test_spec_rejects_unsupported_or_invalid_fields(service, override):
    with pytest.raises((ValidationError, ResearchError)):
        service.template(overrides=override)


def test_decimal_precision_does_not_depend_on_callers_context(service, catalog):
    spec = service.template()
    bars, _ = validate_data(catalog.load(spec.dataset_id), spec)

    def run():
        decisions, skips = build_decisions(bars, spec)
        return digest(simulate(bars, spec, decisions, skips))

    baseline = run()
    with localcontext() as ctx:
        ctx.prec = 6
        assert run() == baseline


@pytest.mark.parametrize("kind", ["future", "after_decision_before_fill", "equal_decision", "missing", "bad_order"])
def test_independent_timing_failures_even_when_no_trade(kind):
    bars = (bar(0), bar(1))
    d = decision(*bars, triggered=False)
    dep = d.dependencies[0]
    if kind == "future":
        dep = dep.model_copy(update={"session": bars[1].session, "available_at": event(bars[1].session, 16)})
    if kind == "after_decision_before_fill":
        dep = dep.model_copy(update={"available_at": d.decision_at + timedelta(hours=1)})
    if kind == "equal_decision":
        dep = dep.model_copy(update={"available_at": d.decision_at})
    d = d.model_copy(update={"dependencies": () if kind == "missing" else (dep,)})
    if kind == "bad_order":
        d = d.model_copy(update={"submitted_at": d.entry_at})
    finding = audit.timing((d,))
    assert finding.status == "FAIL"
    assert finding.execution_effect == "BLOCK"
    assert finding.evidence


def test_naive_timestamp_rejected():
    from datetime import datetime

    with pytest.raises(ValidationError):
        Dependency(row_number=2, session=date(2026, 1, 1), value="1", available_at=datetime(2026, 1, 1))
