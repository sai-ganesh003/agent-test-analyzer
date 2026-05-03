"""
bug_report.py
Transforms LLM analysis into a structured bug report.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SEVERITY_PRIORITY = {
    "critical": "P0",
    "high": "P1",
    "medium": "P2",
    "low": "P3",
}


def generate_bug_report(log_id: str, raw_log: str, analysis: dict) -> dict:
    logger.info(f"[{log_id}] Generating bug report")

    severity = analysis.get("severity", "medium").lower()
    priority = SEVERITY_PRIORITY.get(severity, "P2")

    report = {
        "bug_id": f"BUG-{log_id.upper()}",
        "title": analysis.get("summary", "Unknown failure"),
        "priority": priority,
        "severity": severity,
        "affected_component": analysis.get("affected_component", "unknown"),
        "root_cause": analysis.get("root_cause", ""),
        "recommended_fix": analysis.get("fix", ""),
        "tags": analysis.get("tags", []),
        "confidence": analysis.get("confidence", 0.0),
        "source_log_snippet": raw_log.strip()[:500] + ("..." if len(raw_log.strip()) > 500 else ""),
        "filed_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "requires_manual_review": analysis.get("confidence", 0.0) < 0.6,
    }

    logger.info(f"[{log_id}] Bug report generated — Priority: {priority}, Severity: {severity}")
    return report