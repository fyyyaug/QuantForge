"""Deterministic decimal engine; no model, external network, or generated code."""

from datetime import UTC, datetime, time
from decimal import Decimal, localcontext

from .errors import ResearchError
from .models import BacktestResult, Bar, Decision, Dependency, NavPoint, StrategySpec, Trade

D = Decimal
ENGINE_VERSION = "decimal_daily_v1"


def event(session, hour, minute=0, second=0):
    return datetime.combine(session, time(hour, minute, second), UTC)


def build_decisions(bars: tuple[Bar, ...], spec: StrategySpec, *, diagnostic_future: bool = False):
    decisions, skips = [], []
    with localcontext() as ctx:
        ctx.prec = 34
        for i, bar in enumerate(bars):
            if i + 1 >= len(bars):
                if spec.sample_start <= bar.session <= spec.sample_end:
                    skips.append({"session": bar.session, "reason": "NO_NEXT_SESSION"})
                continue
            entry = bars[i + 1]
            if not spec.sample_start <= entry.session <= spec.sample_end:
                continue
            if i < spec.lookback_sessions:
                skips.append({"session": entry.session, "reason": "WARMUP"})
                continue
            end = entry if diagnostic_future else bar
            start = bars[i - spec.lookback_sessions]
            value = end.close / start.close - 1
            dependencies = tuple(
                Dependency(row_number=b.row_number, session=b.session, value=b.close, available_at=event(b.session, 16))
                for b in (start, end)
            )
            decisions.append(
                Decision(
                    decision_id=f"decision-{i}",
                    session=bar.session,
                    decision_at=event(bar.session, 16, 0, 1),
                    submitted_at=event(bar.session, 16, 0, 2),
                    entry_at=event(entry.session, 9, 30),
                    exit_at=event(entry.session, 16),
                    entry_row=entry.row_number,
                    feature_value=value,
                    triggered=value > spec.threshold_pct / 100,
                    dependencies=dependencies,
                    skip_reason="NON_TRADABLE" if entry.volume == 0 else None,
                )
            )
    return tuple(decisions), tuple(skips)


def simulate(bars, spec, decisions, skips=()):
    by_row = {bar.row_number: bar for bar in bars}
    by_session = {d.entry_at.date(): d for d in decisions}
    trades, points, skipped = [], [], list(skips)
    with localcontext() as ctx:
        ctx.prec = 34
        nav = spec.initial_nav
        peak = nav
        drawdown = D(0)
        turnover = D(0)
        points.append(NavPoint(session=None, nav=nav, session_return=D(0)))
        for bar in bars:
            if not spec.sample_start <= bar.session <= spec.sample_end:
                continue
            daily = D(0)
            decision = by_session.get(bar.session)
            if decision and decision.skip_reason:
                skipped.append(
                    {"session": bar.session, "reason": decision.skip_reason, "decision_id": decision.decision_id}
                )
            elif decision and decision.triggered:
                price = by_row[decision.entry_row]
                gross = price.close / price.open - 1
                fee = 2 * spec.fee_bps_each_side / 10000
                slip = 2 * spec.slippage_bps_each_side / 10000
                net = gross - fee - slip
                daily = spec.allocation_fraction * net
                entry_notional = nav * spec.allocation_fraction
                exit_notional = entry_notional * (1 + gross)
                turnover += entry_notional + exit_notional
                trades.append(
                    Trade(
                        decision_id=decision.decision_id,
                        entry_at=decision.entry_at,
                        exit_at=decision.exit_at,
                        entry_row=price.row_number,
                        entry_price=price.open,
                        exit_price=price.close,
                        entry_notional=entry_notional,
                        exit_notional=exit_notional,
                        gross_return=gross,
                        fee_fraction=fee,
                        slippage_fraction=slip,
                        net_return=net,
                        portfolio_return=daily,
                        fee_amount=entry_notional * fee,
                        slippage_amount=entry_notional * slip,
                    )
                )
            nav *= 1 + daily
            if not nav.is_finite() or nav <= 0 or nav > D("1e24"):
                raise ResearchError(
                    "MODEL_DOMAIN_ERROR", "Cost and return assumptions produce nonpositive or excessive NAV"
                )
            peak = max(peak, nav)
            drawdown = min(drawdown, nav / peak - 1)
            points.append(NavPoint(session=bar.session, nav=nav, session_return=daily))
        count = len(points) - 1
        return BacktestResult(
            trades=tuple(trades),
            nav_series=tuple(points),
            skips=tuple(skipped),
            metrics={
                "total_return": nav / spec.initial_nav - 1,
                "max_drawdown": drawdown,
                "ending_nav": nav,
                "trade_count": len(trades),
                "observation_count": count,
                "exposure_fraction": D(len(trades)) / count if count else D(0),
                "turnover": turnover / spec.initial_nav,
                "sharpe": None,
            },
        )
