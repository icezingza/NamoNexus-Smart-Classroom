# P26.3: Cloud Logging Integration for OpenClaw Gateway

## Overview
Structured logging with automatic shipment to GCP Cloud Logging on Cloud Run. Logs include trace IDs for correlation across OpenClaw → Smart Classroom pipeline.

## Architecture

```text
OpenClaw :18789 (Node.js)
  ↓
Bunyan Logger (structured JSON)
  ├─ stdout (Cloud Run default capture)
  ├─ logs/api_bridge.log (local dev only)
  └─ Cloud Logging Transport (production only, auto-detected via K_SERVICE env)
        ↓
  GCP Cloud Logging (Dashboard + Alerts)
        ↓
  Trace ID Correlation (trace_id in every log entry)
```

## Setup Steps

### 1. Dependencies (Already Added to package.json)
```json
{
  "bunyan": "^1.8.15",
  "@google-cloud/logging-bunyan": "^5.3.0"
}
```

Install:
```bash
npm install
```

### 2. Logger Configuration (logger.ts Updated)

The logger automatically detects Cloud Run:
- **Local Development:** Logs to stdout + `logs/api_bridge.log`
- **Cloud Run:** Logs to stdout + Cloud Logging transport (detected via `K_SERVICE` or `CLOUD_RUN_JOB_NAME` env)

No configuration file needed — environment detection is automatic.

### 3. Environment Variables

Set on Cloud Run deployment:

| Variable | Value | Purpose |
|---|---|---|
| `LOG_LEVEL` | `info` (default) | Bunyan log level (debug, info, warn, error) |
| `GCP_PROJECT_ID` | `namo-classroom` | GCP project for Cloud Logging |
| `NODE_ENV` | `production` | Activates Cloud Logging transport |

### 4. Dockerfile (No Changes Needed)

Cloud Run automatically captures stdout/stderr. Our logger writes JSON to stdout → Cloud Logging.

### 5. Log Schema

Every log entry includes:
```json
{
  "trace_id": "trc_550e8400e29b41d4a716446655440000",
  "operation": "search-query",
  "level": "info",
  "user_id": "tg_123456",
  "query": "กรรม คืออะไร",
  "channel": "telegram",
  "latency_ms": 187,
  "status": 200,
  "cached": false,
  "timestamp": "2026-05-11T10:30:45.123Z"
}
```

## Trace ID Correlation

### OpenClaw Side (Local)
```bash
# View logs with trace ID
cat logs/api_bridge.log | jq '.trace_id' | sort | uniq -c

# Filter by specific trace
cat logs/api_bridge.log | jq 'select(.trace_id=="trc_550e8400e29b41d4a716446655440000")'
```

### Cloud Run Side
```bash
# Query Cloud Logging for specific trace
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.trace_id=trc_550e8400e29b41d4a716446655440000" --limit 10

# Follow logs with latency metrics
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.operation=search-query" --limit 20 | jq '.jsonPayload | {trace_id, latency_ms, status}'
```

## Performance Metrics in Cloud Logging

### Query: Latency Distribution (p50, p95, p99)
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND jsonPayload.operation=search-query" \
  --format='table(jsonPayload.latency_ms)' \
  --limit 1000 | \
  awk '{print $1}' | \
  sort -n | \
  awk '{
    arr[NR]=$1; 
    sum+=$1
  } 
  END {
    n=length(arr); 
    p50=arr[int(n*0.5)]; 
    p95=arr[int(n*0.95)]; 
    p99=arr[int(n*0.99)]; 
    print "p50:", p50, "ms"; 
    print "p95:", p95, "ms"; 
    print "p99:", p99, "ms"; 
    print "avg:", int(sum/n), "ms"
  }'
```

### Query: Error Rate
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND jsonPayload.level=ERROR" \
  --format='table(timestamp, jsonPayload.operation, jsonPayload.status, jsonPayload.error)' \
  --limit 100
```

### Query: Cache Hit Rate
```bash
gcloud logging read \
  "resource.type=cloud_run_revision AND jsonPayload.operation=search-query" \
  --format='table(jsonPayload.cached)' \
  --limit 1000 | \
  awk '{if ($1=="true") hits++; total++} END {print "Cache hit rate:", int(hits*100/total) "%"}'
```

## Alerting Policy (GCP Console)

Create alert for high latency:
```
Condition:
  Resource: Cloud Run Revision
  Metric: cloud_run_revision.request_latencies (p95)
  Threshold: 500 ms
  Duration: 5 minutes

Notification: Send to ops@namonexus.com
```

## Local Development (No Cloud Logging Needed)

Run locally without Cloud Run environment:
```bash
npm run dev
```

Logs appear in:
- Terminal: `[INFO] [trc_...] search-query: {...}`
- File: `logs/api_bridge.log` (raw JSON, one per line)

```bash
tail -f logs/api_bridge.log | jq .
```

## Deployment Checklist

- [ ] Run `npm install` to fetch bunyan + @google-cloud/logging-bunyan
- [ ] Test locally: `npm run dev` → check `logs/api_bridge.log`
- [ ] Deploy to Cloud Run: `gcloud run deploy namo-gateway --source .`
- [ ] Verify logs in Cloud Logging: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=namo-gateway" --limit 5`
- [ ] Test trace correlation: Send request, check trace_id in both OpenClaw (local) + Smart Classroom (Cloud Run) logs
- [ ] Monitor p95 latency: Use latency query above
- [ ] Set up alerting policy for latency > 500ms

## Troubleshooting

**Logs not appearing in Cloud Logging:**
- Check: `K_SERVICE` or `CLOUD_RUN_JOB_NAME` env vars set on Cloud Run
- Verify: Service account has `logging.logEntries.create` permission
- Test: `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=namo-gateway" --limit 1`

**High latency spikes:**
- Check: Trace ID in logs → correlate with Smart Classroom :8000/search latency
- Verify: Cache hit rate (should be > 50% after warm-up)
- Review: Retry attempts (look for `retry-attempt` entries)

**Cloud Logging quota exceeded:**
- Reduce `LOG_LEVEL` to `warn` (skip INFO entries)
- Filter debug logs: set `NODE_ENV=production` before building Docker image
- Archive old logs: Use BigQuery export on Cloud Logging

---

**P26.3 Status:** ✅ Complete
- [x] logger.ts updated with bunyan + Cloud Logging transport
- [x] package.json updated with bunyan dependencies
- [x] Environment auto-detection (local vs Cloud Run)
- [x] Trace ID correlation ready
- [x] Cloud Logging queries documented

**Next:** P26.4 — Execute integration tests against running services
