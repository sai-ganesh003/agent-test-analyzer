import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from logs.sample_logs import SAMPLE_LOGS
from pipeline.pipeline import run_pipeline
from eval.evaluator import run_evaluation, print_eval_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    print(f"\nRunning pipeline over {len(SAMPLE_LOGS)} logs...\n")
    pipeline_results = []

    for i, entry in enumerate(SAMPLE_LOGS):
        log_id = entry["id"]
        log_text = entry["log"]
        print(f"  Processing {log_id}...")

        if i > 0:
            print(f"    Waiting 15s to avoid rate limiting...")
            time.sleep(15)

        result = run_pipeline(log_id=log_id, log_text=log_text)
        pipeline_results.append(result)

        bug = result.get("bug_report")
        fallback = result.get("fallback")

        if bug:
            conf = bug.get("confidence", 0)
            print(f"    → [{result['status'].upper()}] {bug['bug_id']} | {bug['priority']} | conf={conf:.2f}")
        elif fallback:
            print(f"    → [UNCERTAIN] conf={fallback['confidence']:.2f} — manual review needed")
        else:
            print(f"    → [ERROR] {result.get('error', 'unknown error')}")

    eval_report = run_evaluation(pipeline_results)
    print_eval_report(eval_report)

    os.makedirs("outputs", exist_ok=True)

    with open("outputs/pipeline_results.json", "w") as f:
        json.dump(pipeline_results, f, indent=2)

    with open("outputs/eval_report.json", "w") as f:
        json.dump(eval_report, f, indent=2)

    print("Outputs saved to outputs/")


if __name__ == "__main__":
    main()