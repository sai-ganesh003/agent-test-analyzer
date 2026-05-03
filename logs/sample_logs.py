SAMPLE_LOGS = [
    {
        "id": "log_001",
        "log": """
ERROR 2026-04-28 14:23:11 [worker-3] Task failed: DatabaseConnectionError
  File "app/tasks/sync.py", line 87, in run_sync
    conn = db.connect(timeout=5)
  File "lib/db.py", line 42, in connect
    raise DatabaseConnectionError(f"Could not connect to {self.host}:{self.port}")
DatabaseConnectionError: Could not connect to postgres-primary:5432
Retries exhausted (3/3). Task aborted.
"""
    },
    {
        "id": "log_002",
        "log": """
CRITICAL 2026-04-29 09:11:02 [api-server] Unhandled exception in request handler
  File "api/routes/upload.py", line 134, in handle_upload
    result = parser.parse(file.read())
  File "lib/parser.py", line 78, in parse
    chunks = self._split(content, max_tokens=512)
  File "lib/parser.py", line 91, in _split
    raise MemoryError("Cannot allocate buffer: file size 847MB exceeds limit 500MB")
MemoryError: Cannot allocate buffer: file size 847MB exceeds limit 500MB
Request ID: req-9f3a2c. User: uid-4421. Status: 500.
"""
    },
    {
        "id": "log_003",
        "log": """
ERROR 2026-04-29 11:45:33 [celery-worker-1] Task timed out: generate_embeddings
  Task ID: task-abc123
  File "workers/embedding.py", line 56, in generate_embeddings
    vectors = model.encode(batch, timeout=30)
celery.exceptions.SoftTimeLimitExceeded: Task exceeded soft time limit (30s)
Batch size at failure: 256 documents. Memory usage: 91%.
"""
    },
    {
        "id": "log_004",
        "log": """
ERROR 2026-04-30 03:22:17 [scheduler] Cron job failed: nightly_report
  File "jobs/report.py", line 201, in build_report
    data = fetch_metrics(start=yesterday, end=today)
  File "lib/metrics.py", line 67, in fetch_metrics
    return client.query(sql, params)
  File "lib/db.py", line 110, in query
    raise QueryTimeoutError("Query exceeded 60s limit")
QueryTimeoutError: Query exceeded 60s limit
Query: SELECT * FROM events WHERE created_at BETWEEN ... (no index on created_at)
"""
    },
    {
        "id": "log_005",
        "log": """
ERROR 2026-04-30 16:08:54 [auth-service] JWT validation failed repeatedly
  File "auth/middleware.py", line 33, in validate_token
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
jwt.exceptions.InvalidSignatureError: Signature verification failed
Affected requests: 1,847 in last 10 minutes. All from region: ap-south-1.
Possible cause: SECRET_KEY rotation not propagated to ap-south-1 pods.
"""
    },
    {
        "id": "log_006",
        "log": """
WARNING 2026-05-01 08:30:01 [cache-layer] Redis connection pool exhausted
  File "lib/cache.py", line 55, in get
    conn = pool.get_connection(timeout=1.0)
redis.exceptions.ConnectionError: No connections available in pool (max=50)
Active connections: 50/50. Waiting queue: 143 requests.
Upstream cause: Redis CPU at 98% due to KEYS * scan in admin dashboard.
"""
    },
    {
        "id": "log_007",
        "log": """
ERROR 2026-05-01 14:17:39 [ml-pipeline] Model inference returned NaN outputs
  File "ml/inference.py", line 88, in predict
    output = model(inputs)
  File "ml/model.py", line 144, in forward
    logits = self.head(features / self.temperature)
RuntimeWarning: invalid value encountered in true_divide (temperature=0.0)
All predictions for batch batch-7712 are NaN. Downstream scoring skipped.
"""
    },
    {
        "id": "log_008",
        "log": """
CRITICAL 2026-05-02 00:05:12 [storage-service] Disk quota exceeded on /var/data
  File "storage/writer.py", line 29, in write_chunk
    f.write(data)
OSError: [Errno 28] No space left on device: '/var/data/uploads/tmp_8842.bin'
Available: 0 bytes. Used: 500GB/500GB.
Temp files older than 7 days not cleaned: 120GB accumulated in /var/data/uploads/.
"""
    },
    {
        "id": "log_009",
        "log": """
ERROR 2026-05-02 10:44:08 [api-gateway] Rate limit bypass detected
  File "gateway/ratelimit.py", line 77, in check_limit
    count = redis.incr(f"rl:{ip}:{window}")
KeyError: 'x-forwarded-for' header missing — IP extracted from socket instead
IP: 10.0.0.1 (internal load balancer). Effective rate limit: disabled for all proxied traffic.
Requests from external IPs effectively unlimited for past 3 hours.
"""
    },
    {
        "id": "log_010",
        "log": """
ERROR 2026-05-03 07:55:29 [data-pipeline] Schema mismatch during ETL load
  File "etl/loader.py", line 113, in load_batch
    cursor.executemany(INSERT_SQL, rows)
psycopg2.errors.NotNullViolation: null value in column "user_id" violates not-null constraint
Upstream producer changed schema: field 'uid' renamed to 'user_id' without migration.
Failed rows: 14,302. Pipeline halted.
"""
    },
]