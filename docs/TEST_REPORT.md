# QuantForge Verification Report

Date: October 24, 2026. Scope: local public-demo delivery changes. No public deployment, remote CI success or independent user study is claimed.

## Observed results

| Check | Result |
| --- | --- |
| Backend regression | 112 passed, no warnings |
| Statement/branch coverage | 95.41% |
| Engine, audit and demo-access coverage | 100% of measured statements and branches |
| Frontend presentation tests | 7 passed |
| JavaScript syntax | Passed |
| Real localhost HTTP smoke | Passed: private and anonymous-cookie workflows |
| Ruff static and format checks | Passed |
| Prettier frontend and Blueprint formatting | Passed |
| Git whitespace/diff check | Passed |

Environment: macOS arm64, Python 3.12.14, pinned requirements.lock packages and bundled Node.js 24. Coverage includes the new config, anonymous-session, API, and quota code. Coverage is exercised code, not proof of complete correctness.

## Numerical and audit checks

- The independent hand calculation still produces NAV 10,000 -> 10,180 -> 10,057.84, total return 0.5784%, and maximum drawdown -1.2%.
- Three identical pinned runs retain exactly equal scientific outputs and hashes.
- Five-session indexing, strict threshold equality, pre-sample warmup, explicit session gaps, zero-volume skips, final-session behavior, initial-NAV drawdown and partial allocation remain covered.
- Timing tests detect future information, information arriving after a decision but before a fill, equal-boundary ambiguity, missing lineage and invalid order chronology, including non-triggered decisions.
- A03 rejects malformed OHLCV and records source rows/fields. A02 compares zero/nonzero modeled costs on the same gross fills. A04-A06 remain Unverified.
- The new default timing_trap actually recalculates an intentionally invalid +83.7684% result and a corrected -50.8060% result from deliberately constructed synthetic prices. Both contain seven trades, but their entry dates are disjoint and 14 entry signals change. No return is stored in frontend code.
- The original leaky_next_close fixture and its matching control retain their original bytes and remain supported explicitly. Identical results in that case still do not validate future-information use.

## Public-session and persistence checks

- Anonymous mode is opt-in; private credentials and ownership checks continue to work.
- Session responses do not return credentials or workspace IDs. Stored session credentials are hashed. Cookie attributes include HttpOnly/SameSite=Strict; production adds Secure and the host-only prefix.
- A second demo visitor cannot read or correct another workspace's runs. Demo visitors cannot read private runs. Comparison and exact-approval ownership boundaries remain enforced.
- Cookie-authenticated writes require a custom same-origin header and reject foreign Origins. Cross-origin preflight does not grant permission. Bad supplied bearer credentials cannot silently fall back to a cookie.
- Session issuance, authenticated request allowances, plan/correction counts and run counts are bounded. Runs and their correction children share the same allowance.
- Idempotent retries return an existing run at the creation limit; rejected creations do not publish extra runs.
- Sessions, saved runs, issuance counters and total request allowances survive reopening the database.
- Expired sessions immediately fail authentication. Cleanup removes expired demo parents/children, plans, approvals, events and unreferenced artifacts. It preserves private history, artifacts still referenced elsewhere, and expired workspaces with an in-flight run until that run reaches a terminal state.
- Ending a demo revokes a copied cookie and remains available after ordinary request allowance exhaustion.
- Startup honors cloud port/host while enforcing one worker. Invalid ports and malformed private tokens are rejected.

## Real HTTP verification

scripts/smoke_http.py starts a temporary Uvicorn process with an isolated database. It verifies health/static assets, an approved private research run, the new diagnostic and approved correction, comparison, report labels, and private history. It then creates an independent cookie demo, checks isolated history, executes diagnostic/correction runs and ends the session. It cleans up temporary data without printing credentials.

Observed summary: http_smoke=passed, normal_run=COMPLETED, comparison=METHODOLOGY_CORRECTION, parent_preserved=true, anonymous_demo=passed, changed_signals=14.

The local sandbox does not permit listening sockets. The real HTTP smoke and browser-preview server ran with explicit local-network execution permission. The in-process regression ran in the sandbox.

## Browser verification

The in-app browser completed these steps against an isolated localhost synthetic workspace:

1. Open the landing page and enter via Try the live demo, without a private token.
2. Review and run the new invalid diagnostic, observing Blocked and synthetic labels.
3. Inspect source row and actual decision, entry and input-availability timestamps.
4. Approve the correction and observe the recalculated comparison.
5. Inspect 14 changed entry signals and the original/new entry actions.
6. Reload, resume the cookie session and reopen the saved child and comparison from history.

The viewport was approximately 440 pixels wide. Cards stacked and the wide decision table scrolled inside its container. [Changed-decision screenshot](screenshots/changed-decisions.png) records the result. This is local browser QA, not an independent usability measurement or cloud HTTPS acceptance. Earlier workspace verification is documented in WORKSPACE.md; its earlier download/desktop checks were not all repeated for this revision.

## Re-run

From the Git repository root, using the pinned environment:

```sh
python -m pytest -q --cov=backend --cov-branch --cov-fail-under=90
python -m ruff check backend scripts tests
python -m ruff format --check backend scripts tests
python scripts/smoke_http.py
node --check frontend/assets/app.js
node --test frontend/tests/view-model.test.js
npm ci --prefix frontend
npm run format:check --prefix frontend
```

CI is configured for Windows/Linux and Python 3.11/3.12. Local results do not establish remote jobs have passed. Render's runtime, disk and external-device flow must still pass the gate in DEPLOYMENT.md after deployment.

## Remaining limits

Tests do not establish real exchange-calendar correctness, adjusted historical prices, liquidity, multi-asset portfolios, model-provider behavior, distributed execution, public production identity or profitability. There is no hard CPU kill timeout, resumable durable queue or distributed rate limiter. Fixed-window limits constrain small synthetic sessions; platform abuse protection is still required. Artifact hashes are not signatures against an administrator changing the database. Some defensive/error branches remain outside measured coverage.
