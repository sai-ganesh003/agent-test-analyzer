# agent-test-analyzer

A multi-step LLM pipeline that automates error log analysis, failure triage, and bug report generation — with built-in evaluation, confidence-based fallback, and full observability.



## What This Project Does

Engineering teams waste hours manually triaging failure logs — reading stack traces, identifying root causes, writing bug reports, and routing to the right team. This project automates that entire flow using an LLM agent that reads a raw error log and returns a structured analysis with a root cause, a concrete fix, a severity rating, and a confidence score.

If the model isn't confident enough in its answer, the pipeline flags the result for manual review instead of filing a bad bug report. Every step is logged so failures are visible and debuggable.



## How the Pipeline Works

When you pass in a raw error log, the pipeline runs four steps in sequence.

First, it ingests and validates the log. Second, it calls the Gemini LLM and enforces a strict JSON output schema — if the model returns anything other than valid JSON, the call is retried up to two more times. Third, it checks the confidence score returned by the model. If confidence is below 0.6, it generates a fallback message and marks the result for manual review instead of proceeding blindly. Fourth, it generates a structured bug report with a priority level mapped from the severity — critical maps to P0, high to P1, medium to P2, and low to P3.

The whole pipeline is wrapped in error handling at every step. If the LLM call fails, the pipeline records the error and returns a clean result with status set to error. It never crashes silently.



## How Evaluation Works

After the pipeline runs, every result is scored across five dimensions — whether the root cause is present and specific, whether the fix is present and actionable, whether confidence is above 0.5, whether severity is a valid value, and whether a summary is present. Each dimension scores 0 or 1. The aggregate score is the mean. A result passes if the aggregate is 0.6 or above.

On a real run across 10 logs, 7 passed with a mean score of 0.7. The 3 failures were caused by API rate limiting and response truncation, not logic errors — the pipeline caught and logged all of them correctly.



## Failure Handling

The pipeline handles several failure modes explicitly. If the LLM returns malformed JSON, it retries with a delay. If required fields are missing from the response, schema validation raises an error before the pipeline continues. If confidence is too low, a fallback message is generated and the bug report is flagged for manual review. If the API returns a rate limit error, the wrapper waits and retries with exponential backoff. None of these failures crash the pipeline — they are all caught, logged with the log ID, and surfaced in the result.



## Known Limitations

The pipeline does single-turn analysis only. Complex failures involving multiple interacting systems might benefit from a multi-turn reasoning approach. On ambiguous logs with minimal stack trace information, the model may generate plausible but incorrect root causes — the confidence threshold is the primary mitigation for this. The evaluation scoring uses word count thresholds as proxies for quality, which is a heuristic and not ground truth.



## Setup

Clone the repo and create a virtual environment using Python 3.11. Install dependencies with pip install -r requirements.txt. Create a .env file in the root with your Google API key as GOOGLE_API_KEY. Then run python run_all.py to execute the pipeline across all 10 sample logs. Run pytest tests/ -v to run the 14 unit tests — these are fully mocked and do not require an API key.



## Tech Stack

Python 3.11, Google Gemini 2.5 Flash, FastAPI, pytest, and Python's built-in urllib for HTTP calls with no external HTTP library required.



## Author

Kolusu Sai Ganesh — github.com/sai-ganesh003