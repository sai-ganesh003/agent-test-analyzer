# agent-test-analyzer

I wanted to understand how LLM pipelines actually fail in production — not just how to call an API, but what happens when the model returns garbage, when confidence is too low to trust, and how you measure whether the output is any good. So I built this.

It takes a raw error log, calls an LLM, enforces a strict JSON output schema, checks confidence, and generates a bug report. Then it scores every result and prints an evaluation report.



## What it does

You give it an error log. It runs four steps — ingest, analyze, confidence check, generate bug report. If the model isn't confident enough, it flags the result for manual review instead of filing a bad report. Every step is logged independently so you can trace exactly what happened and where it failed.



## The core design decision

LLM output is treated as unreliable input, not trusted output. Every response goes through schema validation before anything downstream touches it. If the model returns malformed JSON, it gets retried. If required fields are missing, the pipeline raises before continuing. If confidence is below threshold, a fallback is generated instead of a bad bug report.

This is the part most demo projects skip — designing for partial failure rather than the happy path.



## How evaluation works

Each result is scored on five binary dimensions.

Root cause is scored as present if it names a specific system component and failure mode — not just "database error" but what specifically failed and why. Fix is scored as actionable if it contains a concrete change rather than generic advice like "investigate further." Confidence is scored as acceptable if it exceeds 0.5. Severity must be one of four valid values. Summary must be non-empty.

Aggregate score is the mean of these five dimensions. A result passes if the aggregate is 0.6 or above.

I want to be honest about what this is — it is heuristic scoring, not ground truth. Word count thresholds are a blunt instrument. The confidence score is what the model self-reports, which I treat as a signal rather than a fact. A production eval would need human-labeled reference answers and probably a second model acting as judge. I noted all of this in the code.



## Actual results

10 logs processed. 70% produced structurally valid, actionable reports under current heuristics. Primary failure modes were retry exhaustion from API rate limiting and response truncation due to token limits — not logic errors in the pipeline. All three failures were caught, logged with their log ID, and surfaced in the eval report without crashing the run.



## What the observability looks like

Every pipeline step logs its status, duration, and key values independently. If the LLM call fails, that is recorded in the steps dict with the error message. If confidence is low, that is recorded with the actual confidence value. If bug report generation fails separately from the LLM call, that is also recorded independently. The result always comes back with a status field — success, uncertain, partial, or error — so the caller always knows what happened.



## Setup

Clone the repo. Create a virtual environment with Python 3.11. Install dependencies from requirements.txt. Add a .env file in the root with your Google API key as GOOGLE_API_KEY. Run python run_all.py to process all logs. Run pytest tests/ -v to run the 14 unit tests — fully mocked, no API key needed.



## Stack

Python 3.11, Google Gemini 2.5 Flash, FastAPI, pytest, urllib.


## Author 

Kolusu Sai Ganesh — github.com/sai-ganesh003