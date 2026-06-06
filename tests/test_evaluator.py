import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

MOCK_HIGH_CONF_ANALYSIS = {
    "root_cause": "Database connection pool exhausted due to missing connection timeout and retry configuration in the ORM layer",
    "fix": "Set pool_timeout=30 and pool_recycle=1800 in SQLAlchemy engine config and add exponential backoff retry logic",
    "severity": "high",
    "confidence": 0.88,
    "summary": "Database connection pool exhausted causing task failures.",
    "affected_component": "lib/db.py",
    "tags": ["database", "connection-pool", "sqlalchemy"],
}

MOCK_LOW_CONF_ANALYSIS = {
    "root_cause": "Unknown failure possibly related to network or config",
    "fix": "Investigate further with more detailed logs",
    "severity": "medium",
    "confidence": 0.42,
    "summary": "Unclear error requiring manual review.",
    "affected_component": "unknown",
    "tags": [],
}


def make_result(analysis, status="success"):
    return {
        "log_id": "eval_test",
        "status": status,
        "steps": {"llm_analysis": {"status": "ok", "raw_output": analysis}},
    }


class TestEvaluator:

    def test_high_confidence_result_passes(self):
        from eval.evaluator import score_result
        result = make_result(MOCK_HIGH_CONF_ANALYSIS)
        score = score_result(result)
        assert score["passed"] is True
        assert score["aggregate_score"] >= 0.6

    def test_low_confidence_fails_dimension(self):
        from eval.evaluator import score_result
        result = make_result(MOCK_LOW_CONF_ANALYSIS)
        score = score_result(result)
        assert score["dimensions"]["confidence_ok"] == 0

    def test_error_pipeline_scores_zero(self):
        from eval.evaluator import score_result
        result = {"log_id": "error_log", "status": "error", "steps": {}}
        score = score_result(result)
        assert score["aggregate_score"] == 0.0
        assert score["passed"] is False

    def test_evaluation_report_structure(self):
        from eval.evaluator import run_evaluation
        results = [make_result(MOCK_HIGH_CONF_ANALYSIS), make_result(MOCK_LOW_CONF_ANALYSIS)]
        report = run_evaluation(results)
        assert "pass_rate" in report
        assert "mean_aggregate_score" in report
        assert report["total"] == 2

    def test_all_dimensions_present_in_score(self):
        from eval.evaluator import score_result
        result = make_result(MOCK_HIGH_CONF_ANALYSIS)
        score = score_result(result)
        expected_dims = ["root_cause_present", "fix_present", "confidence_ok", "severity_valid", "summary_present"]
        for dim in expected_dims:
            assert dim in score["dimensions"], f"Missing dimension: {dim}"

    def test_failed_log_ids_captured(self):
        from eval.evaluator import run_evaluation
        results = [make_result(MOCK_LOW_CONF_ANALYSIS, status="error")]
        report = run_evaluation(results)
        assert len(report["failed_log_ids"]) > 0

    def test_perfect_score_all_dimensions(self):
        from eval.evaluator import score_result
        result = make_result(MOCK_HIGH_CONF_ANALYSIS)
        score = score_result(result)
        assert score["aggregate_score"] == 1.0

    def test_pass_rate_calculation(self):
        from eval.evaluator import run_evaluation
        results = [
            make_result(MOCK_HIGH_CONF_ANALYSIS),
            make_result(MOCK_HIGH_CONF_ANALYSIS),
            make_result(MOCK_LOW_CONF_ANALYSIS, status="error"),
        ]
        report = run_evaluation(results)
        assert report["pass_rate"] == round(2/3, 2)