# QuantForge

**Don't just generate a backtest. Challenge it.**

QuantForge is an AI quantitative research project that turns a constrained investment hypothesis into a reproducible backtest, checks its methodology against machine-verifiable evidence, and helps researchers compare an original experiment with an explicitly approved correction.

The primary user is a student researcher who can describe a simple strategy but needs help finding methodological mistakes. Independent researchers and small research teams are secondary users.

> **Status: integrated workspace and bounded public-demo mode implemented; cloud deployment pending verification.** The browser workflow includes template planning, review, backtesting, timing evidence, correction approval, changed-decision comparisons, report downloads and history. Opt-in anonymous sessions isolate visitors, enforce persistent quotas and resume after a page reload. A Render Blueprint prepares a single-instance service with a persistent disk. Optional Claude structured planning is implemented behind explicit configuration, with template fallback; real-provider validation remains pending credentials. Historical data, durable jobs, production accounts and memory remain future work. See [Workspace usage and verification](docs/WORKSPACE.md), [Implementation status](docs/IMPLEMENTATION.md), and [Test report](docs/TEST_REPORT.md).

## Why this project exists

A convincing equity curve can come from future information, missing transaction costs, or unrealistic execution assumptions. Generating more strategy code does not establish that an experiment is valid.

QuantForge is designed around inspectable evidence: what information a decision used, when that information became available, when a simulated order filled, which assumptions changed, and whether the corrected experiment was actually recomputed.

## Research workflow

1. **Describe a hypothesis** or select a supported strategy template.
2. **Review the plan:** dataset, symbol, sample dates, signal, execution timing, allocation, costs, and explicit defaults.
3. **Run the experiment** with a deterministic Python engine.
4. **Inspect the audit:** individual checks, evidence, severity, and limitations.
5. **Review a proposed correction** and approve a new experiment.
6. **Compare and preserve both runs**, including their specifications, data versions, metrics, and audit findings.

A failed check does not disappear when a report is generated. An unavailable check is marked **Unverified**, rather than passed.

## MVP scope

The initial scope is deliberately constrained:

- One symbol and one currency per experiment.
- Daily OHLCV data from versioned, explicitly labeled synthetic fixtures or appropriately licensed historical datasets.
- Long-only trailing-momentum signals.
- A decision after session t closes, entry at the next trading session's open, and exit at that session's close.
- Fixed allocation, proportional fees, and a disclosed simplified slippage model.
- Deterministic data-integrity, information-timing, and missing-cost checks.
- Immutable original and corrected runs, specification diffs, and comparison.
- A web workspace with a template-first path that remains usable without an LLM.

Optional natural-language planning is implemented; see [Planner setup and limits](docs/PLANNING.md). Account-based saved workspaces and cross-run agent memory remain later enhancements. Full Markdown research/comparison reports and scientific-JSON downloads are implemented. They are not prerequisites for validating the core pipeline.

### Example research question

> If the trailing five-session close-to-close return exceeds 2% after today's close, buy at the next session's open and sell at that session's close.

The five-session return is close(t) / close(t-5) - 1. The threshold comparison is strictly greater than 2%. The next session is determined by the selected trading calendar, not by adding one calendar day.

All example parameters are research assumptions, not investment recommendations.

## Planned agent architecture

QuantForge uses bounded specialist roles coordinated by a deterministic state machine. These roles do not require separate models or autonomous processes.

| Component | Responsibility | Authority boundary |
| --- | --- | --- |
| Research Orchestrator | Enforce workflow state, ownership, budgets, and tool permissions | Owns transitions; does not invent research content |
| Planner | Translate a supported hypothesis into a proposed StrategySpec | Cannot approve its own plan or calculate performance |
| Runner | Request approved data, validation, and engine tools | Deterministic service; no arbitrary generated code |
| Auditor | Execute deterministic rules and explain their evidence | Rule code owns findings; model commentary cannot change verdicts |
| Correction Planner | Propose a minimal, evidence-linked specification change | Cannot overwrite a run or silently approve a rerun |
| Report Writer | Explain saved results and limitations | All numeric claims must reference engine artifacts |
| Memory Adapter (later) | Retrieve relevant, user-confirmed preferences and prior findings | Context only; cannot override the current plan |

The engine calculates all metrics. The audit rule engine establishes machine-verifiable findings. When explicitly configured, Claude proposes bounded parameters for user review; deterministic code writes the reports. No model can approve a plan, calculate a result or change a rule verdict.

See [Architecture](docs/ARCHITECTURE.md) for agent contracts, workflow, numerical semantics, audit evidence, and failure behavior.

