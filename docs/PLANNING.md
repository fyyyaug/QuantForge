# Optional natural-language planning

The application includes a bounded Claude Messages API adapter. The default template workflow performs no model calls. A real provider call and real-model semantic accuracy have **not** been verified in this environment because no Anthropic key is configured. Tests of the adapter use fake credentials and simulated provider responses; they are contract/error-path tests, not proof of a model understanding a hypothesis.

## Operator setup

Configure these variables in the server process environment; do not put secrets in a commit or browser form:

```sh
export QUANTFORGE_ENABLE_PLANNER=true
export ANTHROPIC_API_KEY=... # configure privately in your shell/secret manager
export QUANTFORGE_PLANNER_MODEL=... # a Claude model supporting JSON structured outputs
```

`ANTHROPIC_WORKSPACE_ID` is optional for a key scoped to a workspace and required when Anthropic requires explicit workspace selection. No model is silently selected. Missing credentials, an invalid/missing model identifier or disabled planning leaves the UI in **AI NOT CONFIGURED** mode. The server does not automatically read `.env` files.

Before a configured draft is requested, the UI states that the hypothesis is sent to Anthropic and requires the user to acknowledge that transmission. Only the hypothesis and fixed planner instructions/schema are sent. Prices, saved reports, workspace tokens, browser cookies and server credentials are not sent as model context. Authentication credentials are used only in the provider's HTTPS request headers. A fixed Anthropic endpoint is used; HTTP redirects are rejected.

## Contract and authority

`POST /api/research/hypotheses` accepts an authenticated workspace, a selected dataset ID and a hypothesis of 10-1,200 characters. The model can propose only lookback, threshold, NAV, allocation, fee/slippage and sample dates. It cannot choose code, a network destination, dataset identity, an audit verdict or a performance number. The only supported instrument is the fictional SYNTH symbol, daily trailing momentum, long-only, next-open entry and same-session-close exit.

The provider uses a JSON schema with PLAN / CLARIFY / UNSUPPORTED outcomes. All parameter keys must be present; null means a disclosed template default. A second local Pydantic validation checks ranges, finite decimals, timing policy and the supported specification. Invalid output creates no plan. Clarifications and unsupported requests do not queue a run. A valid draft is stored **unapproved**; exact-hash user approval is still required before execution.

Saved plans and runs record the planning source, model, proposed/defaulted field names, and hashes of the hypothesis/proposal. The raw hypothesis and API credential are not persisted. An approved correction records its rationale, diff and originating finding. The engine and deterministic rule code continue to own every metric and verdict. Structured shape checks do not establish semantic correctness, so the review screen remains essential.

## Bounded calls and fallback

Defaults are 3 attempts per workspace and 20 attempts across the service per fixed clock hour, 768 maximum output tokens per attempt, a 32 KiB response bound and an 8-second socket I/O timeout. Attempts are reserved transactionally before the external request, including failed calls. The counters survive service restarts. This bounds calls/tokens; it is not a dollar-denominated spend cap or hard worker wall-clock kill timeout. Set an account-level spend cap in Anthropic as appropriate for the selected model.

There is no automatic retry. Provider authentication errors, timeout, refusal, truncation, schema errors and unsupported parameters produce controlled errors. No template is silently substituted for a failed natural-language interpretation. The user can explicitly use the editable template afterward. Operational call records contain a workspace ID, timestamp and status, and are retained for at most about 24 hours until the next planning sweep; they contain no prompt or provider response text.

## Verification

Ordinary pytest, HTTP smoke, browser regression and CI explicitly disable live model calls. Adapter tests cover request shape, schema/range checks, clarification/unsupported outcomes, no implicit approval, persisted provenance, provider failures, no secret reflection and quotas across restarts/workspaces.

`fixtures/planner_cases.json` supplies ten public labelled prompts covering English/Chinese requests, defaults, ambiguity, shorting, leverage, portfolios, same-close execution, prompt injection and a real ticker. These are expected labels, **not measured outcomes**.

To measure a configured model, explicitly authorize up to ten billable calls:

```sh
python scripts/evaluate_planner.py --live
```

The command never runs automatically in CI. It uses disposable local storage, permits ten attempts for its evaluation workspace, keeps the service-level attempt bound, and writes observed results to `.quantforge-planner-evaluation/planner-evaluation.json`. It exits nonzero on mismatch/incomplete execution and stops early on provider unavailability. Review its actual output before making model-accuracy claims. Its budget is local to this explicitly invoked command, separate from a running web service.

## Provider references

- [Claude API authentication and versions](https://platform.claude.com/docs/en/api/overview)
- [Claude JSON structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

The adapter uses API version `2026-10-21` and the documented `output_config.format` schema mechanism. Validate the chosen model and credentials in the target Anthropic workspace before demonstrating live planning.
