"""
pipeline.py
Orchestrates the full log analysis pipeline:
  Step 1: Receive raw log
  Step 2: Call LLM for analysis (with JSON enforcement)
  Step 3: Apply confidence threshold + fallback
  Step 4: Generate bug report
  Step 5: Return structured result with full observability data
"""

import logging
import time
from datetime import datetime, timezone

from pipeline.llm_wrapper import call_llm, is_low_confidence, get_fallback_message
from pipeline.bug_report import generate_bug_report

logger = logging.getLogger(__name__)


def run_pipeline(log_id: str, log_text: str) -> dict:
    pipeline_start = time.time()
    result = {
        "log_id": log_id,
        "pipeline_start": datetime.now(timezone.utc).isoformat(),
        "steps": {},
        "status": "success",
        "bug_report": None,
        "fallback": None,
        "error": None,
    }

    logger.info(f"[{log_id}] ━━ Step 1: Log ingestion")
    result["steps"]["ingestion"] = {
        "status": "ok",
        "log_length": len(log_text),
        "log_preview": log_text.strip()[:200],
    }

    logger.info(f"[{log_id}] ━━ Step 2: LLM analysis")
    step2_start = time.time()
    try:
        analysis = call_llm(log_text)
        step2_duration = round(time.time() - step2_start, 2)
        logger.info(f"[{log_id}] LLM analysis complete in {step2_duration}s — confidence: {analysis['confidence']:.2f}")
        result["steps"]["llm_analysis"] = {
            "status": "ok",
            "duration_s": step2_duration,
            "confidence": analysis["confidence"],
            "severity": analysis["severity"],
            "raw_output": analysis,
        }
    except Exception as e:
        logger.error(f"[{log_id}] LLM analysis failed: {e}")
        result["steps"]["llm_analysis"] = {"status": "error", "error": str(e)}
        result["status"] = "error"
        result["error"] = f"LLM analysis failed: {e}"
        result["pipeline_duration_s"] = round(time.time() - pipeline_start, 2)
        return result

    logger.info(f"[{log_id}] ━━ Step 3: Confidence threshold check")
    if is_low_confidence(analysis):
        logger.warning(f"[{log_id}] Low confidence ({analysis['confidence']:.2f}) — flagging for manual review")
        fallback = get_fallback_message(log_id, analysis["confidence"])
        result["steps"]["confidence_check"] = {"status": "low_confidence", "confidence": analysis["confidence"]}
        result["fallback"] = fallback
        result["status"] = "uncertain"
    else:
        result["steps"]["confidence_check"] = {"status": "ok", "confidence": analysis["confidence"]}

    logger.info(f"[{log_id}] ━━ Step 4: Bug report generation")
    try:
        bug_report = generate_bug_report(log_id, log_text, analysis)
        result["bug_report"] = bug_report
        result["steps"]["bug_report"] = {"status": "ok", "bug_id": bug_report["bug_id"]}
        logger.info(f"[{log_id}] Bug report filed: {bug_report['bug_id']} [{bug_report['priority']}]")
    except Exception as e:
        logger.error(f"[{log_id}] Bug report generation failed: {e}")
        result["steps"]["bug_report"] = {"status": "error", "error": str(e)}
        result["status"] = "partial"

    result["pipeline_duration_s"] = round(time.time() - pipeline_start, 2)
    logger.info(f"[{log_id}] ━━ Pipeline complete in {result['pipeline_duration_s']}s — status: {result['status']}")
    return result