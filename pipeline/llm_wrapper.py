"""
llm_wrapper.py
Calls Google Gemini API using only Python built-ins (no external packages).
Handles retries, schema validation, and confidence thresholds.
"""

import json
import logging
import os
import time
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"root_cause", "fix", "severity", "confidence", "summary"}
CONFIDENCE_THRESHOLD = 0.6
API_KEY = os.getenv("GOOGLE_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

SYSTEM_PROMPT = """You are an expert software reliability engineer specializing in log analysis and failure triage.

Analyze the provided error log and respond ONLY with a valid JSON object — no markdown, no explanation, no backticks.

Required JSON schema:
{
  "root_cause": "string — the specific technical reason this failure occurred",
  "fix": "string — concrete actionable fix (code change, config update, infra action)",
  "severity": "critical | high | medium | low",
  "confidence": float between 0.0 and 1.0,
  "summary": "string — one sentence human-readable summary",
  "affected_component": "string — the service/module/file most directly responsible",
  "tags": ["array", "of", "relevant", "tags"]
}

Rules:
- confidence reflects how certain you are given only this log. If the log is ambiguous, set confidence lower.
- fix must be specific, not generic (e.g. "add index on created_at column" not "fix the database").
- Do not include any text outside the JSON object.
"""


def call_llm(log_text: str, retries: int = 2) -> dict:
    attempt = 0
    last_error = None

    while attempt <= retries:
        attempt += 1
        logger.info(f"LLM call attempt {attempt}/{retries + 1}")

        try:
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": SYSTEM_PROMPT + f"\n\nAnalyze this error log:\n\n{log_text.strip()}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1000,
                }
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                raw_response = json.loads(response.read().decode("utf-8"))

            raw_text = raw_response["candidates"][0]["content"]["parts"][0]["text"].strip()
            logger.debug(f"Raw LLM output: {raw_text}")

            # Strip accidental markdown fences
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
                raw_text = raw_text.strip()

            result = json.loads(raw_text)
            validated = _validate_schema(result)
            return validated

        except json.JSONDecodeError as e:
            last_error = f"JSON parse failed: {e}"
            logger.warning(f"Attempt {attempt} — {last_error}")
            if attempt <= retries:
                time.sleep(5)

        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * attempt
                logger.warning(f"Rate limited. Waiting {wait}s before retry...")
                time.sleep(wait)
                last_error = f"Rate limited (429)"
            else:
                last_error = f"HTTP error: {e.code} {e.reason}"
                logger.error(last_error)
                raise

        except urllib.error.URLError as e:
            last_error = f"URL error: {e.reason}"
            logger.error(last_error)
            raise

    raise ValueError(f"LLM failed after {retries + 1} attempts. Last error: {last_error}")


def _validate_schema(data: dict) -> dict:
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        raise ValueError(f"LLM response missing required fields: {missing}")

    data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))

    if "tags" not in data:
        data["tags"] = []

    if "affected_component" not in data:
        data["affected_component"] = "unknown"

    return data


def is_low_confidence(result: dict) -> bool:
    return result.get("confidence", 0) < CONFIDENCE_THRESHOLD


def get_fallback_message(log_id: str, confidence: float) -> dict:
    return {
        "log_id": log_id,
        "status": "uncertain",
        "message": (
            f"Analysis confidence ({confidence:.2f}) is below threshold ({CONFIDENCE_THRESHOLD}). "
            "Manual review recommended. The log may be incomplete, ambiguous, or involve "
            "multiple interacting failure modes."
        ),
        "confidence": confidence,
    }