# agent-test-analyzer

Most portfolio projects call an API and print whatever comes back. I wanted to build something that treated the AI's output as something that could fail — because in production, it does.

This started as a question: what actually happens when an LLM pipeline breaks? Not the happy path where the model returns perfect JSON every time, but the real cases — malformed output, low confidence, rate limits, missing fields. I built this to find out.

It takes a raw error log, runs it through a four-step pipeline, and produces a structured bug report. The interesting part isn't the bug report — it's everything the pipeline does before trusting the output enough to file one.

## What it does

You give it an error log. The pipeline does four things:

1. Ingests the log and records its length and preview for tracing
2. Calls Gemini 2.5 Flash with a strict prompt that enforces JSON output
3. Checks the model's confidence score — if it's below threshold, the result gets flagged for manual review instead of filing a potentially wrong bug report
4. Generates a structured bug report with priority level, affected component, root cause, and recommended fix

Every step logs its status, duration, and key values independently. The result always comes back with a status field — success, uncertain, partial, or error — so the caller always knows what happened, even when something goes wrong.

## The decision that matters

LLM output is treated as unreliable input, not trusted output.

Every response goes through schema validation before anything downstream touches it. If the model returns malformed JSON, it retries. If required fields are missing, the pipeline raises before continuing. If confidence is below 0.6, a fallback is generated instead of a bad bug report.

This is the part most demo projects skip — designing for partial failure rather than the happy path. A pipeline that only works when everything goes right isn't a pipeline, it's a demo.

## How evaluation works

Each result is scored on five binary dimensions — root cause specificity, fix actionability, confidence level, severity validity, and summary presence. Aggregate score is the mean. A result passes at 0.6 or above.

I want to be honest about what this is — heuristic scoring, not ground truth. Word count thresholds are a blunt instrument. The confidence score is what the model self-reports, which I treat as a signal rather than a fact. A production eval would need human-labeled reference answers and probably a second model acting as judge. I noted all of this in the code.

## Confidence threshold ablation

The 0.6 threshold isn't arbitrary — I tested it.

Running the evaluator across thresholds from 0.3 to 0.8 shows that below 0.5 too many low quality results pass through, and above 0.7 too many valid results get flagged for manual review. 0.6 is the balance point for this dataset. Results are in `outputs/ablation_report.json`.

```bash
python ablation.py
```

## Actual results

20 logs processed across diverse failure types — database connections, memory errors, auth failures, SSL certificates, Kubernetes OOM kills, circular imports, queue overflows, and deployment failures. The pipeline handles all of them without crashing. Failures are caught, logged with their log ID, and surfaced in the eval report.

## Running it

Pipeline:
```bash
python run_all.py
```
Processes all 20 logs, prints an evaluation report, saves results to `outputs/`.

API:
```bash
python start_api.py
```
Starts the FastAPI server at `http://localhost:8000`. Three endpoints — `GET /health`, `POST /analyze`, `POST /analyze/batch` (up to 20 logs).

Live deployment: `http://13.60.2.124:8000`

Swagger UI: `http://13.60.2.124:8000/docs`

Example:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"log_id": "log_001", "log": "ERROR: DatabaseConnectionError could not connect to postgres:5432"}'
```

**Tests:**
```bash
pytest tests/ -v
```
52 tests across 5 modules — pipeline, bug report, evaluator, LLM wrapper, and API endpoints. Fully mocked, no API key needed.

## Setup

```bash
git clone https://github.com/sai-ganesh003/agent-test-analyzer.git
cd agent-test-analyzer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# add your GOOGLE_API_KEY to .env
```

Get a free API key at https://aistudio.google.com/app/apikey

## Stack

Python 3.11, Google Gemini 2.5 Flash, FastAPI, uvicorn, pydantic, pytest.

## Author

Kolusu Sai Ganesh — [github.com/sai-ganesh003](https://github.com/sai-ganesh003)