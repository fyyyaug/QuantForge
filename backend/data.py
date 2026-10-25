"""Read-only pinned fixture catalog and strict CSV validation."""

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from .errors import ResearchError
from .models import Bar, DataIssue, DatasetManifest, StrategySpec

CATALOG_IDS = frozenset(
    {"clean_momentum", "leaky_next_close", "timing_trap", "missing_open", "duplicate_sessions", "invalid_ohlc"}
)
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10000
REQUIRED = {"date", "symbol", "open", "high", "low", "close", "volume"}


@dataclass(frozen=True)
class Snapshot:
    manifest: DatasetManifest
    content: bytes


class DatasetCatalog:
    def __init__(self, root: Path):
        self.root = root

    def load(self, dataset_id: str) -> Snapshot:
        if dataset_id not in CATALOG_IDS:
            raise ResearchError("NOT_FOUND", "Dataset not found", 404)
        try:
            manifest = DatasetManifest.model_validate_json((self.root / f"{dataset_id}.json").read_text("utf-8"))
            content = (self.root / f"{dataset_id}.csv").read_bytes()
        except (OSError, ValueError) as exc:
            raise ResearchError("DATASET_UNAVAILABLE", "Pinned dataset is unavailable", 503) from exc
        if len(content) > MAX_BYTES:
            raise ResearchError("RESOURCE_LIMIT", "Dataset exceeds byte limit")
        if manifest.dataset_id != dataset_id or hashlib.sha256(content).hexdigest() != manifest.byte_hash:
            raise ResearchError("DATASET_UNAVAILABLE", "Pinned dataset hash mismatch", 503)
        return Snapshot(manifest, content)

    def list(self):
        return [self.load(key).manifest for key in sorted(CATALOG_IDS)]


def validate_data(snapshot: Snapshot, spec: StrategySpec) -> tuple[tuple[Bar, ...], tuple[DataIssue, ...]]:
    issues: list[DataIssue] = []
    if (
        spec.dataset_id != snapshot.manifest.dataset_id
        or spec.dataset_version != snapshot.manifest.version
        or spec.dataset_hash != snapshot.manifest.byte_hash
    ):
        issues.append(DataIssue(field="dataset_hash", reason="Pinned dataset identity does not match plan"))
    if spec.symbol != snapshot.manifest.symbol or spec.currency != snapshot.manifest.currency:
        issues.append(DataIssue(field="symbol", reason="Symbol or currency does not match dataset"))
    try:
        reader = csv.DictReader(io.StringIO(snapshot.content.decode("utf-8-sig")), strict=True)
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields) or set(fields) != REQUIRED:
            return (), tuple(
                issues
                + [DataIssue(field="columns", reason="Expected unique date,symbol,open,high,low,close,volume columns")]
            )
        rows = list(reader)
    except (UnicodeError, csv.Error):
        return (), tuple(issues + [DataIssue(field="csv", reason="Invalid UTF-8 CSV format")])
    if len(rows) > MAX_ROWS:
        return (), (DataIssue(field="rows", reason="Dataset exceeds row limit"),)
    if len(rows) != snapshot.manifest.row_count:
        issues.append(DataIssue(field="rows", reason="Row count does not match manifest"))
    bars = []
    previous = None
    seen = set()
    for number, row in enumerate(rows, 2):
        try:
            if None in row:
                raise ValueError("Extra cells")
            missing = [key for key, value in row.items() if value is None or not value.strip()]
            if missing:
                issues.extend(
                    DataIssue(row_number=number, field=key, reason="Required value is missing") for key in missing
                )
                continue
            bar = Bar(
                row_number=number,
                session=date.fromisoformat(row["date"]),
                symbol=row["symbol"],
                **{key: row[key] for key in ("open", "high", "low", "close", "volume")},
            )
        except ValidationError as exc:
            issues.extend(
                DataIssue(row_number=number, field=str(error["loc"][0]), reason="Value violates finite numeric bounds")
                for error in exc.errors()
            )
            continue
        except (ValueError, TypeError):
            issues.append(
                DataIssue(row_number=number, field="row", reason="Missing, invalid, nonpositive, or nonfinite value")
            )
            continue
        key = (bar.symbol, bar.session)
        if key in seen:
            issues.append(DataIssue(row_number=number, field="date", reason="Duplicate symbol/session key"))
        if previous is not None and bar.session <= previous:
            issues.append(DataIssue(row_number=number, field="date", reason="Sessions must be strictly increasing"))
        if bar.symbol != snapshot.manifest.symbol:
            issues.append(DataIssue(row_number=number, field="symbol", reason="Unexpected symbol"))
        if not (bar.low <= bar.open <= bar.high and bar.low <= bar.close <= bar.high):
            issues.append(
                DataIssue(row_number=number, field="OHLC", reason="Prices violate low/open/close/high ordering")
            )
        seen.add(key)
        previous = bar.session
        bars.append(bar)
    if not bars:
        issues.append(DataIssue(field="rows", reason="Dataset contains no valid rows"))
    elif bars[0].session != snapshot.manifest.start_session or bars[-1].session != snapshot.manifest.end_session:
        issues.append(DataIssue(field="coverage", reason="Session coverage does not match manifest"))
    if bars and not any(spec.sample_start <= bar.session <= spec.sample_end for bar in bars):
        issues.append(DataIssue(field="sample", reason="Sample contains no observations"))
    return tuple(bars), tuple(issues)
