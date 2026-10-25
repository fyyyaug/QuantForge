# QuantForge Experiment Comparison

Classification: CONTROLLED_ASSUMPTION_CHANGE
Original run: 8e89b97ba0ae4ca49a987a039906de88
New run: 0bb22ffd955c417b978951df9b53b1f2

Synthetic research simulation. This is not evidence of market profitability or statistical significance.
A methodology correction changes information usage; it is not a controlled estimate of performance improvement.

## Metric comparison

| Metric | Original | New experiment |
| --- | --- | --- |
| ending_nav | USD 11066.53 | USD 10913.66 |
| exposure_fraction | 70.0000% | 70.0000% |
| max_drawdown | -2.1857% | -2.2857% |
| observation_count | 20 | 20 |
| sharpe | N/A | N/A |
| total_return | 10.6653% | 9.1366% |
| trade_count | 14 | 14 |
| turnover | 29.7880 x initial NAV | 29.5928 x initial NAV |

## Recorded differences

```json
{
  "specification": {
    "fee_bps_each_side": {
      "before": "15",
      "after": "20"
    }
  },
  "execution_mode": {
    "before": "RESEARCH",
    "after": "RESEARCH"
  }
}
```

## Changed entry decisions

```json
{
  "changed_signals": 0,
  "changes": [],
  "before_trade_count": 14,
  "after_trade_count": 14
}
```

## Original experiment

# QuantForge Research Report

Report format: 2

Admissibility: ADMISSIBLE_WITHIN_CHECKED_SCOPE
Execution mode: RESEARCH
Dataset: SYNTHETIC

Research simulation only. No investment recommendation or guarantee of performance.

## Research hypothesis

After a session closes, if its 5-session trailing return is strictly greater than 2%, allocate 1 of NAV at the next explicit session's open and exit at that session's close.

Symbol: SYNTH. Sample: 2026-01-02 to 2026-01-29.
Initial NAV: USD 10000. Commission: 15 bps per side; slippage: 5 bps per side.

The diagnostic warning overrides the lawful hypothesis above when mode is DIAGNOSTIC_INVALID.

## Exact strategy specification

```json
{
  "schema_version": "1",
  "strategy_type": "trailing_momentum",
  "dataset_id": "clean_momentum",
  "dataset_version": "1",
  "dataset_hash": "53c26c6d8e8568132e22d453fef8f7045e6d225eb75062fac7b5bc40a1240f2d",
  "symbol": "SYNTH",
  "sample_start": "2026-01-02",
  "sample_end": "2026-01-29",
  "lookback_sessions": 5,
  "threshold_pct": "2",
  "comparator": "gt",
  "feature_definition_id": "trailing_close_return_v1",
  "decision_policy": "after_close_t",
  "entry_policy": "next_session_open",
  "exit_policy": "entry_session_close",
  "initial_nav": "10000",
  "currency": "USD",
  "allocation_fraction": "1",
  "fee_bps_each_side": "15",
  "slippage_bps_each_side": "5",
  "cost_model_version": "simple_return_deduction_v1"
}
```

## Planning and correction provenance

```json
{
  "correction": {
    "base_spec_hash": "76094326137854559fa76a4c6ac0ab23ae0a0b4cc3c9d5fc0ddb61c088c35321",
    "classification": "CONTROLLED_ASSUMPTION_CHANGE",
    "diff": {
      "fee_bps_each_side": {
        "after": "15",
        "before": "10"
      }
    },
    "finding_id": "A02_MISSING_COSTS",
    "rationale": "Recompute the same signal and gross fills under explicit nonzero modeled costs.",
    "requires_approval": true
  },
  "source": "APPROVED_CORRECTION"
}
```

## Dataset provenance

```json
{
  "dataset_id": "clean_momentum",
  "version": "1",
  "kind": "SYNTHETIC",
  "source": "QuantForge synthetic fixture generator v1",
  "license": "CC0-1.0",
  "symbol": "SYNTH",
  "currency": "USD",
  "timezone": "UTC",
  "calendar": "synthetic_explicit_sessions_v1",
  "adjustment_policy": "synthetic_no_corporate_actions",
  "availability_policy": "Open 09:30 UTC; close published 16:00 UTC; decision 16:00:01 UTC.",
  "byte_hash": "53c26c6d8e8568132e22d453fef8f7045e6d225eb75062fac7b5bc40a1240f2d",
  "row_count": 20,
  "start_session": "2026-01-02",
  "end_session": "2026-01-29",
  "limitations": [
    "Synthetic sessions are authoritative; this is not a historical exchange calendar.",
    "No real liquidity, market impact, taxes, dividends, or corporate actions modeled."
  ]
}
```

## Computed results

