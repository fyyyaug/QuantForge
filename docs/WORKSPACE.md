# Research Workspace

For step-by-step end-user instructions, see the [User Guide](USER_GUIDE.md).

The local web workspace is implemented in buildless HTML, CSS, and JavaScript modules, served by the existing FastAPI process. There is no separate frontend server or production JavaScript dependency. Node.js is used only for development checks.

## Start

Follow the Python environment and private token setup in README.md, then run python -m backend. Open http://127.0.0.1:8000/ and connect using the same QUANTFORGE_API_TOKEN configured for that server.

For private mode, the browser keeps the token only in tab memory. Refreshing requires reconnecting; the server's saved experiments remain in SQLite. Disconnecting clears the current token and research views. This is local development authentication, not public account management.

## Implemented experience

1. Select an explicitly synthetic dataset and edit the supported strategy parameters.
2. Inspect the exact specification, sample, cost assumptions, hash, and decision/execution timeline.
3. Check the review acknowledgment and approve the exact plan revision.
4. Inspect computed NAV, returns, drawdown, exposure, trade count, trade ledger, and skipped sessions.
5. Inspect all six audit coverage records, including unsupported checks marked Unverified.
6. Review an allowed correction diff and approve a separate child experiment.
7. Compare saved original and child results; neither artifact is overwritten.
8. Reopen saved runs from scoped history; reopening a child restores its comparison.

The guided diagnostic defaults to the allowlisted `timing_trap` future-close case; the original `leaky_next_close` case remains available through its explicit API parameter. It is marked invalid before execution, in results, in audit, and in its report. Matching before/after metrics do not imply that a future-information dependency is valid.

The browser draws charts from engine-provided NAV series. JavaScript converts Decimal strings to numbers only for chart coordinates and display rounding; the scientific arithmetic and stored results remain on the backend. Independent chart scales and lack of statistical significance are disclosed in comparison.

## Error and empty states

If demo initialization or reconnection fails while a session is still active, the access page retains an **End existing demo session** control. Ending it explicitly revokes the cookie before a new session is requested; failed reconnection never silently replaces the session. Minute/hour rate limits still require waiting, and new sessions remain subject to the service issuance limit.

- Invalid credentials leave the user outside the workspace with a reconnect message.
- Invalid form values are rejected by native controls/client checks and again by backend contracts.
- Dataset integrity failures show Blocked, no performance chart, no fake metrics, and row/field evidence.
- Zero trades show computed constant NAV and an empty trade ledger, not an application error.
- Operationally failed runs show their safe error code and retain access to history.
- Requests time out after 30 seconds. The message explains that server execution may still have finished and recommends checking history; retries of the same approved plan reuse its idempotency key.
- Duplicate clicks are disabled while work is in progress. Navigation cannot change the active experiment mid-request.

## Access and assets

Protected calls use the Authorization header and same-origin fetch. No credential is placed in a URL or browser storage. Workspace history is resolved from server authentication and limited to the latest 50 rows in the UI.

Only frontend/assets is mounted publicly; tests, development dependencies, manifests, backend code, and runtime storage are not part of that static mount. The workspace uses a same-origin Content Security Policy without unsafe-inline, plus no-store, nosniff, no-referrer, and frame-denial headers.

Dynamic text is escaped before HTML insertion. Numeric chart coordinates are finite-checked. The application does not render Markdown as raw HTML or execute model-generated content.

## Frontend checks

Requires Node.js 24 for the checked development workflow:

```powershell
npm ci --prefix frontend
npm test --prefix frontend
npm run format:check --prefix frontend
node --check frontend/assets/app.js
```

The application itself does not require npm install to run. Prettier is a pinned development-only dependency. Presentation tests cover escaping, unavailable values, flat charts, parameter boundaries, and audit labels.

Backend tests cover authenticated history, scoped limits, static responses, static-path isolation, and security headers in addition to the existing numerical/workflow suite. The test suite also prevents recurrence of the request-body replay issue that initially stalled static file responses.

## Browser QA

The following were exercised manually in Chrome against an isolated local synthetic workspace:

- Valid connection, invalid token rejection, disconnect and reconnect.
- Normal plan review, approval, actual backtest results, and ledger.
- Invalid diagnostic, A01 evidence, correction review, child execution and comparison.
- Missing-open dataset blocked with row 10 / open evidence.
- High-threshold zero-trade experiment with constant NAV.
- Zero-cost warning and a separately approved nonzero-cost sensitivity run.
- Scoped history and restoration of a child comparison.
- Stopped-backend refresh produces a controlled connection message and preserves the visible history.
- Desktop layout and 390-pixel mobile viewport; no document-level horizontal overflow was observed. Wide tables scroll within their containers.

The report-download control was triggered without a browser script error. Although the browser tool's completion event timed out, its downloaded report appeared in the test working directory. That concrete output file was checked against the persisted server artifact: all 1,405 bytes matched the saved report text and included the SYNTHETIC label. No access to the browser's internal downloads page was needed for this artifact comparison.

Report/JSON downloads use the already retrieved saved artifact, a temporary Blob URL, and a generated download filename. They do not put the workspace credential in a download URL. The report and artifact API remain available independently.

## Remaining scope

An optional Claude planner adapter is implemented; live-provider validation remains pending credentials. Real historical data, production identity, durable workers, and cross-run agent memory remain unimplemented. Public-demo code and a disk-backed Render Blueprint are prepared, but a public URL and cloud acceptance remain to be verified. The UI does not imply otherwise. Existing engine assumptions and limitations continue to apply.

## Anonymous demonstration mode

Set `QUANTFORGE_PUBLIC_DEMO=true` to display **Try the live demo**. Each browser receives an isolated cookie-authenticated workspace. Refresh resumes the same unexpired session and history. Use a different browser profile to test a different visitor; tabs share the session cookie. **End demo** revokes access. The landing page discloses the lifetime and run allowance; the connected workspace shows its UTC expiry. Use `QUANTFORGE_COOKIE_SECURE=true` for production HTTPS and false only for local HTTP.

A human-readable timing panel now shows the actual source row, decision time, opening entry and input availability before the raw audit records. Comparisons report the number of changed entry signals and show original/new actions. These are derived from saved decisions, without performance promises. The intentionally constructed `timing_trap` fixture yields different entry dates under flawed and corrected methodology; the original equal-result fixture is unchanged.

See [Deployment](DEPLOYMENT.md) for complete limits, cleanup, persistence, and the external-device gate. This section describes implementation; browser and HTTP verification for the current revision are recorded in TEST_REPORT.md.

## Current review and evidence features

Optional AI planning appears above the template with an explicit configured/unconfigured label. A configured request requires acknowledgement that the hypothesis is sent to Anthropic; drafts must still be reviewed and approved. Missing configuration, provider failures and unsupported output leave the template usable. See PLANNING.md for exact boundaries and evaluation status.

Cost forms propose a real assumption change, display the before/after costs, and disable unchanged or invalid input. Comparison pages can export a single Markdown document containing both experiments. New research reports retain full strategy fields, units, source evidence and scientific fingerprints; scientific JSON remains available for all underlying records.

The home screen links to the audit-evaluation table. Its 26 generated synthetic controls are separate from the fixed product CSVs; it explicitly disclaims real-market detection rates and external-benchmark status. The browser regression now exercises desktop and 390-pixel mobile flows automatically, including a fix that keeps offscreen table captions inside their scroll container.
