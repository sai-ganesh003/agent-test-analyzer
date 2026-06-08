"""
config.py
Central configuration for pipeline constants.
"""

# Confidence threshold below which results are flagged for manual review
CONFIDENCE_THRESHOLD = 0.6

# Minimum confidence for eval scoring to pass the confidence dimension
EVAL_MIN_CONFIDENCE = 0.5

# Maximum batch size for /analyze/batch endpoint
MAX_BATCH_SIZE = 20

# LLM retry attempts
LLM_RETRY_COUNT = 2

# LLM request timeout in seconds
LLM_TIMEOUT = 30

# LLM temperature
LLM_TEMPERATURE = 0.2

# LLM max output tokens
LLM_MAX_TOKENS = 1000