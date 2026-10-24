"""Versioned contracts. Decimal values serialize as strings to preserve precision."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

D = Decimal
Positive = Annotated[Decimal, Field(gt=0, le=D("1e12"), max_digits=24, decimal_places=12, allow_inf_nan=False)]
Cost = Annotated[Decimal, Field(ge=0, le=1000, max_digits=12, decimal_places=6, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StrategySpec(Contract):
    schema_version: Literal["1"] = "1"
    strategy_type: Literal["trailing_momentum"] = "trailing_momentum"
    dataset_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
    dataset_version: Literal["1"] = "1"
    dataset_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    symbol: str = Field(min_length=1, max_length=20)
    sample_start: date
    sample_end: date
    lookback_sessions: int = Field(default=5, ge=1, le=252, strict=True)
    threshold_pct: Decimal = Field(
        default=D("2"), ge=-100, le=10000, max_digits=16, decimal_places=8, allow_inf_nan=False
    )
    comparator: Literal["gt"] = "gt"
    feature_definition_id: Literal["trailing_close_return_v1"] = "trailing_close_return_v1"
    decision_policy: Literal["after_close_t"] = "after_close_t"
    entry_policy: Literal["next_session_open"] = "next_session_open"
    exit_policy: Literal["entry_session_close"] = "entry_session_close"
    initial_nav: Positive = D("10000")
    currency: Literal["USD"] = "USD"
    allocation_fraction: Decimal = Field(
        default=D("1"), gt=0, le=1, max_digits=13, decimal_places=12, allow_inf_nan=False
    )
    fee_bps_each_side: Cost = D("5")
    slippage_bps_each_side: Cost = D("5")
    cost_model_version: Literal["simple_return_deduction_v1"] = "simple_return_deduction_v1"

    @field_validator("initial_nav")
    @classmethod
    def bounded_nav(cls, value):
        if value > D("1e12"):
            raise ValueError("initial_nav exceeds model limit")
        return value

    @model_validator(mode="after")
    def ordered_sample(self):
        if self.sample_end < self.sample_start:
            raise ValueError("sample_end must not precede sample_start")
        return self


class DatasetManifest(Contract):
    dataset_id: str
    version: Literal["1"] = "1"
    kind: Literal["SYNTHETIC"] = "SYNTHETIC"
    source: str = "QuantForge synthetic fixture generator v1"
    license: str = "CC0-1.0"
    symbol: str = "SYNTH"
    currency: Literal["USD"] = "USD"
    timezone: Literal["UTC"] = "UTC"
    calendar: Literal["synthetic_explicit_sessions_v1"] = "synthetic_explicit_sessions_v1"
    adjustment_policy: Literal["synthetic_no_corporate_actions"] = "synthetic_no_corporate_actions"
    availability_policy: str = "Open 09:30 UTC; close published 16:00 UTC; decision 16:00:01 UTC."
    byte_hash: str
    row_count: int
    start_session: date
    end_session: date
    limitations: tuple[str, ...] = (
        "Synthetic sessions are authoritative; this is not a historical exchange calendar.",
        "No real liquidity, market impact, taxes, dividends, or corporate actions modeled.",
    )


class Bar(Contract):
    row_number: int
    session: date
    symbol: str
    open: Positive
    high: Positive
    low: Positive
    close: Positive
    volume: Decimal = Field(ge=0, le=D("1e16"), max_digits=24, decimal_places=8, allow_inf_nan=False)


class DataIssue(Contract):
    row_number: int | None = None
    field: str
    reason: str


class Dependency(Contract):
    row_number: int
    session: date
    field: Literal["close"] = "close"
    value: Decimal
    available_at: datetime

    @field_validator("available_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("availability must be timezone-aware")
        return value


class Decision(Contract):
    decision_id: str
    session: date
    decision_at: datetime
    submitted_at: datetime
    entry_at: datetime
    exit_at: datetime
    entry_row: int
    feature_value: Decimal
    triggered: bool
    dependencies: tuple[Dependency, ...]
    skip_reason: str | None = None

    @field_validator("decision_at", "submitted_at", "entry_at", "exit_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("events must be timezone-aware")
        return value


class Finding(Contract):
    check_id: str
    rule_version: Literal["1"] = "1"
    status: Literal["PASS", "WARN", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"]
    severity: Literal["INFO", "MEDIUM", "HIGH"] = "INFO"
    execution_effect: Literal["NONE", "BLOCK"] = "NONE"
    explanation: str
    evidence: tuple[dict, ...] = ()
    requires_rerun: bool = False


class Trade(Contract):
    decision_id: str
    entry_at: datetime
    exit_at: datetime
    entry_row: int
    entry_price: Decimal
    exit_price: Decimal
    entry_notional: Decimal
    exit_notional: Decimal
    gross_return: Decimal
    fee_fraction: Decimal
    slippage_fraction: Decimal
    net_return: Decimal
    portfolio_return: Decimal
    fee_amount: Decimal
    slippage_amount: Decimal


class NavPoint(Contract):
    session: date | None
    nav: Decimal
    session_return: Decimal


class BacktestResult(Contract):
    trades: tuple[Trade, ...]
    nav_series: tuple[NavPoint, ...]
    metrics: dict[str, Decimal | int | None]
    skips: tuple[dict, ...]
    assumptions: tuple[str, ...] = (
        "Research simulation only; fractional notional, long only, no leverage or overnight carry.",
        "Fees and slippage deducted from gross return against entry notional, not shifted fill prices.",
        "Turnover is entry-plus-exit notional divided by initial NAV, not annualized.",
    )
