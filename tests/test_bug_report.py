import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

SAMPLE_LOG = "ERROR: DatabaseConnectionError — could not connect to postgres:5432"

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

    def test_high_confidence_no_manual_review(self):
        from pipeline.bug_report import generate_bug_report
        report = generate_bug_report("log_001", SAMPLE_LOG, MOCK_HIGH_CONF_ANALYSIS)
        assert report["requires_manual_review"] is False

    def test_bug_report_contains_required_fields(self):
        from pipeline.bug_report import generate_bug_report
        report = generate_bug_report("log_001", SAMPLE_LOG, MOCK_HIGH_CONF_ANALYSIS)
        required = ["bug_id", "title", "priority", "severity", "root_cause",
                    "recommended_fix", "confidence", "filed_at", "status"]
        for field in required:
            assert field in report, f"Missing field: {field}"

    def test_long_log_gets_truncated_in_report(self):
        from pipeline.bug_report import generate_bug_report
        long_log = "ERROR: something went wrong\n" * 100
        report = generate_bug_report("log_002", long_log, MOCK_HIGH_CONF_ANALYSIS)
        assert len(report["source_log_snippet"]) <= 503

    def test_unknown_severity_defaults_to_p2(self):
        from pipeline.bug_report import generate_bug_report
        analysis = {**MOCK_HIGH_CONF_ANALYSIS, "severity": "weird_value"}
        report = generate_bug_report("log_003", SAMPLE_LOG, analysis)
        assert report["priority"] == "P2"

    def test_bug_id_format(self):
        from pipeline.bug_report import generate_bug_report
        report = generate_bug_report("log_042", SAMPLE_LOG, MOCK_HIGH_CONF_ANALYSIS)
        assert report["bug_id"] == "BUG-LOG_042"