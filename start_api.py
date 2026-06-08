"""
start_api.py
Starts the FastAPI server for the Agent Test Analyzer API.

Usage:
    python start_api.py

The API will be available at:
    http://localhost:8000
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/health (Health check)
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )