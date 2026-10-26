from backend.evaluation import evaluate_audits


def test_independent_generated_controls_are_reproducible_and_have_no_mismatches():
    result = evaluate_audits()
    assert result == evaluate_audits()
    assert result["summary"] == {"total": 26, "passed": 26}
    assert len(set(result["generation"]["dataset_hashes"])) == 12
    for counts in result["detection"].values():
        assert counts["false_positive"] == counts["false_negative"] == 0
        assert counts["true_positive"] > 0 and counts["true_negative"] > 0
    assert all(c["evidence_count"] > 0 for c in result["cases"] if c["expected"] == "FAIL")


def test_evaluation_endpoint_is_scoped_to_authenticated_access(client):
    assert client.get("/api/evaluation").json()["summary"]["passed"] == 26
    client.headers.pop("Authorization")
    assert client.get("/api/evaluation").status_code == 401
