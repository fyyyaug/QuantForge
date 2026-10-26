# Demo and submission preparation

Status: script and product flow prepared; no recorded video, external user study, public repository transition, or Devpost submission is claimed by this document.

## Project cover

The selected cover is [QuantForge — Question the curve](submission/quantforge-devpost-cover-v3.png): a 1536 × 1024 PNG in a 3:2 ratio, under the 5 MB Devpost image limit. Use it for the project thumbnail; keep actual application screenshots in the image gallery. The cover is conceptual artwork generated with the built-in imagegen tool. See [cover usage and prompt](submission/README.md).

## Two-minute recording script

Use a fresh demo session and the real deployed build when available. Keep the synthetic and invalid-result labels visible. The suggested spoken script is in English for the event audience.

| Time | Product action | Suggested narration |
| --- | --- | --- |
| 00:00-00:15 | Landing page, Try the live demo | “A convincing equity curve can come from information you could not have known. QuantForge helps student researchers inspect the evidence behind a backtest.” |
| 00:15-00:35 | Review a normal template and its timing/cost assumptions, approve it | “The strategy and its assumptions are explicit. A deterministic Python engine calculates every trade, cost, and performance metric.” |
| 00:35-00:55 | New research, guided diagnostic, review and run | “This separate example deliberately uses tomorrow's close before an opening fill. These prices are synthetic, and this result is intentionally invalid.” |
| 00:55-01:20 | Audit; show the timeline and row evidence | “The source input becomes available after the decision and the simulated fill. The timing rule blocks the experiment and points to the exact record.” |
| 01:20-01:40 | Review timing correction, approve and rerun | “The correction removes that future dependency. Approval creates a new experiment and recomputes it; the original remains intact.” |
| 01:40-02:00 | Compare, changed entry decisions, report | “You can trace which entry decisions changed. Passing these checks does not establish profitability. Current scope is one daily long-only strategy, three implemented audit checks, and clearly labeled synthetic data.” |

The new `timing_trap` fixture deliberately alternates returns around the default threshold. With the current default specification, actual execution yields 7 trades in each run but 14 changed entry signals. The intentionally flawed result is about +83.77%; the corrected result is about -50.81%. These are demonstration outputs from constructed data, not market evidence, claimed alpha, or a guarantee that corrections reduce returns. Recompute before recording; do not type those numbers into the UI.

The original `leaky_next_close` fixture remains supported and retains its original byte hash. It illustrates the separate fact that identical trade results can still have different information validity. The default guided example now uses `timing_trap`.

## One-person usability task

Give a non-team participant the live URL and this task without coaching:

> Run the guided example, identify why its result is invalid, approve a correction, and explain what changed. Find and download the corrected report.

Record completion time, whether they found the row/timestamps, whether they understood changed trade selection, and any help required. Ask them to explain what “Within checked scope” does and does not establish. Do not report the three-minute or five-minute targets as achieved until measured.

## Submission text draft

**Tagline**

QuantForge: reproducible backtests with evidence you can challenge.

**Problem**

Student and independent quantitative researchers can mistake future-information leakage or missing costs for a useful strategy. A polished chart alone does not expose those methodological errors.

**What we built**

QuantForge provides a template-based research workspace with explicit strategy review, a deterministic Python backtest engine, three implemented audit checks, user-approved corrections, preserved experiment history, and a comparison of recalculated results. A guided synthetic timing trap shows exactly which source information was unavailable at the simulated decision and fill.

**Technical implementation**

FastAPI and frozen Pydantic contracts validate requests. Decimal arithmetic calculates daily single-symbol, long-only open-to-close trades and modeled costs. Independent timing, cost, and dataset-integrity rules produce machine-readable evidence. SQLite stores exact approvals, immutable scientific artifacts, idempotency records, and scoped history. A buildless HTML/CSS/JavaScript frontend renders the saved numerical outputs. Optional anonymous demo sessions use isolated workspaces and bounded allowances.

**Limitations and future work**

All current datasets are synthetic. Split leakage, overfitting risk, and survivorship coverage remain Unverified. Optional natural-language planning is implemented but requires provider configuration and live validation before demonstration. Historical market data, cross-run agent memory, production account management and distributed execution remain future work. No broker is connected and no investment performance is promised.

**Tools and prior-work disclosure**

