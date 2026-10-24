# Contracts and Delivery Plan

Design version: 0.1 | October 24, 2026 | Status: target contracts; foundation partially implemented

Implementation note: [Implementation status](IMPLEMENTATION.md) documents actual endpoint behavior. Run execution currently returns synchronously with HTTP 201 rather than using a durable asynchronous queue with HTTP 202.

This document defines the handoff between frontend, backend, numerical engine, and agent roles. It accompanies [Architecture](ARCHITECTURE.md). Tables describe contracts; they are not implemented API or schema code.

## 1. Shared conventions

- Use opaque server-generated identifiers and timezone-aware UTC timestamps.
- Distinguish an exchange session date from an event timestamp.
- Use explicit units: threshold_pct is percent; fee/slippage fields are basis points per side; metric returns are decimal fractions.
- Use named schema versions. Reject unsupported versions and unknown executable fields.
- Store canonical specification and dataset hashes with every run.
- Resolve identity from server-side session context, never a client-supplied user ID.
- Distinguish operational state, research admissibility, audit coverage, and artifact availability.
- Empty, zero, and unavailable are different values.
- Preserve provenance for derived values and field defaults.

## 2. Core entities

### DatasetManifest

| Field | Meaning |
| --- | --- |
| dataset_id, version, schema_version | Immutable dataset identity |
| source, source_reference, license, redistribution_allowed | Provenance and usage rights |
| kind | SYNTHETIC or HISTORICAL |
| created_at, retrieved_at, as_of | Creation/retrieval and known coverage dates |
| symbols, currency, timezone, exchange_calendar | Supported market context |
| adjustment_policy, corporate_action_policy | Consistent OHLC basis and modeled exclusions |
| start_session, end_session, row_count | Coverage |
| byte_hash, normalized_hash, normalization_version | Reproducibility |
| availability_policy | How raw fields receive availability timestamps |
| limitations, generator_version, seed | Declared constraints and synthetic generation provenance |

The dataset adapter must resolve a manifest plus immutable rows. A user-provided label such as "clean" is not an integrity certificate.

### PlanRevision and StrategySpec

PlanRevision records hypothesis text, strategy revision, assumption sources, questions, validation output, and approval binding.

| Strategy field | MVP meaning |
| --- | --- |
| schema_version, strategy_type | Version and trailing_momentum strategy family |
| dataset_id, dataset_version, dataset_hash | Pinned data |
| symbol, sample_start, sample_end | One supported symbol and sample |
| lookback_sessions | Positive integer; five by default |
| threshold_pct, comparator | Default 2.0 and strict greater-than |
| feature_definition_id | Registered feature; no arbitrary expression or source code |
| decision_policy | After session-t close availability |
| entry_policy, exit_policy | Next-session open and that session's close |
| initial_nav, currency | Default 10,000; must match dataset |
| allocation_fraction | Fixed fraction in (0, 1], default 1 |
| fee_bps_each_side, slippage_bps_each_side | Nonnegative, explicit; default proposal 5 and 5 |
| cost_model_version | simple_return_deduction_v1 |
| missing_data_policy, calendar_policy | Registered, bounded policies |
| assumptions, provenance | Visible limitations and per-field source |

Default costs are illustrative research settings, not estimates of a particular broker or market. Show them for review.

Sample selection constrains trade entry/exit sessions. The engine may read earlier rows solely for feature warmup and records them in lineage. It may not enter or exit outside the selected sample. Missing pre-sample warmup produces disclosed skips.

### ResearchRun

Contains run_id, workspace_id, plan_revision_id, parent_run_id, correction_id, specification snapshot/hash, data references/hashes, execution_mode, execution versions, state, admissibility, active_stage, timestamps, attempt/lease metadata, error code, and artifact manifest.

User approval captures actor, timestamp, approved revision/hash, and correction ID where relevant. Runs are immutable in research content; lifecycle fields advance through controlled transitions.

### FeatureDependency and DecisionRecord

FeatureDependency includes dependency_id, feature_id, source row/field references, transformation/version, source availability timestamps, maximum availability, and diagnostic future-reference flag.

DecisionRecord includes decision_id, session, decision timestamp/event order, dependencies, feature value, threshold, comparison outcome, proposed order reference, or skip reason.

Record false and skipped signals as well as true signals.

### Order, Fill, and Trade

Order records decision ID, submission time, intended session/policy, side, allocation, and status.

Fill records order ID, execution timestamp/event order, source price/row, modeled notional, and explicit execution assumptions.

Trade records linked entry/exit fills, gross return, each fee/slippage component, total cost fraction, net return, portfolio contribution, and skip/rejection reason if no completed trade exists. Do not confuse a decision count with a trade count.

