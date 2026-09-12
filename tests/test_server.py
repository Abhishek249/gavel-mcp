from gavel.server import validate_candidate_pipeline


def test_mcp_tool_returns_json_safe_report() -> None:
    report = validate_candidate_pipeline(faults=["timezone_shift"], row_count=100, seed=1)
    assert report["status"] == "fail"
    assert "pickup_hour_distribution" in [
        check["name"] for check in report["checks"] if check["status"] == "fail"
    ]

