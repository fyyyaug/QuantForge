# QuantForge Verification Report

Date: October 25, 2026. Scope: local research-delivery improvements and integration with the remote demo-recovery changes. No public deployment, remote CI pass, independent user study or real-provider semantic result is claimed.

## Observed results

| Check | Observed result |
| --- | --- |
| Backend regression | 146 passed, no warnings |
| Statement/branch coverage | 96.33% |
| Engine, audit, generated controls and report coverage | 100% of measured statements/branches |
| Planner adapter coverage | 98%; simulated provider contract/error cases |
| Frontend helper and session-recovery tests | 10 passed |
| Browser regression | Chromium, desktop 1440x1050 and mobile 390x844 passed |
| Generated audit controls | 26/26 expected outcomes matched |
| Real HTTP smoke | Passed, private + anonymous sessions, evaluation and comparison export |
| Ruff / Prettier / JavaScript syntax / dependency consistency | Passed |

Environment: macOS arm64, Python 3.12.14, pinned requirements.lock, Node.js 24.22.1 and Playwright 1.62.1 / Chromium 151. Coverage measures exercised code, not complete correctness or real-world detection rates.

## Changes verified

The merged error handler retains field-validation details together with session-expiry handling and demo quota/rate-limit guidance. The remote session-recovery test now supplies the evaluation response used by the home screen; it verifies explicit logout and reconnection after exhaustion. CI runs all frontend unit tests, including this regression. The complete backend, frontend, HTTP smoke and desktop/mobile browser checks above passed again after integration. The user guide now describes optional Claude planning and comparison exports.

Cost forms propose values different from current costs, reject unchanged/zero-total/invalid-precision input before submission and show the actual assumption diff. The browser test specifically begins at commission 10/slippage 5, prevents submitting those unchanged values, then completes two separate approved cost corrections. Original runs remain in history.

New research reports include exact specification, parameter units, dataset provenance, planning/correction source, trade ledger, evidence timestamps and reproducibility fingerprints. Tables disclose truncation beyond 100 trade/evidence records; complete scientific JSON is still downloadable. Comparison exports contain a metric table, both run IDs, changed decisions, both saved results and their warnings. [Actual cost-comparison export from the disposable browser test](examples/cost-comparison-report.md) is included as an example; it is synthetic, not market evidence. Existing stored reports are not rewritten.

The new schema adds plan_context/run_context with cascading ownership-linked lifecycle, and a planner-call ledger. Plans/runs without context read as LEGACY_TEMPLATE; immutable artifacts remain intact. A valid model draft cannot execute without exact-hash approval. Plan provenance survives save/read/run/report. Request validation exposes only allowlisted field names, not raw input.

## Numerical and audit regression

The original hand calculation remains NAV 10,000 -> 10,180 -> 10,057.84, total return 0.5784% and drawdown -1.2%. Identical pinned runs still produce equal scientific artifacts. Warmup, strict threshold equality, initial-NAV drawdown, partial allocation, session gaps, zero trades, data errors, causality, ownership, idempotency, failures and restart recovery remain covered.

The timing-trap diagnostic still calculates +83.7684% before correction and -50.8060% afterward from deliberately constructed synthetic prices. There are seven trades on each side but disjoint entry dates and 14 changed signals. The original equal-result diagnostic fixture remains unchanged.

[Generated audit-control results](evaluation/README.md) use two independent seeds and 24-session datasets rather than the product CSVs. There are 26 labelled controls for A01-A03, including legal timing, future close, information arriving between decision/fill, equal boundaries, missing lineage, zero/nonzero costs, missing open, duplicate dates, invalid OHLC, negative volume and nonfinite prices. No false positives/negatives occurred within this constructed set. These are not an external blind benchmark, arbitrary-strategy test or estimate of live detection accuracy. A04-A06 remain Unverified.

## Browser verification

frontend/tests/browser.e2e.mjs starts a temporary local server with model planning explicitly disabled and isolated temporary SQLite storage. Both desktop and mobile passed these scenarios:

1. Anonymous connection and template plan approval.
2. Unchanged-cost prevention and consecutive cost corrections.
3. Downloading and inspecting the complete comparison report.
4. Diagnostic audit timeline, correction and 14 changed entry signals.
5. Reload/session restoration and reopening a child comparison from history.
6. Separate browser-context isolation and denied cross-workspace artifact access.
7. Invalid-data Blocked state without a fabricated chart.
8. Zero-trade result and empty ledger.
9. The 26-control evaluation view.
10. Offline error handling, preserved history and recovery.

No page JavaScript errors were observed. A mobile document-overflow failure was found and fixed by positioning the table scroll container so hidden captions remain contained. The final desktop and mobile history pages passed the no-document-overflow check. [Desktop comparison screenshot](screenshots/comparison-v2-desktop.png) records the actual UI. Per-run outputs remain under ignored .quantforge-browser-tests/.

The CI configuration includes a separate Chromium browser job and retains its test outputs for three days. This report does not claim those remote jobs have run or passed.

## Optional Claude planning verification

The adapter implements fixed-endpoint HTTPS, strict JSON output schema, local specification validation, bounded calls/tokens, no redirects, no implicit approval, safe errors and persistent request allowances. Tests simulate successful responses, malformed/oversize/refused/truncated output, unsafe extra fields, missing required fields, out-of-range values, clarification/unsupported outcomes, provider HTTP/timeout failures, secret non-reflection and global/per-workspace limits across restarts.

Ordinary pytest, HTTP smoke and browser regression explicitly disable live model calls. No Anthropic credential was configured for this work. No paid inference occurred. The semantic accuracy of an actual model, account permissions, model availability and latency are unverified. Ten public labelled prompts and an explicit opt-in evaluation command are provided in PLANNING.md. The labels are expectations, not measured model outcomes. Without configuration the UI says AI NOT CONFIGURED and the template path remains usable.

## Real HTTP and reproducibility

scripts/smoke_http.py passed a real Uvicorn flow with private plan approval, normal run, diagnostic, correction, comparison, research report, generated evaluation, combined comparison report, anonymous cookie session, isolated history and logout. Temporary processes/databases were cleaned up without printing credentials. Listening sockets and browser execution required explicit local execution permission; the backend regression ran in the sandbox.

Re-run from the repository root:

```sh
python -m pytest -q --cov=backend --cov-branch --cov-fail-under=90
python -m ruff check backend scripts tests
python -m ruff format --check backend scripts tests
python scripts/smoke_http.py
python scripts/evaluate_audit.py
npm ci --prefix frontend
npm test --prefix frontend
npm run format:check --prefix frontend
# From frontend/: npx playwright install --with-deps chromium
npm run test:e2e --prefix frontend
```

Set QUANTFORGE_PYTHON if Python is not available as python on PATH. Installing Playwright browsers requires network access. Live model evaluation requires explicit provider configuration and --live; it is not part of the commands above or CI.

## Remaining limits

Real historical markets/calendars, corporate actions, liquidity, multi-asset portfolios, production accounts, distributed rate limiting, hard CPU kill limits and resumable durable jobs remain outside implemented/verified scope. Local browser/HTTP success does not establish public HTTPS, cloud disk persistence or external-device availability. No claim of profitability or winning an award follows from this verification.