### BacktestResult

Contains result_id, run_id, session return series, NAV series including initial NAV, metrics with units and availability reasons, trades, skips, input/output counts, assumptions, data coverage, and content hash.

Metric provenance identifies the result artifact and calculation version. Metrics are not editable report fields.

### AuditFinding

| Field | Meaning |
| --- | --- |
| finding_id, run_id, check_id, rule_version | Stable finding and rule identity |
| status, severity, execution_effect | Separate verdict, priority, and gate behavior |
| scope | What was actually checked |
| evidence_refs | Row, field, decision, order, fill, or manifest references |
| observed, expected | Machine-readable comparison where applicable |
| explanation | Factual explanation or deterministic fallback |
| suggested_action | Allowed correction or data remediation |
| requires_rerun, limitations | Next action and coverage boundary |

AuditSummary includes counts by status, mandatory-rule completion, blocked/unverified reasons, and rule versions. It never reduces the result to an invented confidence percentage.

### CorrectionProposal and Comparison

CorrectionProposal includes correction_id, parent_run_id, finding_ids, base_spec_hash, field patches, rationale, impact on economic meaning, comparison classification, remaining limitations, approval status, and child_run_id.

Comparison includes both run IDs, classification, dataset/sample/engine differences, metrics from both artifacts, metric deltas where meaningful, audit changes, spec diff, and alignment disclosure.

### Report and RunEvent

Report includes artifact/version, run references, deterministic metric sections, finding references, generated narrative provenance, limitations, and generation status.

RunEvent includes event_id, run_id, monotonic sequence, stage, event type, safe payload, and timestamp. Client polling can request events after a known sequence without duplicate display.

## 3. Bounded tool registry

Tools are server functions with validated arguments. Names below are proposed conceptual contracts.

| Tool | Inputs | Outputs | Allowed caller |
| --- | --- | --- | --- |
| parse_hypothesis | Bounded text, catalog, manifest summary | Candidate plan and assumption sources | Planner |
| validate_spec | Candidate spec, supported versions | Field and semantic errors | Coordinator |
| get_dataset_manifest | Authorized dataset reference | Manifest summary | Coordinator/Planner |
| load_market_data | Authorized immutable dataset reference | Internal frame handle and validation report | Runner only |
| run_backtest | Approved run ID | Persisted result/evidence references | Coordinator only |
| run_audit | Run ID and stored stage artifacts | Persisted findings and coverage | Coordinator only |
| propose_fix | Run ID and finding IDs | Validated correction proposal | Correction Planner |
| approve_correction | Proposal revision/hash | Approval record | User action through API only |
| rerun | Approved correction ID and idempotency key | Child run reference | Coordinator only |
| build_report | Saved result/finding references | Report reference | Coordinator |
| retrieve_memory | Workspace, bounded research context | Provenance-linked suggestions | Planner, P1 |
| save_research | Authorized artifact manifest | Persistence confirmation | Coordinator |

No tool accepts arbitrary Python, SQL, shell commands, filesystem paths, or external URLs supplied by the model. Model tool calls are proposals validated by the coordinator, not direct service authority.

## 4. API surface

All mutations require ownership checks and bounded input. Queueing mutations require idempotency keys.

| Method and route | Purpose | Response |
| --- | --- | --- |
| GET /api/datasets | List available authorized datasets | Manifest summaries |
| POST /api/research/plans | Create template or language-based plan | Plan revision, questions, validation, assumptions |
| PATCH /api/research/plans/{plan_id} | Save an edited revision | New revision; old approval invalidated |
| POST /api/research/plans/{plan_id}/approve | Approve exact revision and spec hash | Approval record |
| POST /api/research/runs | Queue approved plan revision | 202 with run_id and QUEUED |
| GET /api/runs/{run_id} | Poll lifecycle and available artifacts | State, admissibility, stage, safe errors |
| GET /api/runs/{run_id}/events?after={sequence} | Incremental progress | Ordered safe events |
| GET /api/runs/{run_id}/result | Retrieve saved engine result | Result or explicit not-ready status |
| GET /api/runs/{run_id}/audit | Retrieve findings and coverage | Findings, versions, summary |
| POST /api/runs/{run_id}/corrections | Propose selected corrections | Proposal and diff; no execution |
| POST /api/corrections/{correction_id}/approve-and-rerun | Approve exact proposal and queue child | Approval and child run reference |
| GET /api/runs/{run_id}/comparison?other_run_id={id} | Compare two authorized runs | Comparison classification and saved values |
| GET /api/runs/{run_id}/report | Read saved report | Report/status; download later |
| POST /api/runs/{run_id}/cancel | Request safe cancellation | Current state and cancellation outcome |
| POST /api/demo/diagnostic-runs | Run an allowlisted synthetic demonstration | Permanently invalid diagnostic run reference |

