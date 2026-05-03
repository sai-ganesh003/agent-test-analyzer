"""
main.py — FastAPI application
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pipeline.pipeline import run_pipeline
from eval.evaluator import score_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agent Test Analyzer",
    description="Multi-step LLM pipeline for automated log analysis, failure triage, and bug filing.",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    log_id: str = Field(..., example="log_001")
    log: str = Field(..., example="ERROR: DatabaseConnectionError...")


@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    logger.info(f"POST /analyze — log_id={request.log_id}")

    if not request.log.strip():
        raise HTTPException(status_code=400, detail="Log text cannot be empty")

    try:
        result = run_pipeline(log_id=request.log_id, log_text=request.log)
        result["eval_score"] = score_result(result)
        return result
    except Exception as e:
        logger.error(f"[{request.log_id}] Unhandled error in /analyze: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.post("/analyze/batch")
def analyze_batch(requests: list[AnalyzeRequest]):
    if len(requests) > 20:
        raise HTTPException(status_code=400, detail="Batch size limit is 20 logs")

    results = []
    for req in requests:
        result = run_pipeline(log_id=req.log_id, log_text=req.log)
        result["eval_score"] = score_result(result)
        results.append(result)

    return {"batch_size": len(results), "results": results}