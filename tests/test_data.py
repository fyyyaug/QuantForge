import csv
import hashlib
import io

import pytest

from backend.data import Snapshot, validate_data
from backend.errors import ResearchError


def altered(snapshot, mutate):
    rows = list(csv.DictReader(io.StringIO(snapshot.content.decode())))
    fields = list(rows[0])
    mutate(rows, fields)
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    content = text.getvalue().encode()
    manifest = snapshot.manifest.model_copy(
        update={"byte_hash": hashlib.sha256(content).hexdigest(), "row_count": len(rows)}
    )
    return Snapshot(manifest, content)


@pytest.mark.parametrize("fixture", ["missing_open", "duplicate_sessions", "invalid_ohlc"])
def test_malformed_pinned_fixtures(service, catalog, fixture):
    spec = service.template(fixture)
    _bars, issues = validate_data(catalog.load(fixture), spec)
    assert issues
    assert any(i.row_number for i in issues)


@pytest.mark.parametrize(
    "field,value",
    [
        ("volume", "-1"),
        ("volume", "NaN"),
        ("open", "0"),
        ("close", "Infinity"),
        ("open", ""),
        ("date", "not-a-date"),
        ("symbol", "WRONG"),
    ],
)
def test_csv_value_errors_preserve_row_number(service, catalog, field, value):
    snapshot = altered(catalog.load("clean_momentum"), lambda rows, fields: rows[4].update({field: value}))
    spec = service.template()
    spec = spec.model_copy(update={"dataset_hash": snapshot.manifest.byte_hash})
    _, issues = validate_data(snapshot, spec)
    assert any(i.row_number == 6 for i in issues)


def test_missing_columns(service, catalog):
    source = catalog.load("clean_momentum")
    content = b"date,symbol,close\n2026-01-02,SYNTH,100\n"
    snapshot = Snapshot(source.manifest, content)
    _, issues = validate_data(snapshot, service.template())
    assert any(i.field == "columns" for i in issues)


def test_sample_outside_data_is_blocked(service, catalog):
    spec = service.template(overrides={"sample_start": "2030-01-01", "sample_end": "2030-01-02"})
    _, issues = validate_data(catalog.load("clean_momentum"), spec)
    assert any(i.field == "sample" for i in issues)


def test_hash_mismatch_is_not_silently_substituted(service, catalog):
    spec = service.template().model_copy(update={"dataset_hash": "0" * 64})
    _, issues = validate_data(catalog.load("clean_momentum"), spec)
    assert any(i.field == "dataset_hash" for i in issues)


def test_catalog_rejects_path_traversal(catalog):
    with pytest.raises(ResearchError) as error:
        catalog.load("../../private")
    assert error.value.code == "NOT_FOUND"


def test_catalog_detects_tampered_fixture(tmp_path, catalog):
    from backend.data import DatasetCatalog

    source = catalog.load("clean_momentum")
    (tmp_path / "clean_momentum.csv").write_bytes(source.content + b"tamper")
    (tmp_path / "clean_momentum.json").write_text(source.manifest.model_dump_json())
    with pytest.raises(ResearchError) as error:
        DatasetCatalog(tmp_path).load("clean_momentum")
    assert error.value.code == "DATASET_UNAVAILABLE"


def test_missing_open_evidence_names_exact_field(service, catalog):
    _, issues = validate_data(catalog.load("missing_open"), service.template("missing_open"))
    assert any(issue.field == "open" and issue.row_number == 10 for issue in issues)