The diagnostic endpoint ignores/rejects client execution-mode overrides and accepts only fixed server-approved fixture identifiers. It does not accept uploads.

A blocked research result is domain information, not a server crash. A queued job may complete with BLOCKED admissibility and a structured audit report. No result endpoint fabricates metrics when simulation never ran.

## 5. Errors and recovery

Error envelopes include code, safe message, stage, retryable flag, correlation ID, and optional field/evidence references. Internal stack traces stay server-side.

| Code | Meaning | Recovery |
| --- | --- | --- |
| INVALID_SPEC | Schema or semantic violation | Edit specified fields |
| UNSUPPORTED_STRATEGY | Request exceeds supported catalog | Choose supported template |
| PLAN_NEEDS_INPUT | Material ambiguity remains | Answer plan questions |
| STALE_APPROVAL | Revision/hash no longer matches | Review and approve latest version |
| DATASET_INVALID | Required integrity check failed | Inspect row evidence; select valid snapshot |
| DATASET_UNAVAILABLE | Authorized pinned data cannot be loaded | Retry only if transient; never substitute |
| TIMING_VIOLATION | Future/unavailable input affected a decision | Inspect A01 and propose correction |
| MODEL_UNAVAILABLE | Planning/explanation request failed | Template or deterministic explanation |
| EXECUTION_TIMEOUT | Stage exceeded budget | Preserve failure; bounded retry if appropriate |
| MODEL_DOMAIN_ERROR | Numerical assumptions yield unsupported state | Review assumptions and model limits |
| ARTIFACT_WRITE_FAILED | Required persistence failed | Do not claim completion |
| AUDIT_EVIDENCE_MISSING | Mandatory evidence absent | Mark Unverified; investigate/recompute |
| RUN_NOT_READY | Requested artifact not committed yet | Poll lifecycle |
| IDEMPOTENCY_CONFLICT | Same key reused with different content | Use original request or a new key |
| RESOURCE_LIMIT | Row/size/concurrency budget exceeded | Reduce request or wait |
| NOT_FOUND | Missing or inaccessible resource | Do not reveal another workspace's existence |

A retry with the same idempotency key and same request returns the existing run. A same-key/different-request mutation is rejected. Automatic retries do not create additional children.

If narrative generation fails, the required deterministic report remains available and records narrative fallback. If persistence or a mandatory audit fails, completion must not be advertised.

## 6. Evaluation fixtures and expected outcomes

These are acceptance specifications to implement later, not tests already passing.

### Independently hand-checkable ledger case

Use starting NAV 10,000, allocation 1, entry open 100, exit close 102, fee 5 bps per side, and slippage 5 bps per side.

Gross return = 2%. Round-trip cost = 20 bps = 0.2%. Net return = 1.8%. Ending NAV = 10,180.

Append a second executed trade with open 100 and close 99 under the same costs: net return = -1.2%; NAV = 10,057.84. Running peak is 10,180, so maximum drawdown is -1.2%. Total return is 0.5784%. This verifies compounding rather than simply adding trade returns.

A separate signal fixture must establish which sessions trigger those trades; the ledger example alone is not an end-to-end momentum fixture.

### Fixture matrix

| Case | Expected behavior |
| --- | --- |
| clean_momentum | Valid dependencies, genuine computed trades, A01 PASS |
| leaky_next_close | A01 FAIL; normal path blocks; diagnostic path computes but stays invalid |
| decision_before_availability | A01 FAIL even if input became available before fill |
| equal_boundary_without_order | Reject ambiguous timing until event ordering is specified |
| valid_after_close_ordering | Close publication before decision and next-open fill passes |
| missing_open | A03 FAIL, no fake fill/result |
| duplicate_sessions | A03 FAIL with original row references |
| invalid_ohlc / negative_volume / nonfinite_price | A03 FAIL |
| zero_cost_trades | A02 WARN; actual nonzero-cost child required for comparison |
| zero_cost_no_trades | A02 NOT_APPLICABLE with reason; no implied profitability |
| five_session_warmup | close(t)/close(t-5)-1 uses six close observations |
| threshold_exactly_two_percent | No trade under strict greater-than semantics |
| weekend_or_holiday | Next trading session, not next calendar day |
| final_session_signal | No unavailable next-session fill |
| suspended_session | Skip according to disclosed tradability policy |
| flat_no_signal | NAV constant; zero trades; unsupported statistics N/A |
| correction_failure | Parent unchanged; child error visible |
| changed_dataset_comparison | NOT_DIRECTLY_COMPARABLE and explicit differences |

