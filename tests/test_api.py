import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

MOCK_PIPELINE_RESULT = {
    "log_id": "log_001",
    "status": "success",
    "pipeline_start": "2026-05-01T00:00:00+00:00",
    "pipeline_duration_s": 1.2,
    "steps": {
        "ingestion": {"status": "ok", "log_length": 50, "log_preview": "ERROR: something"},
        "llm_analysis": {
            "status": "ok",
            "duration_s": 1.0,
            "confidence": 0.88,
            "severity": "high",
            "raw_output": {
                "root_cause": "Database connection pool exhausted due to missing timeout config in ORM layer",
                "fix": "Set pool_timeout=30 and pool_recycle=1800 in SQLAlchemy engine config",
                "severity": "high",
                "confidence": 0.88,
                "summary": "Connection pool exhausted causing task failures.",
                "affected_component": "lib/db.py",
                "tags": ["database"],
            },
        },
        "confidence_check": {"status": "ok", "confidence": 0.88},
        "bug_report": {"status": "ok", "bug_id": "BUG-LOG_001"},
    },
    "bug_report": {
        "bug_id": "BUG-LOG_001",
        "title": "Connection pool exhausted",
        "priority": "P1",
        "severity": "high",
        "affected_component": "lib/db.py",
        "root_cause": "Database connection pool exhausted",
        "recommended_fix": "Set pool_timeout=30",
        "tags": ["database"],
        "confidence": 0.88,
        "source_log_snippet": "ERROR: something",
        "filed_at": "2026-05-01T00:00:00+00:00",
        "status": "open",
        "requires_manual_review": False,
    },
    "fallback": None,
    "error": None,
}


class TestHealthEndpoint:

    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_returns_timestamp(self):
        response = client.get("/health")
        assert "timestamp" in response.json()


class TestAnalyzeEndpoint:

    @patch("api.main.run_pipeline", return_value=MOCK_PIPELINE_RESULT)
    @patch("api.main.score_result", return_value={"aggregate_score": 0.9, "passed": True})
    def test_analyze_success(self, mock_score, mock_pipeline):
        response = client.post("/analyze", json={
            "log_id": "log_001",
            "log": "ERROR: DatabaseConnectionError could not connect to postgres:5432"
        })
        assert response.status_code == 200
        assert "eval_score" in response.json()

    def test_analyze_empty_log_returns_400(self):
        response = client.post("/analyze", json={
            "log_id": "log_001",
            "log": "   "
        })
        assert response.status_code == 400

    def test_analyze_missing_log_field_returns_422(self):
        response = client.post("/analyze", json={
            "log_id": "log_001"
        })
        assert response.status_code == 422

    def test_analyze_missing_log_id_returns_422(self):
        response = client.post("/analyze", json={
            "log": "ERROR: something went wrong"
        })
        assert response.status_code == 422

    @patch("api.main.run_pipeline", side_effect=Exception("unexpected crash"))
    def test_analyze_pipeline_exception_returns_500(self, mock_pipeline):
        response = client.post("/analyze", json={
            "log_id": "log_001",
            "log": "ERROR: something went wrong in the system"
        })
        assert response.status_code == 500


class TestBatchEndpoint:

    @patch("api.main.run_pipeline", return_value=MOCK_PIPELINE_RESULT)
    @patch("api.main.score_result", return_value={"aggregate_score": 0.9, "passed": True})
    def test_batch_analyze_success(self, mock_score, mock_pipeline):
        payload = [
            {"log_id": "log_001", "log": "ERROR: database connection failed on primary host"},
            {"log_id": "log_002", "log": "CRITICAL: memory limit exceeded in worker process"},
        ]
        response = client.post("/analyze/batch", json=payload)
        assert response.status_code == 200
        assert response.json()["batch_size"] == 2

    def test_batch_exceeds_limit_returns_400(self):
        payload = [{"log_id": f"log_{i}", "log": "ERROR: something"} for i in range(21)]
        response = client.post("/analyze/batch", json=payload)
        assert response.status_code == 400

    @patch("api.main.run_pipeline", return_value=MOCK_PIPELINE_RESULT)
    @patch("api.main.score_result", return_value={"aggregate_score": 0.9, "passed": True})
    def test_batch_returns_results_list(self, mock_score, mock_pipeline):
        payload = [{"log_id": "log_001", "log": "ERROR: timeout on database query execution"}]
        response = client.post("/analyze/batch", json=payload)
        assert "results" in response.json()
        assert len(response.json()["results"]) == 1