QuantForge is a two-person project by **Xuefeng Qin** (GitHub: [fyyyaug](https://github.com/fyyyaug)) and **Lucas Chu** (GitHub: [Lucccccys](https://github.com/Lucccccys)).

We used **OpenAI Codex** to assist with architecture, documentation, code generation and editing, test development, debugging, and verification. AI-assisted development does not mean that a model runs inside the shipped application: numerical execution, audit verdicts, and report generation remain deterministic. An optional Claude planning adapter is implemented behind explicit configuration, with template fallback; live-provider validation remains pending credentials. No runtime OpenAI model integration is claimed.

The design input was the team's **QuantForge Build North Whitepaper, Revised V2.0, dated October 24, 2026**. Repository history starts with an initial scaffold and planning documents, followed by application implementation. The reviewed history records backend, web-workspace, and anonymous-demo implementation on **October 24, 2026**, followed by planning, audit-evaluation, reporting, and browser-regression enhancements on **October 25, 2026 (America/Toronto)**. We distinguish these implemented features from future capabilities described in the whitepaper.

The implementation uses third-party libraries and development tools, including Python, FastAPI, Pydantic, Uvicorn, SQLite, pytest, Ruff, Node.js, and Prettier. Dependency versions are recorded in `requirements.lock` and `frontend/package-lock.json`. These tools and libraries are existing third-party work, not team-authored components. The reviewed source does not identify an imported application starter or UI template; the application's supported strategy templates are its own constrained research inputs, not a claim to have invented momentum investing or backtesting.

All bundled market-price fixtures are project-generated synthetic data, explicitly labeled as such, with a CC0-1.0 data declaration. They are not licensed historical exchange data or evidence of investment performance. The software itself has no selected license; the fixture declaration does not license the application code.

The repository includes a Render deployment blueprint. A configuration file does not establish a completed deployment. Clerk, Eon Era, Expo, and SurrealDB Agent Memory integrations are not implemented or claimed. Any sponsor-use statement must describe actual verified use.

### Recorded development contributions

The following summarizes commits associated with each member's account. It is a record of submitted changes, not a claim that every line was written manually or by one person alone.

| Member | Changes recorded in repository history | Example commits |
| --- | --- | --- |
| Xuefeng Qin | Project documentation and architecture; deterministic backtest and audit backend; SQLite persistence and API; integrated web workspace; startup diagnostics; exhausted-demo recovery and English user guide | `cf5d9e1`, `1523650`, `b25a6bf`, `df8f8ad` |
| Lucas Chu | Isolated anonymous demo sessions, persistent quotas and expiry; timing-trap dataset; audit timeline and changed-entry comparisons; cloud startup settings, Render blueprint, deployment and demo documentation; optional Claude planning, generated audit controls, enhanced reports, and browser regression coverage | `768ab18`, `36ecbfe` |

Together, these changes implement the supported strategy review, actual numerical backtest, three evidence-backed audit categories, explicitly approved correction runs, preserved parent/child history, exports, anonymous-demo access, and automated verification. Optional natural-language planning requires real-provider validation before being presented as a verified live feature. Cross-run agent memory, production accounts, real market-data integration, and distributed workers remain future work.

Before copying this disclosure into the final submission, both members should add any development tools, reused assets, or work outside the reviewed repository that are not captured here. Repository timestamps establish recorded commits, not the creation date of every design idea or the absence of unrecorded prior work. Team eligibility and event registration must be confirmed separately; names and commit history do not establish eligibility.

## Remaining external deliverables

- [ ] Confirm the final deployed source revision and complete the external-device gate in DEPLOYMENT.md.
- [ ] Record and upload the actual demo video; verify an anonymous viewer can play it.
- [ ] Confirm repository visibility and review its contents before any public release.
- [ ] Choose a software license with the team's agreement; the synthetic data's CC0 declaration is separate.
- [x] Document both team members and the repository-backed development / AI-tool disclosure above.
- [ ] Have both members confirm any unrecorded prior work, additional tools or assets, and actual partner use; copy the final disclosure into Devpost.
- [ ] Fill the Devpost project form and verify all links before submitting.
- [ ] Record at least one independent user's task outcome if time permits.

The [official Devpost overview](https://build-north.devpost.com/) currently describes an October 25, 2026, 11:59 PM ET submission deadline and an optional video of four minutes or less. A two-minute recording fits that limit and the shorter whitepaper plan. Confirm the final form at submission time.

## Optional additions to the demonstration

If live Claude planning has actually been configured and verified, show its proposed/defaulted parameters and exact user approval. Otherwise keep the template path and explicitly state that live planning is unverified. The auditor-evaluation view now exposes 26 generated synthetic controls, and comparison reports export both experiments. These additions do not substitute for a real user study, public deployment or an actual submission/video.
