"""
evaluator.py
Evaluation system for agent output quality.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

VALID_SEVERITIES = {"critical", "high", "medium", "low"}
MIN_CONFIDENCE = 0.5


def score_result(result: dict) -> dict:
    log_id = result.get("log_id", "unknown")
    llm_step = result.get("steps", {}).get("llm_analysis", {})
    analysis = llm_step.get("raw_output", {})

    if not analysis:
        logger.warning(f"[{log_id}] No LLM output found — scoring as 0")
        return _zero_score(log_id, reason="pipeline_error")

    root_cause = analysis.get("root_cause", "")
    fix = analysis.get("fix", "")
    confidence = analysis.get("confidence", 0.0)
    severity = analysis.get("severity", "")
    summary = analysis.get("summary", "")

    scores = {
        "log_id": log_id,
        "dimensions": {
            "root_cause_present": int(bool(root_cause) and len(root_cause.split()) > 10),
            "fix_present": int(bool(fix) and len(fix.split()) > 8),
            "confidence_ok": int(confidence >= MIN_CONFIDENCE),
            "severity_valid": int(severity.lower() in VALID_SEVERITIES),
            "summary_present": int(bool(summary) and len(summary) > 5),
        },
        "confidence": confidence,
        "severity": severity,
        "pipeline_status": result.get("status", "unknown"),
    }

    dim_values = list(scores["dimensions"].values())
    scores["aggregate_score"] = round(sum(dim_values) / len(dim_values), 2)
    scores["passed"] = scores["aggregate_score"] >= 0.6

    logger.info(f"[{log_id}] Score: {scores['aggregate_score']} | Passed: {scores['passed']}")
    return scores


def run_evaluation(pipeline_results: list[dict]) -> dict:
    logger.info(f"Running evaluation over {len(pipeline_results)} results")

    individual_scores = [score_result(r) for r in pipeline_results]

    passed = [s for s in individual_scores if s["passed"]]
    failed = [s for s in individual_scores if not s["passed"]]
    error_results = [s for s in individual_scores if s["pipeline_status"] == "error"]

    aggregate_scores = [s["aggregate_score"] for s in individual_scores]
    mean_score = round(sum(aggregate_scores) / len(aggregate_scores), 3) if aggregate_scores else 0.0

    dim_names = ["root_cause_present", "fix_present", "confidence_ok", "severity_valid", "summary_present"]
    dim_pass_rates = {}
    for dim in dim_names:
        values = [s["dimensions"].get(dim, 0) for s in individual_scores if "dimensions" in s]
        dim_pass_rates[dim] = round(sum(values) / len(values), 2) if values else 0.0

    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(individual_scores),
        "passed": len(passed),
        "failed": len(failed),
        "errors": len(error_results),
        "pass_rate": round(len(passed) / len(individual_scores), 2) if individual_scores else 0.0,
        "mean_aggregate_score": mean_score,
        "dimension_pass_rates": dim_pass_rates,
        "individual_scores": individual_scores,
        "failed_log_ids": [s["log_id"] for s in failed],
    }

    logger.info(f"Evaluation complete — Pass rate: {report['pass_rate']} | Mean score: {mean_score}")
    return report


def print_eval_report(report: dict):
    print("\n" + "═" * 60)
    print("  AGENT EVALUATION REPORT")
    print("═" * 60)
    print(f"  Evaluated at : {report['evaluated_at']}")
    print(f"  Total logs   : {report['total']}")
    print(f"  Passed       : {report['passed']}  ✓")
    print(f"  Failed       : {report['failed']}  ✗")
    print(f"  Errors       : {report['errors']}  ⚠")
    print(f"  Pass rate    : {report['pass_rate'] * 100:.0f}%")
    print(f"  Mean score   : {report['mean_aggregate_score']}")
    print()
    print("  Dimension Pass Rates:")
    for dim, rate in report["dimension_pass_rates"].items():
        bar = "█" * int(rate * 20) + "░" * (20 - int(rate * 20))
        print(f"    {dim:<25} {bar} {rate * 100:.0f}%")
    print()
    print("  Per-Log Results:")
    for s in report["individual_scores"]:
        status = "✓" if s["passed"] else "✗"
        conf = s.get("confidence", 0)
        print(f"    {status} {s['log_id']:<12} score={s['aggregate_score']}  conf={conf:.2f}  status={s['pipeline_status']}")
    if report["failed_log_ids"]:
        print(f"\n  Failed logs: {', '.join(report['failed_log_ids'])}")
    print("═" * 60 + "\n")


def _zero_score(log_id: str, reason: str = "unknown") -> dict:
    return {
        "log_id": log_id,
        "dimensions": {d: 0 for d in ["root_cause_present", "fix_present", "confidence_ok", "severity_valid", "summary_present"]},
        "confidence": 0.0,
        "severity": "unknown",
        "pipeline_status": "error",
        "aggregate_score": 0.0,
        "passed": False,
        "reason": reason,
    }