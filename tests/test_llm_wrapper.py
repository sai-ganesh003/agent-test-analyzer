import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock
import json
import urllib.error


class TestLLMWrapper:

    def test_low_confidence_detection_below_threshold(self):
        from pipeline.llm_wrapper import is_low_confidence
        assert is_low_confidence({"confidence": 0.4}) is True
        assert is_low_confidence({"confidence": 0.3}) is True
        assert is_low_confidence({"confidence": 0.0}) is True

    def test_low_confidence_detection_above_threshold(self):
        from pipeline.llm_wrapper import is_low_confidence
        assert is_low_confidence({"confidence": 0.6}) is False
        assert is_low_confidence({"confidence": 0.9}) is False
        assert is_low_confidence({"confidence": 1.0}) is False

    def test_confidence_exactly_at_threshold(self):
        from pipeline.llm_wrapper import is_low_confidence
        assert is_low_confidence({"confidence": 0.6}) is False

    def test_fallback_message_structure(self):
        from pipeline.llm_wrapper import get_fallback_message
        fb = get_fallback_message("log_001", 0.42)
        assert fb["status"] == "uncertain"
        assert fb["confidence"] == 0.42
        assert "manual review" in fb["message"].lower()
        assert fb["log_id"] == "log_001"

    def test_fallback_message_contains_threshold(self):
        from pipeline.llm_wrapper import get_fallback_message
        fb = get_fallback_message("log_002", 0.35)
        assert "0.35" in fb["message"] or "0.6" in fb["message"]

    def test_validate_schema_passes_valid_data(self):
        from pipeline.llm_wrapper import _validate_schema
        valid = {
            "root_cause": "something broke",
            "fix": "fix it this way",
            "severity": "high",
            "confidence": 0.85,
            "summary": "brief summary here",
        }
        result = _validate_schema(valid)
        assert result["confidence"] == 0.85
        assert "tags" in result
        assert "affected_component" in result

    def test_validate_schema_clamps_confidence_above_1(self):
        from pipeline.llm_wrapper import _validate_schema
        data = {
            "root_cause": "x", "fix": "y", "severity": "low",
            "confidence": 1.5, "summary": "z"
        }
        result = _validate_schema(data)
        assert result["confidence"] == 1.0

    def test_validate_schema_clamps_confidence_below_0(self):
        from pipeline.llm_wrapper import _validate_schema
        data = {
            "root_cause": "x", "fix": "y", "severity": "low",
            "confidence": -0.3, "summary": "z"
        }
        result = _validate_schema(data)
        assert result["confidence"] == 0.0

    def test_validate_schema_raises_on_missing_fields(self):
        from pipeline.llm_wrapper import _validate_schema
        incomplete = {"root_cause": "something", "confidence": 0.8}
        with pytest.raises(ValueError, match="missing required fields"):
            _validate_schema(incomplete)

    def test_validate_schema_adds_default_tags(self):
        from pipeline.llm_wrapper import _validate_schema
        data = {
            "root_cause": "x", "fix": "y", "severity": "low",
            "confidence": 0.7, "summary": "z"
        }
        result = _validate_schema(data)
        assert result["tags"] == []

    def test_validate_schema_adds_default_affected_component(self):
        from pipeline.llm_wrapper import _validate_schema
        data = {
            "root_cause": "x", "fix": "y", "severity": "low",
            "confidence": 0.7, "summary": "z"
        }
        result = _validate_schema(data)
        assert result["affected_component"] == "unknown"