| Metric | Display value | Exact engine value |
| --- | --- | --- |
| total_return | 10.6653% | 0.106652961919872429713248598647191 |
| max_drawdown | -2.1857% | -0.0218571428571428571428571428571433 |
| ending_nav | USD 11066.53 | 11066.52961919872429713248598647191 |
| trade_count | 14 | 14 |
| observation_count | 20 | 20 |
| exposure_fraction | 70.0000% | 0.7 |
| turnover | 29.7880 x initial NAV | 29.78802637706659427960628571626802 |
| sharpe | N/A | N/A |

Returns and exposure serialize as fractions: 0.01 means 1%. Costs are bps per side: 1 bp = 0.01%.
Turnover is entry-plus-exit notional divided by initial NAV, not annualized. Sharpe is not estimated.

### Trade ledger

| Entry UTC | Exit UTC | Entry price | Exit price | Net trade return |
| --- | --- | --- | --- | --- |
| 2026-01-12T09:30:00+00:00 | 2026-01-12T16:00:00+00:00 | 106 | 108 | 1.4868% |
| 2026-01-13T09:30:00+00:00 | 2026-01-13T16:00:00+00:00 | 108 | 107 | -1.3259% |
| 2026-01-14T09:30:00+00:00 | 2026-01-14T16:00:00+00:00 | 107 | 112 | 4.2729% |
| 2026-01-15T09:30:00+00:00 | 2026-01-15T16:00:00+00:00 | 112 | 110 | -2.1857% |
| 2026-01-16T09:30:00+00:00 | 2026-01-16T16:00:00+00:00 | 110 | 114 | 3.2364% |
| 2026-01-19T09:30:00+00:00 | 2026-01-19T16:00:00+00:00 | 114 | 113 | -1.2772% |
| 2026-01-20T09:30:00+00:00 | 2026-01-20T16:00:00+00:00 | 113 | 117 | 3.1398% |
| 2026-01-21T09:30:00+00:00 | 2026-01-21T16:00:00+00:00 | 117 | 116 | -1.2547% |
| 2026-01-22T09:30:00+00:00 | 2026-01-22T16:00:00+00:00 | 116 | 120 | 3.0483% |
| 2026-01-23T09:30:00+00:00 | 2026-01-23T16:00:00+00:00 | 120 | 118 | -2.0667% |
| 2026-01-26T09:30:00+00:00 | 2026-01-26T16:00:00+00:00 | 118 | 123 | 3.8373% |
| 2026-01-27T09:30:00+00:00 | 2026-01-27T16:00:00+00:00 | 123 | 122 | -1.2130% |
| 2026-01-28T09:30:00+00:00 | 2026-01-28T16:00:00+00:00 | 122 | 126 | 2.8787% |
| 2026-01-29T09:30:00+00:00 | 2026-01-29T16:00:00+00:00 | 126 | 124 | -1.9873% |

### Skips and modeling assumptions

```json
{
  "skips": [
    {
      "session": "2026-01-05",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-06",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-07",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-08",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-09",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-29",
      "reason": "NO_NEXT_SESSION"
    }
  ],
  "assumptions": [
    "Research simulation only; fractional notional, long only, no leverage or overnight carry.",
    "Fees and slippage deducted from gross return against entry notional, not shifted fill prices.",
    "Turnover is entry-plus-exit notional divided by initial NAV, not annualized."
  ]
}
```

## Audit coverage and source evidence

### A03_DATA_INTEGRITY: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

Pinned synthetic dataset passed supported integrity checks

### A01_LOOKAHEAD: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

All recorded dependencies precede decisions and fills

### A02_MISSING_COSTS: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

Explicit nonzero modeled costs applied; realism remains unverified

```json
[
  {
    "trade_count": 14,
    "fee_bps_each_side": "15",
    "slippage_bps_each_side": "5"
  }
]
```

### A04_SPLIT_LEAKAGE: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No training/test selection provenance in MVP

### A05_OVERFITTING_RISK: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No complete search history or independent holdout evidence

### A06_SURVIVORSHIP: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No historical point-in-time universe or delisting coverage

## Reproduction fingerprints

```json
{
  "engine": "decimal_daily_v1",
  "rules": "1",
  "schema": "1",
  "precision": 34,
  "python": "3.12.14",
  "pydantic": "2.14.1",
  "source_hash": "0bbc5ec295bd282ec9d5bae5d54a670e888d16c8c3126f2d545f80da745850f9",
  "dependency_lock_hash": "3daea0bc006f978a17c385bde0869d20cf26b8274e0b2e2eaf2836bcb7c5d000",
  "normalized_data_hash": "87e2f47e1c6ba94539c337ea4778556b414fb0fa68d5d286dcca1bb8bb2141ba"
}
```

