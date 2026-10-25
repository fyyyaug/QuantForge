"""Bounded template planner, orchestrator, corrections, and factual reports."""

import importlib.metadata
import logging
import platform
import threading
from pathlib import Path

from . import audit
from .canonical import digest, plain
from .data import DatasetCatalog, validate_data
from .engine import ENGINE_VERSION, build_decisions, simulate
from .errors import ResearchError
from .models import Finding, StrategySpec
from .store import Store

logger = logging.getLogger(__name__)


class ResearchService:
    def __init__(self, store: Store, catalog: DatasetCatalog):
        self.store = store
        self.catalog = catalog
        self.execution_lock = threading.Lock()
        source_root = Path(__file__).resolve().parent
        self.source_hash = digest(
            {
                path.relative_to(source_root).as_posix(): path.read_text("utf-8")
                for path in sorted(source_root.rglob("*.py"))
            }
        )
        lockfile = source_root.parent / "requirements.lock"
        self.dependency_hash = digest(lockfile.read_text("utf-8")) if lockfile.exists() else "unlocked"

    def template(self, dataset_id="clean_momentum", overrides=None):
        manifest = self.catalog.load(dataset_id).manifest
        fields = {
            "dataset_id": dataset_id,
            "dataset_hash": manifest.byte_hash,
            "symbol": manifest.symbol,
            "sample_start": manifest.start_session,
            "sample_end": manifest.end_session,
        }
        fields.update(overrides or {})
        spec = StrategySpec.model_validate(fields)
        if spec.dataset_id != dataset_id or spec.dataset_hash != manifest.byte_hash:
            raise ResearchError("INVALID_SPEC", "Template overrides cannot replace dataset identity")
        return spec

    def execute(self, workspace, identity):
        # A process-wide execution lock plus atomic state transitions prevents duplicate execution.
        with self.execution_lock:
            run = self.store.get("runs", identity, workspace)
            if run["state"] != "QUEUED":
                return self.view(workspace, identity)
            self.store.transition(workspace, identity, "VALIDATING")
            try:
                spec = StrategySpec.model_validate_json(run["spec"])
                snapshot = self.catalog.load(spec.dataset_id)
                bars, issues = validate_data(snapshot, spec)
                findings = [audit.integrity(issues)]
                result = None
                decisions = ()
                diagnostic = run["mode"] == "DIAGNOSTIC_INVALID"
                if not issues:
                    decisions, skips = build_decisions(bars, spec, diagnostic_future=diagnostic)
                    preflight = audit.timing(decisions)
                    if preflight.status != "FAIL" or diagnostic:
                        self.store.transition(workspace, identity, "RUNNING")
                        result = simulate(bars, spec, decisions, skips)
                    # Re-evaluate evidence after execution rather than accepting a preflight flag.
                    findings.append(audit.timing(decisions))
                else:
                    findings.append(
                        Finding(
                            check_id="A01_LOOKAHEAD",
                            status="UNVERIFIED",
                            explanation="Dataset integrity blocked feature generation",
                        )
                    )
                self.store.transition(workspace, identity, "AUDITING")
                findings.extend((audit.costs(spec, result), *audit.uncovered()))
                blocked = diagnostic or any(f.execution_effect == "BLOCK" for f in findings)
                mandatory_unknown = any(
                    f.status == "UNVERIFIED" for f in findings if f.check_id.startswith(("A01", "A03"))
                )
                admissibility = (
                    "BLOCKED" if blocked else "UNVERIFIED" if mandatory_unknown else "ADMISSIBLE_WITHIN_CHECKED_SCOPE"
                )
                scientific = {
                    "spec": spec,
                    "dataset": snapshot.manifest,
                    "mode": run["mode"],
                    "decisions": decisions,
                    "result": result,
                    "findings": findings,
                    "admissibility": admissibility,
                    "versions": {
                        "engine": ENGINE_VERSION,
                        "rules": "1",
                        "schema": "1",
                        "precision": 34,
                        "python": platform.python_version(),
                        "pydantic": importlib.metadata.version("pydantic"),
                        "source_hash": self.source_hash,
                        "dependency_lock_hash": self.dependency_hash,
                        "normalized_data_hash": digest(bars),
                    },
                }
                scientific = plain(scientific)
                scientific["scientific_hash"] = digest(scientific)
                self.store.transition(workspace, identity, "REPORTING")
                scientific["report"] = self.report(scientific)
                self.store.transition(workspace, identity, "COMPLETED", artifact=scientific)
            except ResearchError as exc:
                self.store.transition(workspace, identity, "FAILED", error=exc.code)
            except Exception:
                logger.exception("Research execution failed for run %s", identity)
                self.store.transition(workspace, identity, "FAILED", error="INTERNAL_EXECUTION_ERROR")
            return self.view(workspace, identity)

    @staticmethod
    def report(artifact):
        lines = [
            "# QuantForge Research Report",
            "",
            f"Admissibility: {artifact['admissibility']}",
            f"Execution mode: {artifact['mode']}",
            "Dataset: SYNTHETIC",
            "",
            "Research simulation only. No investment recommendation or guarantee of performance.",
            "",
        ]
        if artifact["mode"] == "DIAGNOSTIC_INVALID":
            lines.append("INTENTIONALLY FLAWED DIAGNOSTIC: future information was used; results are invalid.")
        if artifact["result"] is None:
            lines.append("No simulation result is available. No performance metrics are claimed.")
        else:
            for key, value in artifact["result"]["metrics"].items():
                lines.append(f"- {key}: {value if value is not None else 'N/A'}")
        lines.extend(["", "## Audit coverage"])
        lines.extend(f"- {f['check_id']}: {f['status']} - {f['explanation']}" for f in artifact["findings"])
        lines.extend(
            [
                "",
                "## Limitations",
                *artifact["dataset"]["limitations"],
                "Unverified rules do not establish absence of bias. Costs and fills are simplified assumptions.",
                "",
                f"Scientific artifact hash: {artifact['scientific_hash']}",
            ]
        )
        return "\n".join(lines) + "\n"

    def view(self, workspace, identity):
        run = self.store.get("runs", identity, workspace)
        return {
            "run_id": run["id"],
            "state": run["state"],
            "error": run["error"],
            "execution_mode": run["mode"],
            "parent_run_id": run["parent_id"],
            "spec_hash": run["spec_hash"],
            "artifact_hash": run["artifact_hash"],
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
        }

    def history(self, workspace, limit=50):
        return [
            {
                **self.view(workspace, row["id"]),
                "symbol": plain(row_spec.symbol),
                "dataset_id": row_spec.dataset_id,
                "sample_start": str(row_spec.sample_start),
                "sample_end": str(row_spec.sample_end),
            }
            for row in self.store.list_runs(workspace, limit)
            for row_spec in [StrategySpec.model_validate_json(row["spec"])]
        ]

    def propose(self, workspace, identity, kind, fee="5", slippage="5"):
        artifact = self.store.artifact(workspace, identity)
        spec = StrategySpec.model_validate(artifact["spec"])
        if kind == "timing":
            if artifact["mode"] != "DIAGNOSTIC_INVALID":
                raise ResearchError("NO_SUPPORTED_CORRECTION", "This run has no diagnostic timing correction")
            corrected = spec
            classification = "METHODOLOGY_CORRECTION"
            rationale = "Remove privileged future-close diagnostic behavior; restore trailing signal at t. Economic meaning changes."
            diff = {
                "execution_mode": {"before": "DIAGNOSTIC_INVALID", "after": "RESEARCH"},
                "feature_source": {"before": "close(t+1)", "after": "close(t)"},
            }
            finding_id = "A01_LOOKAHEAD"
        elif kind == "costs":
            if artifact["mode"] != "RESEARCH" or artifact["result"] is None:
                raise ResearchError("NO_SUPPORTED_CORRECTION", "Cost sensitivity requires a normal simulated run")
            values = spec.model_dump()
            values.update(fee_bps_each_side=fee, slippage_bps_each_side=slippage)
            corrected = StrategySpec.model_validate(values)
            if corrected.fee_bps_each_side + corrected.slippage_bps_each_side == 0 or corrected == spec:
                raise ResearchError("INVALID_SPEC", "Cost sensitivity must change the plan to nonzero costs")
            classification = "CONTROLLED_ASSUMPTION_CHANGE"
            rationale = "Recompute the same signal and gross fills under explicit nonzero modeled costs."
            diff = {
                key: {"before": getattr(spec, key), "after": getattr(corrected, key)}
                for key in ("fee_bps_each_side", "slippage_bps_each_side")
                if getattr(spec, key) != getattr(corrected, key)
            }
            finding_id = "A02_MISSING_COSTS"
        else:
            raise ResearchError("NO_SUPPORTED_CORRECTION", "Unknown correction kind")
        proposal = {
            "spec": corrected,
            "base_spec_hash": digest(spec),
            "diff": diff,
            "classification": classification,
            "rationale": rationale,
            "finding_id": finding_id,
            "requires_approval": True,
        }
        return self.store.correction(workspace, identity, proposal)

    def compare(self, workspace, left_id, right_id):
        left = self.store.artifact(workspace, left_id)
        right = self.store.artifact(workspace, right_id)
        diff = {
            key: {"before": left["spec"][key], "after": right["spec"][key]}
            for key in left["spec"]
            if left["spec"][key] != right["spec"][key]
        }
        costs_only = set(diff) <= {"fee_bps_each_side", "slippage_bps_each_side", "allocation_fraction", "initial_nav"}
        same_data = left["dataset"]["byte_hash"] == right["dataset"]["byte_hash"]
        if not same_data or left["versions"] != right["versions"] or not costs_only:
            classification = "NOT_DIRECTLY_COMPARABLE"
        elif left["mode"] != right["mode"]:
            classification = "METHODOLOGY_CORRECTION"
        else:
            classification = "CONTROLLED_ASSUMPTION_CHANGE" if diff else "IDENTICAL_CONFIGURATION"
        decision_changes = None
        if same_data and left["versions"] == right["versions"] and classification != "NOT_DIRECTLY_COMPARABLE":
            previous = {d["entry_at"]: d for d in left["decisions"]}
            changed = [
                {
                    "entry_at": d["entry_at"],
                    "before_feature": previous[d["entry_at"]]["feature_value"],
                    "after_feature": d["feature_value"],
                    "before_triggered": previous[d["entry_at"]]["triggered"],
                    "after_triggered": d["triggered"],
                }
                for d in right["decisions"]
                if d["entry_at"] in previous and d["triggered"] != previous[d["entry_at"]]["triggered"]
            ]
            decision_changes = {
                "changed_signals": len(changed),
                "changes": changed,
                "before_trade_count": len(left["result"]["trades"]) if left["result"] else None,
                "after_trade_count": len(right["result"]["trades"]) if right["result"] else None,
            }
        return {
            "left_run_id": left_id,
            "right_run_id": right_id,
            "classification": classification,
            "spec_diff": diff,
            "mode_diff": {"before": left["mode"], "after": right["mode"]},
            "decision_changes": decision_changes,
            "left": {
                "admissibility": left["admissibility"],
                "metrics": left["result"]["metrics"] if left["result"] else None,
            },
            "right": {
                "admissibility": right["admissibility"],
                "metrics": right["result"]["metrics"] if right["result"] else None,
            },
            "limitations": "No curve alignment or performance significance is implied.",
        }
