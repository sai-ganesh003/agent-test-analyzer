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

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_HIGH_CONF_ANALYSIS)
    def test_pipeline_log_id_preserved(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("my_custom_id", SAMPLE_LOG)
        assert result["log_id"] == "my_custom_id"

    @patch("pipeline.pipeline.call_llm", return_value=MOCK_HIGH_CONF_ANALYSIS)
    def test_pipeline_ingestion_records_log_length(self, mock_llm):
        from pipeline.pipeline import run_pipeline
        result = run_pipeline("test_006", SAMPLE_LOG)
        assert result["steps"]["ingestion"]["log_length"] == len(SAMPLE_LOG)