Scientific artifact hash: 0cd412af24cf5404605981d39e55a8ead768fb24d5c50c94eeef712108f3c1f4

Use the pinned dataset and exact specification above with the matching implementation and dependency lock. Download the scientific JSON alongside this report to retain full decisions, trades and audit evidence. A hash alone is not an independent attestation.

## Limitations

Synthetic sessions are authoritative; this is not a historical exchange calendar.
No real liquidity, market impact, taxes, dividends, or corporate actions modeled.

Unverified rules do not establish absence of bias. Costs and fills are simplified assumptions.

## New experiment

# QuantForge Research Report

Report format: 2

Admissibility: ADMISSIBLE_WITHIN_CHECKED_SCOPE
Execution mode: RESEARCH
Dataset: SYNTHETIC

Research simulation only. No investment recommendation or guarantee of performance.

## Research hypothesis

After a session closes, if its 5-session trailing return is strictly greater than 2%, allocate 1 of NAV at the next explicit session's open and exit at that session's close.

Symbol: SYNTH. Sample: 2026-01-02 to 2026-01-29.
Initial NAV: USD 10000. Commission: 20 bps per side; slippage: 5 bps per side.

The diagnostic warning overrides the lawful hypothesis above when mode is DIAGNOSTIC_INVALID.

## Exact strategy specification

```json
{
  "schema_version": "1",
  "strategy_type": "trailing_momentum",
  "dataset_id": "clean_momentum",
  "dataset_version": "1",
  "dataset_hash": "53c26c6d8e8568132e22d453fef8f7045e6d225eb75062fac7b5bc40a1240f2d",
  "symbol": "SYNTH",
  "sample_start": "2026-01-02",
  "sample_end": "2026-01-29",
  "lookback_sessions": 5,
  "threshold_pct": "2",
  "comparator": "gt",
  "feature_definition_id": "trailing_close_return_v1",
  "decision_policy": "after_close_t",
  "entry_policy": "next_session_open",
  "exit_policy": "entry_session_close",
  "initial_nav": "10000",
  "currency": "USD",
  "allocation_fraction": "1",
  "fee_bps_each_side": "20",
  "slippage_bps_each_side": "5",
  "cost_model_version": "simple_return_deduction_v1"
}
```

## Planning and correction provenance

```json
{
  "correction": {
    "base_spec_hash": "486ce9c8023334f8b9578da9f835bc7127302f28a4507f324bffbe3bd2bdebeb",
    "classification": "CONTROLLED_ASSUMPTION_CHANGE",
    "diff": {
      "fee_bps_each_side": {
        "after": "20",
        "before": "15"
      }
    },
    "finding_id": "A02_MISSING_COSTS",
    "rationale": "Recompute the same signal and gross fills under explicit nonzero modeled costs.",
    "requires_approval": true
  },
  "source": "APPROVED_CORRECTION"
}
```

## Dataset provenance

```json
{
  "dataset_id": "clean_momentum",
  "version": "1",
  "kind": "SYNTHETIC",
  "source": "QuantForge synthetic fixture generator v1",
  "license": "CC0-1.0",
  "symbol": "SYNTH",
  "currency": "USD",
  "timezone": "UTC",
  "calendar": "synthetic_explicit_sessions_v1",
  "adjustment_policy": "synthetic_no_corporate_actions",
  "availability_policy": "Open 09:30 UTC; close published 16:00 UTC; decision 16:00:01 UTC.",
  "byte_hash": "53c26c6d8e8568132e22d453fef8f7045e6d225eb75062fac7b5bc40a1240f2d",
  "row_count": 20,
  "start_session": "2026-01-02",
  "end_session": "2026-01-29",
  "limitations": [
    "Synthetic sessions are authoritative; this is not a historical exchange calendar.",
    "No real liquidity, market impact, taxes, dividends, or corporate actions modeled."
  ]
}
```

## Computed results

| Metric | Display value | Exact engine value |
| --- | --- | --- |
| total_return | 9.1366% | 0.091365921501320369781869252919909 |
| max_drawdown | -2.2857% | -0.0228571428571428571428571428571433 |
| ending_nav | USD 10913.66 | 10913.65921501320369781869252919909 |
| trade_count | 14 | 14 |
| observation_count | 20 | 20 |
| exposure_fraction | 70.0000% | 0.7 |
| turnover | 29.5928 x initial NAV | 29.59276740836406018081102378461613 |
| sharpe | N/A | N/A |

Returns and exposure serialize as fractions: 0.01 means 1%. Costs are bps per side: 1 bp = 0.01%.
Turnover is entry-plus-exit notional divided by initial NAV, not annualized. Sharpe is not estimated.

### Trade ledger

