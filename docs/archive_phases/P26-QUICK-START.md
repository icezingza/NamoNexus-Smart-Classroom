# P26 Quick Start — Test & Verify

## 1. Install Dependencies
```bash
cd openclaw-2026.4.5
npm install
```

Newly added:
- `bunyan` (structured JSON logging)
- `@google-cloud/logging-bunyan` (Cloud Logging transport)

## 2. Run Backend Services

### Terminal 1: Smart Classroom (NamoNexus Smart Classroom)
```bash
cd NamoNexus-Smart-Classroom/backend/namo_core
python -m uvicorn main:app --host localhost --port 8000 --reload
```

Check: `curl http://localhost:8000/health`

### Terminal 2: OpenClaw Gateway
```bash
cd openclaw-2026.4.5
npm run dev
```

Check: Logs appear in console + `logs/api_bridge.log`

## 3. Run Integration Tests

### Terminal 3: Test Suite
```bash
cd openclaw-2026.4.5

# Set environment variables
export TEST_API_BASE="http://localhost:18789"
export TEST_JWT_TOKEN="test-token"

# Run all 5 scenarios + validation + load tests
npm test -- tests/integration/p26-integration.test.ts
```

## 4. Verify Results

### Expected Output
```
PASS  tests/integration/p26-integration.test.ts

P26.4 OpenClaw → Smart Classroom Integration
  Scenario 1: Happy Path
    ✓ should return Tripitaka result for valid query within latency SLA (187ms)
    ✓ should contain valid source attribution
  Scenario 2: Cache Hit
    ✓ should return cached result for duplicate query within 2ms
  Scenario 3: Fallback with Retry
    ✓ should return 503 after exhausting retries
    ✓ should validate 503 error response structure
  Scenario 4: Source Attribution
    ✓ should attribute sources correctly
  Scenario 5: Trace ID Propagation
    ✓ should correlate trace IDs
    ✓ should include trace_id in all error responses
  Input Validation
    ✓ should reject empty query
    ✓ should reject missing user_id
    ✓ should reject invalid JSON
    ✓ should reject missing JWT
  Performance SLAs
    ✓ should maintain < 500ms p95 latency under sustained load

Tests:  14 passed
Time:   ~30s
```

## 5. Check Logs

### Local Logs (api_bridge.log)
```bash
cd openclaw-2026.4.5

# Pretty-print JSON logs
tail -f logs/api_bridge.log | jq '.'

# Filter by trace ID
cat logs/api_bridge.log | jq 'select(.trace_id=="trc_...")'

# Show latency distribution
cat logs/api_bridge.log | jq '.latency_ms' | sort -n | tail -20
```

### Log Entry Example
```json
{
  "trace_id": "trc_550e8400e29b41d4a716446655440000",
  "operation": "search-query",
  "level": "info",
  "user_id": "test_user_1",
  "query": "สัตตา คืออะไร",
  "channel": "integration-test",
  "latency_ms": 187,
  "status": 200,
  "cached": false,
  "timestamp": "2026-05-11T10:30:45.123Z"
}
```

## 6. Manual Test (Single Query)

```bash
# Terminal 4: Test a search request
curl -X POST http://localhost:18789/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "query": "กรรม คืออะไร",
    "user_id": "test_user_1",
    "channel": "integration-test"
  }' | jq '.'
```

Expected Response:
```json
{
  "answer": "กรรมหมายถึง...",
  "sources": [
    {
      "book": "DN 1: Brahmajala Sutta",
      "library": "tripitaka",
      "confidence": 0.92
    }
  ],
  "confidence": 0.92,
  "trace_id": "trc_550e8400e29b41d4a716446655440000",
  "latency_ms": 187,
  "cached": false
}
```

## 7. Verify Cache Hit

```bash
# First request (cache miss)
curl -X POST http://localhost:18789/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "query": "กรรม",
    "user_id": "cache_test",
    "channel": "integration-test"
  }' | jq '{latency_ms, cached}'
# Output: { "latency_ms": 187, "cached": false }

# Immediate repeat (cache hit)
curl -X POST http://localhost:18789/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "query": "กรรม",
    "user_id": "cache_test",
    "channel": "integration-test"
  }' | jq '{latency_ms, cached}'
# Output: { "latency_ms": 1, "cached": true }
```

## 8. Test Failure Scenario (Smart Classroom Offline)

```bash
# Stop Smart Classroom (Ctrl+C in Terminal 1)

# Try a search request
curl -X POST http://localhost:18789/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{"query": "test", "user_id": "test", "channel": "test"}'

# Expected response (after 3 retries, ~450ms)
# {
#   "error": "Smart Classroom service unavailable (3 retries exhausted)",
#   "trace_id": "trc_...",
#   "retry_count": 3,
#   "last_attempt_ms": 450
# }

# Restart Smart Classroom
```

## 9. Monitor Performance

```bash
# Watch latency percentiles
watch -n 2 'cat logs/api_bridge.log | jq ".latency_ms" | sort -n | awk "{arr[NR]=\$1} END {n=length(arr); p50=arr[int(n*0.5)]; p95=arr[int(n*0.95)]; print \"p50:\", p50, \"ms\"; print \"p95:\", p95, \"ms\"}"'
```

## 10. Deploy to Cloud Run (After Testing)

```bash
# Build Docker image
docker build -t namo-gateway:latest .

# Push to GCP Artifact Registry
gcloud builds submit --tag gcr.io/namo-classroom/namo-gateway:latest

# Deploy to Cloud Run
gcloud run deploy namo-gateway \
  --image gcr.io/namo-classroom/namo-gateway:latest \
  --region asia-southeast1 \
  --set-env-vars LOG_LEVEL=info,GCP_PROJECT_ID=namo-classroom \
  --port 8000

# Verify
curl https://namo-gateway-xxx.a.run.app/health
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=namo-gateway" --limit 5
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ECONNREFUSED :8000` | Smart Classroom not running — start in Terminal 1 |
| `ECONNREFUSED :18789` | OpenClaw not running — start in Terminal 2 |
| `401 Unauthorized` | Missing Bearer token in Authorization header |
| `400 Bad Request` | Missing query or user_id field |
| `503 Service Unavailable` | Smart Classroom offline, retried 3x — restart service |
| Logs not appearing | Check `logs/api_bridge.log` exists; verify `LOG_LEVEL=info` |
| Cache not working | Check TTL (5 min) hasn't expired; verify same `user_id` used |

---

## Success Criteria

✅ All 14 tests PASS  
✅ p95 latency < 500ms sustained  
✅ Cache hit latency < 2ms  
✅ 3 retries work on timeout  
✅ Trace IDs visible in logs  
✅ Sources labeled correctly (tripitaka / global_library)  

**Once complete:** Ready to move to P27 (Telegram integration)

---

*Last Updated: 2026-05-11 | P26 Integration Sprint*
