# Demo and submission preparation

Status: script and product flow prepared; no recorded video, external user study, public repository transition, or Devpost submission is claimed by this document.

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

All current datasets are synthetic. Split leakage, overfitting risk, and survivorship coverage remain Unverified. Natural-language model planning, historical market data, cross-run agent memory, production account management, and distributed job execution are future work. No broker is connected and no investment performance is promised.

**Tools and prior-work disclosure**

The project was developed with Codex using the team's revised QuantForge whitepaper. Before submission, add the actual team members, development dates, starting code/templates, and changes made during Build Week, checked against version history. Do not claim an integration merely because it appears in the design. Render deployment is not evidence of Clerk, Eon, Expo, or SurrealDB integration.

## Remaining external deliverables

- [ ] Confirm the final deployed source revision and complete the external-device gate in DEPLOYMENT.md.
- [ ] Record and upload the actual demo video; verify an anonymous viewer can play it.
- [ ] Confirm repository visibility and review its contents before any public release.
- [ ] Choose a software license with the team's agreement; the synthetic data's CC0 declaration is separate.
- [ ] Complete real team/prior-work disclosures and any partner-use evidence.
- [ ] Fill the Devpost project form and verify all links before submitting.
- [ ] Record at least one independent user's task outcome if time permits.

The [official Devpost overview](https://build-north.devpost.com/) currently describes an October 25, 2026, 11:59 PM ET submission deadline and an optional video of four minutes or less. A two-minute recording fits that limit and the shorter whitepaper plan. Confirm the final form at submission time.
