# Backend Foundation: Implementation and Usage

Version 0.1.0 | October 24, 2026

This is the implemented subset of the target architecture. All market data is synthetic. Default template mode calls no external service. An opt-in Claude planner is implemented; real-provider validation remains pending credentials, and no market-data service is integrated.

## Implemented modules

| Module | Responsibility |
| --- | --- |
| models.py | Strict, frozen Pydantic contracts, bounded finite Decimal inputs, schema version 1 |
| canonical.py | Stable JSON representation and SHA-256 hashing; Decimal precision preserved as strings |
| data.py | Allowlisted, byte-pinned fixture catalog and strict CSV validation |
| engine.py | Feature dependencies, decisions, deterministic fills, cost deductions, NAV and metrics |
| audit.py | Independent A01 timing and A03 integrity evaluation; A02 cost coverage; explicit A04-A06 unknowns |
| store.py | SQLite transactions, plan revisions, exact-hash approvals, run events, immutable artifacts and idempotency |
| service.py | Template planning, orchestration, reports, allowed corrections and comparison classification |
| api.py | Private token / anonymous-cookie resolution, same-origin mutation checks, bounded bodies and safe errors |
| demo.py | Hashed anonymous sessions, persistent request allowances, expiry and scoped cleanup |
| config.py | Explicit local/cloud startup and bounded demo policy |
| planner.py | Optional schema-bound Claude parameter proposals and persistent call allowances |
| reporting.py | Full deterministic research and comparison Markdown exports |
| evaluation.py | Independent seeded synthetic controls and per-rule detection counts |

The planner, runner, auditor, correction planner, and report writer are bounded logical roles. There is no autonomous model loop or generated code execution.

## Deliberate differences from the target

- Execution is synchronous and serialized within one process. Run creation returns HTTP 201 and a saved lifecycle state, not HTTP 202 with a durable worker queue.
- Scientific artifacts are committed atomically inside SQLite instead of separate content-addressed files. Partial numerical outputs are not published. Interrupted runs become FAILED with WORKER_INTERRUPTED at startup; they are not resumed automatically.
- Cancellation works only while QUEUED. In-flight synchronous cancellation returns a conflict rather than pretending to cancel.
- Local development uses configured bearer-token-to-workspace mappings. The environment-based startup maps one private token to the local workspace. Opt-in anonymous cookie sessions now support isolated synthetic demos. User administration and production account integration are not included.
- The synthetic UTC calendar consists of the explicitly listed CSV sessions. It is not a real exchange calendar and must not be used to claim historical correctness.
- Availability is derived from the fixture's declared UTC publication policy. Inputs must be strictly earlier than decisions. Equal-boundary events without finer ordering are rejected conservatively.
- The source tree hash and dependency-lock hash provide implementation fingerprints; a Git commit can be supplied by the surrounding checkout. Artifacts do not yet contain a separately injected Git commit identifier.
- There is a 64 KiB request body bound, 5 MiB dataset bound, 10,000-row bound, parameter precision/range checks, and no arbitrary uploads. Opt-in public demos add persistent per-session request/run/plan/correction quotas and bounded session issuance. Hard worker CPU/time isolation and a durable job system remain future work; use the deployment guide and platform abuse protection for Internet exposure.
- Reports are deterministic Markdown. A buildless frontend is now served by the same backend; see [Workspace usage](WORKSPACE.md). Optional natural-language planning is implemented with the limits in PLANNING.md; no live-provider validation, historical data, PDF report, award-platform integration, or agent memory is claimed.

## Numerical contract

All arithmetic runs inside a local Decimal context with precision 34. Input prices and starting NAV are positive, bounded to 1e12, with at most 12 decimal places. Allocation is in (0,1]. Fee/slippage inputs are nonnegative, bounded, and explicit. NAV above 1e24 or nonpositive NAV terminates with MODEL_DOMAIN_ERROR.

The selected sample constrains simulated entry/exit sessions. Earlier observations may supply warmup. Five-session returns require close(t) and close(t-5), not merely five price observations.

Gross trade return is exit close / entry open - 1. Fees and slippage are deducted as return fractions against entry notional. They do not also shift fill prices. The default round-trip deduction is 0.002, using 5 bps commission and 5 bps slippage on each side. Fixed allocation scales the resulting session return. No-position sessions retain NAV.

Turnover is total modeled entry-plus-exit notional divided by initial NAV. Sharpe is N/A. Drawdown includes the initial NAV peak. Maximum drawdown is reported as a nonpositive decimal fraction.

Prices, costs, returns, and metrics serialize as decimal strings. Counts serialize as integers. A missing metric is null, never an invented zero.

## Local API walkthrough