Use at least two valid timing cases and two invalid cases to measure false positives as well as detection.

### Model and workflow evaluation

Use ten fixed hypotheses covering clear requests, missing parameters, ambiguous timing, unsupported leverage/shorting, arbitrary-code requests, and prompt injection. Expected outcomes are valid bounded plans or explicit questions/refusals, never silently broadened strategy scope.

Verify that generated summaries cannot replace rule verdicts or numeric artifacts. Test a provider timeout and invalid structured output; both must leave the template workflow usable.

### Reproducibility and security

- Repeat a pinned run three times; compare canonical trade, NAV, metric, and audit artifacts.
- Record the spec, data, engine, rule, calendar, and dependency versions used.
- Attempt cross-workspace reads, comparisons, corrections, and artifact access.
- Attempt diagnostic-mode escalation through a normal run request.
- Repeat approve-and-rerun requests; exactly one child should be queued per idempotency key.
- Simulate worker interruption before and after artifact commit.
- Confirm secrets and internal stack traces are absent from user errors and reports.
- Verify synthetic/diagnostic labels survive every view and report.

### Product acceptance

A new visitor can select a template, review assumptions, run it, inspect an actual timing failure in the diagnostic example, approve a correction, and explain the difference between the original and corrected methodology.

The three-minute time-to-result and five-minute onboarding ideas from the whitepaper remain targets until measured. Record observed timings rather than announcing targets as achievements.

## 7. Two-person work split

Assignment by role is proposed; it does not assume either teammate's expertise.

| Track A: Agent and Quant Backend | Track B: Product and Frontend |
| --- | --- |
| Freeze validated entities and units | Review the same contracts and plan fields |
| Build synthetic datasets and manifests | Build five workspace views and navigation |
| Implement data checks and temporal lineage | Build timeline, assumption editor, and provenance labels |
| Implement deterministic ledger and metrics | Render engine charts, tables, and unavailable states |
| Implement A01-A03 and evidence artifacts | Build audit evidence cards and correction diff review |
| Implement run state, persistence, and idempotency | Integrate polling, retries, failures, and child comparison |
| Add optional model adapter after core pipeline | Deployment and end-to-end demonstration flow |

Both review the golden numerical case, definition of completion, and invalid-demo isolation before integration.

Use small task branches and pull requests. Freeze contract changes through review; update both documents and acceptance cases together when units or semantics change.

## 8. Implementation order and exit gates

1. **Contract freeze:** agree on the proposed assumptions, entity names, units, time ordering, and acceptance examples.
2. **Deterministic vertical slice:** fixture -> spec validation -> feature lineage -> trades -> NAV -> saved run. Exit only after hand calculation and three-run replay agree.
3. **Audit and correction:** A01-A03, isolated diagnostic fixture, user-approved child, immutable comparison. Exit only after leaky and valid controls behave correctly.
4. **Web integration:** plan review, lifecycle, results, findings, rerun, and comparison. Exit only after a fresh browser session completes the flow.
5. **Optional language layer:** structured planning, bounded repair, deterministic fallback, evidence-based narrative.
6. **Optional persistence/auth/memory enhancement:** add only after the core slice works; prove ownership isolation and memory's effect.
7. **Release documentation:** actual setup commands, actual tests, real deployment link, data rights, integration evidence, limitations, and tool disclosures.

If time is constrained, defer model planning, login, memory, PDF export, and sponsor integrations before weakening numerical or audit correctness.

## 9. Remaining decisions

| Decision | Proposed baseline | When to settle |
| --- | --- | --- |
| Initial dataset | Versioned synthetic one-symbol fixtures | Before engine implementation |
| Exchange/calendar | One explicit calendar/timezone; synthetic metadata must be coherent | Before timestamp fixtures |
| Plan defaults | Five sessions, 2%, NAV 10,000, allocation 1, fees/slippage 5 bps each side | Before schema freeze |
| Provider/model | Provider-independent adapter; Claude candidate | Before optional language integration |
| Chart library and deployment | Select after first vertical slice | Before frontend integration |
| Public repository release | Keep current private visibility until explicit release decision | Before external submission |
| Software and dataset licenses | Select separately; no inferred permission | Before publication |
| Optional sponsor tooling | Require working integration evidence | After P0 exit gates |

These planning documents describe the target. The backend foundation is now implemented in this repository; deployment and optional provider integrations remain future work.