| Entry UTC | Exit UTC | Entry price | Exit price | Net trade return |
| --- | --- | --- | --- | --- |
| 2026-01-12T09:30:00+00:00 | 2026-01-12T16:00:00+00:00 | 106 | 108 | 1.3868% |
| 2026-01-13T09:30:00+00:00 | 2026-01-13T16:00:00+00:00 | 108 | 107 | -1.4259% |
| 2026-01-14T09:30:00+00:00 | 2026-01-14T16:00:00+00:00 | 107 | 112 | 4.1729% |
| 2026-01-15T09:30:00+00:00 | 2026-01-15T16:00:00+00:00 | 112 | 110 | -2.2857% |
| 2026-01-16T09:30:00+00:00 | 2026-01-16T16:00:00+00:00 | 110 | 114 | 3.1364% |
| 2026-01-19T09:30:00+00:00 | 2026-01-19T16:00:00+00:00 | 114 | 113 | -1.3772% |
| 2026-01-20T09:30:00+00:00 | 2026-01-20T16:00:00+00:00 | 113 | 117 | 3.0398% |
| 2026-01-21T09:30:00+00:00 | 2026-01-21T16:00:00+00:00 | 117 | 116 | -1.3547% |
| 2026-01-22T09:30:00+00:00 | 2026-01-22T16:00:00+00:00 | 116 | 120 | 2.9483% |
| 2026-01-23T09:30:00+00:00 | 2026-01-23T16:00:00+00:00 | 120 | 118 | -2.1667% |
| 2026-01-26T09:30:00+00:00 | 2026-01-26T16:00:00+00:00 | 118 | 123 | 3.7373% |
| 2026-01-27T09:30:00+00:00 | 2026-01-27T16:00:00+00:00 | 123 | 122 | -1.3130% |
| 2026-01-28T09:30:00+00:00 | 2026-01-28T16:00:00+00:00 | 122 | 126 | 2.7787% |
| 2026-01-29T09:30:00+00:00 | 2026-01-29T16:00:00+00:00 | 126 | 124 | -2.0873% |

### Skips and modeling assumptions

```json
{
  "skips": [
    {
      "session": "2026-01-05",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-06",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-07",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-08",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-09",
      "reason": "WARMUP"
    },
    {
      "session": "2026-01-29",
      "reason": "NO_NEXT_SESSION"
    }
  ],
  "assumptions": [
    "Research simulation only; fractional notional, long only, no leverage or overnight carry.",
    "Fees and slippage deducted from gross return against entry notional, not shifted fill prices.",
    "Turnover is entry-plus-exit notional divided by initial NAV, not annualized."
  ]
}
```

## Audit coverage and source evidence

### A03_DATA_INTEGRITY: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

Pinned synthetic dataset passed supported integrity checks

### A01_LOOKAHEAD: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

All recorded dependencies precede decisions and fills

### A02_MISSING_COSTS: PASS

Rule version: 1. Severity: INFO. Execution effect: NONE.

Explicit nonzero modeled costs applied; realism remains unverified

```json
[
  {
    "trade_count": 14,
    "fee_bps_each_side": "20",
    "slippage_bps_each_side": "5"
  }
]
```

### A04_SPLIT_LEAKAGE: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No training/test selection provenance in MVP

### A05_OVERFITTING_RISK: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No complete search history or independent holdout evidence

### A06_SURVIVORSHIP: UNVERIFIED

Rule version: 1. Severity: INFO. Execution effect: NONE.

No historical point-in-time universe or delisting coverage

## Reproduction fingerprints

```json
{
  "engine": "decimal_daily_v1",
  "rules": "1",
  "schema": "1",
  "precision": 34,
  "python": "3.12.14",
  "pydantic": "2.14.1",
  "source_hash": "0bbc5ec295bd282ec9d5bae5d54a670e888d16c8c3126f2d545f80da745850f9",
  "dependency_lock_hash": "3daea0bc006f978a17c385bde0869d20cf26b8274e0b2e2eaf2836bcb7c5d000",
  "normalized_data_hash": "87e2f47e1c6ba94539c337ea4778556b414fb0fa68d5d286dcca1bb8bb2141ba"
}
```

Scientific artifact hash: b13bf7c474ef61df5074efecb179146736f2debf47b74a2b0ff9a0aab87c25cc

Use the pinned dataset and exact specification above with the matching implementation and dependency lock. Download the scientific JSON alongside this report to retain full decisions, trades and audit evidence. A hash alone is not an independent attestation.

## Limitations

Synthetic sessions are authoritative; this is not a historical exchange calendar.
No real liquidity, market impact, taxes, dividends, or corporate actions modeled.

Unverified rules do not establish absence of bias. Costs and fills are simplified assumptions.