First start the server as described in the README, with a private QUANTFORGE_API_TOKEN in the same PowerShell session. The example below assumes that server is running and that the client session has the same token.

```powershell
$base = 'http://127.0.0.1:8000'
$headers = @{ Authorization = "Bearer $env:QUANTFORGE_API_TOKEN" }
$plan = Invoke-RestMethod "$base/api/research/plans" -Method Post -Headers $headers -ContentType 'application/json' -Body '{}'
$approval = @{ revision = $plan.revision; spec_hash = $plan.spec_hash }
$null = Invoke-RestMethod "$base/api/research/plans/$($plan.plan_id)/approve" -Method Post -Headers $headers -ContentType 'application/json' -Body ($approval | ConvertTo-Json)
$runHeaders = @{ Authorization = $headers.Authorization; 'Idempotency-Key' = [guid]::NewGuid().ToString() }
$request = @{ plan_id = $plan.plan_id; revision = $plan.revision; spec_hash = $plan.spec_hash }
$run = Invoke-RestMethod "$base/api/research/runs" -Method Post -Headers $runHeaders -ContentType 'application/json' -Body ($request | ConvertTo-Json)
$artifact = Invoke-RestMethod "$base/api/runs/$($run.run_id)/artifact" -Headers $headers
$artifact.admissibility
$artifact.result.metrics
```

For the intentionally flawed example, POST an empty object to /api/demo/diagnostic-runs with an Idempotency-Key. Then POST kind=timing to /api/runs/{run_id}/corrections. Inspect its rationale and diff. Only after review, POST its exact proposal_hash to /api/corrections/{correction_id}/approve-and-rerun with an idempotency key.

A costs correction accepts fee_bps_each_side and slippage_bps_each_side. It creates a separate recomputed run. No metric is edited in place.

The automated real-HTTP example is scripts/smoke_http.py. It generates an ephemeral token, validates the full workflow, and terminates its temporary server without printing the credential.

## Persistence and failure interpretation

Plan edits increment revisions and invalidate approval. Each run captures a specification snapshot. A stale approval cannot start a new run. Retries with the same action, workspace, idempotency key, and request return the same run; a changed request with that key conflicts. A correction can produce at most one child even if approved again using a new key.

Each state change appends a sequence-numbered event in the same transaction. COMPLETED requires a stored hash-checked artifact. A completed invalid-data experiment contains audit evidence and no numerical result. Operational failures are FAILED and have no fabricated completed artifact. Failure of a child cannot replace its parent.

All artifact reads, comparisons, corrections, and approvals verify workspace ownership. Unknown and inaccessible identifiers both return NOT_FOUND. Secrets and raw validation input are not echoed in error responses.

Application-enforced immutability does not protect against a machine administrator changing the SQLite database. Content hashes detect accidental or direct artifact-content alteration against its saved hash; they are not digital signatures or third-party attestation.

## Reproducibility

Scientific outputs include frozen strategy data, dataset byte hash, normalized-data hash, source-tree fingerprint, dependency-lock fingerprint, Python/Pydantic versions, engine/rule/schema versions, decisions, results, and findings. Scientific hashes omit UUIDs and wall-clock timestamps. Three identical runs are tested for exact artifact equality.

Reproducibility is scoped to pinned inputs and implementation environment. Cross-platform CI is configured, but local results do not prove every OS/runtime combination. A future historical adapter needs a real calendar, corporate-action policy, licensed data provenance, and new fixtures before being accepted.

## Public demo and cloud delivery

See [Deployment](DEPLOYMENT.md) for HTTPS cookie configuration, persistent-disk setup, per-session allowances, retention and external verification. `python -m backend` honors `PORT` and `QUANTFORGE_HOST`; its default remains loopback unless a cloud port is supplied. It always starts one worker. The default guided diagnostic uses `timing_trap`; `leaky_next_close` remains explicitly supported with unchanged data. Comparisons now include computed changed-entry decisions when scientific configurations are comparable.

## Review and export enhancements

Cost sensitivity defaults now differ from current assumptions; unchanged, zero-total or invalid-precision inputs are blocked before a request. API validation errors expose only allowlisted field names, never raw input. New research reports include exact parameters, units, provenance, a bounded ledger, source evidence and reproducibility fingerprints. Comparison exports include both saved results and changed decisions. Report evidence/ledger tables disclose truncation beyond 100 records and refer to the complete scientific JSON. Previously saved reports remain immutable.

Planning provenance uses new plan_context/run_context tables with foreign-key cascades; existing plans/runs without context are explicitly marked LEGACY_TEMPLATE on read. No existing scientific artifact is rewritten. Planner attempt records are reserved in SQLite and are separate from numerical experiment state.