## Planned audit coverage

| Check | MVP behavior | Evidence |
| --- | --- | --- |
| A01: Information timing | Block a normal run if inputs were unavailable at the decision or execution boundary | Feature lineage, source rows, availability timestamps, decision and fill events |
| A02: Missing or zero costs | Warn and offer a clearly labeled cost-sensitivity experiment | Cost configuration, actual trade count, separately computed comparison |
| A03: Dataset integrity | Block invalid datasets before simulation | Missing columns, duplicate keys, offending rows, OHLC constraints |
| A04: Split leakage | Later: check recorded split boundaries and parameter provenance | Training/test intervals and selection history |
| A05: Overfitting risk | Later: flag insufficient holdout discipline | Trial history and holdout usage; never proof from one backtest |
| A06: Survivorship bias | Unverified until adequate historical universe metadata exists | Universe provenance and delisting coverage |

A passed rule means that its specified checks passed for the recorded inputs. It does not certify profitability, generalizability, or freedom from all bias.

## Demonstration design

The demonstration will use the same engine to compute a clean experiment and an explicitly labeled **synthetic, intentionally flawed diagnostic experiment**. The diagnostic fixture uses future close information before a simulated entry.

Normal research execution must reject such timing violations. A separate server-controlled diagnostic path may compute the flawed experiment solely to demonstrate the audit. It must remain visibly invalid and must not be presented as an admissible strategy.

Corrections create new runs. Before/after values must come from actual execution; the project will not hard-code impressive performance changes.

## Proposed technology choices

- **Frontend:** buildless HTML/CSS/JavaScript modules and SVG charts are implemented. The earlier Next.js/TypeScript/Tailwind proposal remains an optional future migration, not a current dependency.
- **Backend:** FastAPI and Pydantic.
- **Numerical engine:** Python Decimal and a small explicit execution model. pandas and NumPy are deferred; the foundation requires neither.
- **Planner:** optional bounded Claude Messages API with JSON structured outputs, local validation, persisted call allowances and an explicit template fallback.
- **Persistence:** SQLite for the first implementation; a production database can follow.
- **Evaluation:** deterministic fixtures, hand-checked calculations, pytest, and an end-to-end browser smoke test.

The backend uses pinned FastAPI, Pydantic, Uvicorn, SQLite, and Decimal dependencies. Provider and production identity choices remain proposals. The bounded demo uses cookie sessions and includes a Render deployment configuration. Exact tested packages are recorded in requirements.lock.

## Repository guide

Current planning documents:

- [Architecture](docs/ARCHITECTURE.md): system boundaries, specialist roles, state transitions, financial semantics, and audits.
- [Contracts and delivery plan](docs/CONTRACTS_AND_DELIVERY.md): data entities, tool/API contracts, errors, acceptance cases, and two-person work split.

Proposed implementation layout:

| Path | Intended contents |
| --- | --- |
| frontend/ | Research, plan review, results, audit, and comparison views |
| backend/api/ | Authorized research endpoints and request validation |
| backend/agent/ | Orchestration, prompts, model adapter, and tool registry |
| backend/quant/ | Data validation, feature lineage, fills, ledger, and metrics |
| backend/auditor/ | Versioned deterministic audit rules |
| backend/models/ | Shared validated contracts |
| fixtures/ | Labeled synthetic or redistributable datasets and manifests |
| tests/ | Golden calculations, audit cases, security and workflow checks |
| docs/ | Product and engineering design |

The initial implementation uses backend/models.py, data.py, engine.py, audit.py, store.py, service.py, and api.py to keep the foundation navigable. The directory layout above remains the longer-term modularization target.

## Setup and verification

Requires Python 3.11 or 3.12. From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
$env:QUANTFORGE_API_TOKEN = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(40))"
.\.venv\Scripts\python.exe -m backend
```

The service binds to 127.0.0.1:8000. Open the [research workspace](http://127.0.0.1:8000/) and connect using your private token, or use the [API documentation](http://127.0.0.1:8000/docs). Protected endpoints require Authorization: Bearer followed by your private token. The database defaults to .quantforge/research.sqlite3; QUANTFORGE_DATA_DIR changes its location. Use exactly one worker. This shared-secret setup is local development authentication, not a production account system.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --cov=backend --cov-branch
.\.venv\Scripts\python.exe -m ruff check backend scripts tests
.\.venv\Scripts\python.exe -m ruff format --check backend scripts tests
.\.venv\Scripts\python.exe scripts/smoke_http.py
```

