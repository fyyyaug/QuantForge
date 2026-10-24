# Backend Foundation Verification Report

Date: October 24, 2026

## Result

The final local regression run passed **87 tests** with no warnings. The suite ran on Windows with Python 3.11.0 and the pinned packages in requirements.lock.

| Check | Observed result |
| --- | --- |
| pytest regression | 87 passed in 4.26 seconds |
| Combined statement/branch coverage | 94.82% (terminal rounded display: 95%) |
| Engine coverage | 100% of measured engine statements and branches |
| Audit coverage | 100% of measured audit statements and branches |
| Real localhost HTTP smoke | Passed |
| Ruff static checks | Passed |
| Ruff formatting check | 19 files already formatted |
| Python compileall | Passed |
| pip dependency consistency | No broken requirements found |

Coverage is a measurement of exercised code, not a proof that every behavior is correct. The HTTP smoke test exercises a real Uvicorn process separately from the in-process API tests. Its temporary process and database are cleaned up.

## Verified behavior

- Independent hand calculation: NAV 10,000 -> 10,180 -> 10,057.84 for a +2% trade followed by a -1% trade with 20 bps round-trip modeled costs. Total return is 0.5784%; maximum drawdown is -1.2%.
- Initial NAV is included when computing drawdown; partial allocation and flat sessions behave as specified.
- Five-session return indexing, exact threshold equality, pre-sample warmup, explicit session gaps, and final-session skips are covered.
- Non-tradable zero-volume sessions do not produce fabricated fills.
- Zero-cost and paid runs use the same gross trade sequence; modeled costs do not increase NAV under those controlled assumptions.
- Three identical pinned runs produce exactly equal scientific artifacts and hashes.
- Numerical execution does not inherit a caller's lower Decimal precision.
- Known future-close leakage, information arriving after a decision but before a fill, equal-boundary ambiguity, missing lineage, and invalid order chronology are detected.
- No-decision samples are Not Applicable for timing coverage rather than falsely passed.
- Missing open prices, duplicate sessions, invalid OHLC relationships, invalid dates, negative volume, nonfinite values, missing columns, unknown symbols, empty data, and corrupt fixture hashes are rejected.
- A03 errors identify source rows and specific missing fields where available.
- Path traversal, arbitrary feature code, diagnostic-mode overrides, nonfinite strategy inputs, extreme Decimal exponents, oversize and chunked request bodies are rejected.
- Exact-revision approvals are required; editing invalidates approval.
- Concurrent retries create one run; repeated execution does not duplicate state events.
- Corrections produce at most one child per proposal and require the exact approved proposal hash.
- A failed child leaves the parent's stored artifact unchanged.
- Cross-workspace reads, comparisons, corrections, and approvals are denied.
- Restart recovery fails interrupted runs explicitly instead of pretending they completed.
- Stored artifact tampering or a missing artifact produces a controlled integrity error.
- Injected execution/persistence failures do not publish successful output or expose internal exception text through the public result.
- A completed workflow with invalid data has BLOCKED admissibility and no numerical result.

## Actual HTTP smoke flow

The smoke script launched a temporary server on a free localhost port and performed:

1. Health request.
2. Template plan creation and exact-hash approval.
3. Normal research execution to COMPLETED.
4. Synthetic intentionally invalid diagnostic execution.
5. Timing-correction proposal and approval.
6. Child research rerun.
7. Comparison confirming the invalid parent remains BLOCKED and the corrected child is ADMISSIBLE_WITHIN_CHECKED_SCOPE.
8. Report retrieval preserving the SYNTHETIC label.

The observed comparison classification was METHODOLOGY_CORRECTION. No credential was printed or committed.

## Environment issue encountered

The restricted execution sandbox prevented Windows asyncio from creating its local socket pair. API tests therefore stalled before entering application code. The final API tests and real HTTP smoke were run with local-network execution permitted and passed. Earlier blocked test processes were stopped.

The test body limiter was also implemented as ordinary ASGI middleware rather than relying on private Request body internals. The final version is covered for oversized streamed input.

## Re-run

From the project root, after installing requirements.lock:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=backend --cov-branch --cov-fail-under=90
.\.venv\Scripts\python.exe -m ruff check backend scripts tests
.\.venv\Scripts\python.exe -m ruff format --check backend scripts tests
.\.venv\Scripts\python.exe scripts/smoke_http.py
.\.venv\Scripts\python.exe -m pip check
```

The CI workflow configures Windows/Linux and Python 3.11/3.12. This report describes local verification; it does not assert that remote CI jobs have passed before their results are available.

## Remaining limits

No tests establish correctness for real market calendars, adjusted historical prices, market liquidity, multi-asset portfolios, production identity, public deployment, a language-model provider, or a durable multi-process worker system. Those features are not implemented.

The single-process service does not enforce a hard CPU kill timeout. Deployment recovery marks interrupted jobs failed rather than resuming them. Non-queued cancellation is unsupported. Artifact hashes detect content changes against stored hashes but are not signatures protecting against a database administrator.

Some defensive branches, startup entrypoint lines, and error wrappers remain outside the measured unit-test coverage. The actual HTTP server launch is checked separately. No claim of zero possible bugs or complete security is made.
