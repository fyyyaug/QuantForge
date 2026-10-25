# Audit control evaluation

Generated synthetic controls for A01 timing, A02 costs and A03 data integrity.

Not an external blind benchmark or a market backtest. Constructed controls do not establish profitability, arbitrary-strategy coverage or real-world detection rates. A04-A06 remain Unverified.

Matched: 26 / 26 expected outcomes.

| Case | Rule | Expected | Observed | Matched |
| --- | --- | --- | --- | --- |
| valid_data_seed_104729 | A03_DATA_INTEGRITY | PASS | PASS | True |
| lawful_timing_seed_104729 | A01_LOOKAHEAD | PASS | PASS | True |
| future_close_seed_104729 | A01_LOOKAHEAD | FAIL | FAIL | True |
| after_decision_before_fill_seed_104729 | A01_LOOKAHEAD | FAIL | FAIL | True |
| equal_decision_boundary_seed_104729 | A01_LOOKAHEAD | FAIL | FAIL | True |
| missing_lineage_seed_104729 | A01_LOOKAHEAD | FAIL | FAIL | True |
| explicit_costs_seed_104729 | A02_MISSING_COSTS | PASS | PASS | True |
| zero_costs_seed_104729 | A02_MISSING_COSTS | WARN | WARN | True |
| missing_open_seed_104729 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| duplicate_session_seed_104729 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| invalid_ohlc_seed_104729 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| negative_volume_seed_104729 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| nonfinite_close_seed_104729 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| valid_data_seed_130363 | A03_DATA_INTEGRITY | PASS | PASS | True |
| lawful_timing_seed_130363 | A01_LOOKAHEAD | PASS | PASS | True |
| future_close_seed_130363 | A01_LOOKAHEAD | FAIL | FAIL | True |
| after_decision_before_fill_seed_130363 | A01_LOOKAHEAD | FAIL | FAIL | True |
| equal_decision_boundary_seed_130363 | A01_LOOKAHEAD | FAIL | FAIL | True |
| missing_lineage_seed_130363 | A01_LOOKAHEAD | FAIL | FAIL | True |
| explicit_costs_seed_130363 | A02_MISSING_COSTS | PASS | PASS | True |
| zero_costs_seed_130363 | A02_MISSING_COSTS | WARN | WARN | True |
| missing_open_seed_130363 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| duplicate_session_seed_130363 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| invalid_ohlc_seed_130363 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| negative_volume_seed_130363 | A03_DATA_INTEGRITY | FAIL | FAIL | True |
| nonfinite_close_seed_130363 | A03_DATA_INTEGRITY | FAIL | FAIL | True |

Generated with `python scripts/evaluate_audit.py`. Full source/data fingerprints and detection counts are in audit-evaluation.json.
