import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

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

SAMPLE_LOG = "ERROR: DatabaseConnectionError — could not connect to postgres:5432"


class TestPipeline:

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_HIGH_CONF_ANALYSIS)
    def test_pipeline_success(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_001", SAMPLE_LOG)
        assert result["status"] == "success"
        assert result["bug_report"] is not None
        assert result["bug_report"]["bug_id"] == "BUG-TEST_001"
        assert result["bug_report"]["priority"] == "P1"
        assert result["fallback"] is None

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_LOW_CONF_ANALYSIS)
    def test_pipeline_low_confidence_flagged(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_002", SAMPLE_LOG)
        assert result["status"] == "uncertain"
        assert result["fallback"] is not None
        assert result["fallback"]["confidence"] == 0.42
        assert result["bug_report"] is not None

    @patch("pipeline.pipeline.call_llm", side_effect=ValueError("LLM failed after retries"))
    def test_pipeline_llm_failure_handled(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_003", SAMPLE_LOG)
        assert result["status"] == "error"
        assert result["error"] is not None
        assert result["bug_report"] is None

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_HIGH_CONF_ANALYSIS)
    def test_pipeline_steps_all_present(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_004", SAMPLE_LOG)
        assert "ingestion" in result["steps"]
        assert "llm_analysis" in result["steps"]
        assert "confidence_check" in result["steps"]
        assert "bug_report" in result["steps"]

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_HIGH_CONF_ANALYSIS)
    def test_pipeline_duration_recorded(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_005", SAMPLE_LOG)
        assert "pipeline_duration_s" in result
        assert result["pipeline_duration_s"] >= 0


class TestBugReport:

    def test_bug_report_structure(self):
        from pipeline.bug_report import generate_bug_report
        report = generate_bug_report("log_001", SAMPLE_LOG, MOCK_HIGH_CONF_ANALYSIS)
        assert report["bug_id"] == "BUG-LOG_001"
        assert report["priority"] == "P1"
        assert report["severity"] == "high"
        assert report["status"] == "open"

    def test_severity_to_priority_mapping(self):
        from pipeline.bug_report import generate_bug_report
        for severity, expected_priority in [("critical", "P0"), ("high", "P1"), ("medium", "P2"), ("low", "P3")]:
            analysis = {**MOCK_HIGH_CONF_ANALYSIS, "severity": severity}
            report = generate_bug_report("log_x", SAMPLE_LOG, analysis)
            assert report["priority"] == expected_priority

    def test_low_confidence_flags_manual_review(self):
        from pipeline.bug_report import generate_bug_report
        report = generate_bug_report("log_001", SAMPLE_LOG, MOCK_LOW_CONF_ANALYSIS)
        assert report["requires_manual_review"] is True


class TestEvaluator:

    def _make_result(self, analysis, status="success"):
        return {
            "log_id": "eval_test",
            "status": status,
            "steps": {"llm_analysis": {"status": "ok", "raw_output": analysis}},
        }

    def test_high_confidence_result_passes(self):
        from eval.evaluator import score_result
        result = self._make_result(MOCK_HIGH_CONF_ANALYSIS)
        score = score_result(result)
        assert score["passed"] is True
        assert score["aggregate_score"] >= 0.6

    def test_low_confidence_fails_dimension(self):
        from eval.evaluator import score_result
        result = self._make_result(MOCK_LOW_CONF_ANALYSIS)
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
        results = [self._make_result(MOCK_HIGH_CONF_ANALYSIS), self._make_result(MOCK_LOW_CONF_ANALYSIS)]
        report = run_evaluation(results)
        assert "pass_rate" in report
        assert "mean_aggregate_score" in report
        assert report["total"] == 2


class TestLLMWrapper:

    def test_low_confidence_detection(self):
        from pipeline.llm_wrapper import is_low_confidence
        assert is_low_confidence({"confidence": 0.4}) is True
        assert is_low_confidence({"confidence": 0.6}) is False

    def test_fallback_message_structure(self):
        from pipeline.llm_wrapper import get_fallback_message
        fb = get_fallback_message("log_001", 0.42)
        assert fb["status"] == "uncertain"
        assert fb["confidence"] == 0.42
        assert "manual review" in fb["message"].lower()