On Linux/macOS use .venv/bin/python and your shell's environment-variable syntax. The real HTTP smoke script starts and stops a temporary loopback server. Windows test clients also need permission to create local sockets.

[Implementation notes](docs/IMPLEMENTATION.md) provide the full request sequence, numerical assumptions, and known limits. The current API executes synchronously and returns HTTP 201 with the saved run state. A completed workflow can still have BLOCKED admissibility.

Before a release is described as usable, it must demonstrate:

- The same pinned inputs produce identical trades and metrics across three executions.
- At least one numerical case matches an independent hand calculation.
- Known timing leaks are detected with concrete evidence, while valid controls avoid false high-severity findings.
- Invalid data produces a controlled failure rather than fabricated fills.
- Corrections preserve the original run and recompute the new result.
- A visitor can complete the supported workflow on the deployed application.

## Public demo and deployment

Local anonymous preview on macOS/Linux, after installing the Python dependencies:

```sh
export QUANTFORGE_PUBLIC_DEMO=true
export QUANTFORGE_COOKIE_SECURE=false
python -m backend
```

Open http://127.0.0.1:8000/ and choose **Try the live demo**. The environment must not contain a malformed private token. Each visitor receives an isolated two-hour session with up to 12 runs; no shared secret is embedded in the frontend. Existing private bearer-token access remains available. The demo supports six synthetic fixtures, three implemented audit checks, and explicit Unverified coverage for the other three.

The guided `timing_trap` example produces a real change in selected entry sessions after the approved correction. The original equal-result diagnostic fixture remains available. No result is hard-coded into the UI.

[Deployment guide](docs/DEPLOYMENT.md) documents the paid disk-backed Render Blueprint, quota/retention behavior and external-device acceptance gate. [Demo and submission preparation](docs/DEMO_AND_SUBMISSION.md) includes a two-minute recording script and honest project-description draft. A public URL, completed cloud verification and actual video are not yet claimed.

## Audit controls and browser regression

The workspace now includes an audit-evaluation view backed by 26 controls generated independently of the fixed demo CSVs. It shows expected versus observed outcomes, source/data fingerprints and detection counts for A01-A03. These are constructed synthetic controls, not an external blind benchmark or evidence of profitability. Reproduce with `python scripts/evaluate_audit.py`; [observed control results](docs/evaluation/README.md) include the complete case list.

Run `npm ci --prefix frontend`, install the pinned Playwright Chromium (`npx playwright install --with-deps chromium` from frontend/), then run `npm run test:e2e --prefix frontend`. The local-only regression starts/stops a temporary Python server and tests desktop/mobile planning, consecutive cost corrections, report download, timing evidence, refresh/history, visitor isolation, invalid data, zero trades, evaluation and offline recovery. Set `QUANTFORGE_PYTHON` if the Python executable is not named `python`. All ordinary automated checks disable live provider calls. CI includes a separate browser job; local results do not prove its remote status.

## Data, safety, and limitations

QuantForge is a research and simulation tool. It will not connect to a broker, place trades, custody assets, promise returns, or automatically search for a supposedly optimal strategy.

The MVP execution model does not establish real-world liquidity, market impact, shorting, leverage, intraday path behavior, or multi-asset portfolio correctness. Corporate-action handling and data adjustment conventions must be disclosed.

Dataset manifests must record provenance, license, currency, timezone, calendar, adjustment policy, synthetic/historical status, and content hash. Private or non-redistributable data must not be committed.

Models must not receive credentials or unrestricted shell, network, filesystem, or code-execution capabilities. User text and dataset metadata are untrusted input. Saved experiments require server-side access checks.

## Team collaboration

Repository: [fyyyaug/QuantForge](https://github.com/fyyyaug/QuantForge).

Collaborators should work on task branches and use pull requests to review changes. Backend/agent and frontend/product work should begin from the same frozen contracts and acceptance examples.

The repository is currently private. Any future public release requires a separate decision and a review of data rights, secrets, and disclosures.

## Integrations and disclosures

Clerk, SurrealDB Agent Memory, Eon Era, Expo, and hosting providers are optional candidates discussed in the source whitepaper. None is claimed as integrated. Cross-run memory must affect an observable planning decision before it is described as agent memory.

Documentation and the backend foundation were developed with Codex from the team's revised QuantForge whitepaper dated October 24, 2026. Target-design documents include future capabilities; implementation and measured verification are tracked separately. Competition requirements and submission eligibility have not been independently verified here.

## License

No software license has been selected. Dataset licenses must be tracked separately.
