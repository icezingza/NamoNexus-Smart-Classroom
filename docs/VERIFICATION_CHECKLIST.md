# ✅ Lazy-Loading Implementation Verification Checklist
**Date:** 2026-04-21 | **Status:** Ready for Testing

---

## 📋 Pre-Test Checklist

- [ ] Lazy-loading applied to `backend/namo_core/services/orchestrator.py`
- [ ] All old Python processes killed (RAM cleanup)
- [ ] `.pid` file removed
- [ ] Backend ready to start fresh

---

## 🚀 Step 1: Start Fresh Backend

```powershell
# Remove old PID
rm .pid

# Start backend with PID tracking
powershell -File 'scripts/namo_start_backend.ps1'

# Wait 5-10 seconds for startup
Start-Sleep -Seconds 10

# Verify backend is running
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**Expected outcome:**
- ✅ Backend starts instantly (no model loading yet)
- ✅ `/health` responds within 0.5 seconds
- ✅ RAM usage: 50-80MB

---

## 🧪 Step 2: Run Enhanced Stress Test V2

This test specifically tracks **TTFB (Time To First Byte)** to verify lazy-loading:

```powershell
# Run with 5 concurrent workers, 30 requests
powershell -File 'scripts/run_stress_test.ps1' -Workers 5 -Requests 30
# OR use the new V2 test directly:
python tests/test_orchestrator_stress_v2.py 5 30
```

**What to watch for:**
```
Request   0: TTFB=22.45s | Total=22.45s  (FIRST - triggers model loading)
Request   1: TTFB= 2.15s | Total= 2.15s  (cached models now)
Request   2: TTFB= 1.98s | Total= 1.98s  (fast)
Request   3: TTFB= 2.12s | Total= 2.12s  (fast)
...
Request  29: TTFB= 2.05s | Total= 2.05s  (stable)
```

---

## 📊 Step 3: Verify Expected Results

### Success Rate Check
```
✅ Expected: 80-100% success rate
   Why: Lazy loading spreads model loading over time
   
❌ If < 50%: Something still wrong, check logs
   type logs\watchdog.log
   Check backend stdout for errors
```

### Response Time Pattern (TTFB Analysis)

**Expected pattern:**
```
Slow Phase (Request 0-1):    ~20-25 seconds (model loading)
Fast Phase (Request 2-30):   ~2-4 seconds   (cached)

Time Profile:
├─ First request:  22.5s (Reasoner 500MB + Emotion 50MB loading)
├─ Request 1-3:    2-5s  (Models in RAM, minor loading)
└─ Request 4+:     1.5-3s (All models cached, stable)
```

**Success Metrics:**
- [ ] First request: 15-25 seconds (model loading)
- [ ] Requests 2-5: 2-5 seconds (models cached)
- [ ] Requests 6+: 1.5-3 seconds (stable)
- [ ] Success rate: 80-100%

---

## 🔍 Step 4: RAM Usage Verification

Check memory efficiency:

```powershell
# During stress test, check RAM in separate PowerShell:
while($true) { 
    Get-Process python | Select-Object Id, @{Name='RAM_MB';Expression={[math]::Round($_.WorkingSet64/1MB,0)}}
    Start-Sleep -Seconds 5
}
```

**Expected RAM pattern:**
```
Before test:  50-80 MB
During test:  200-400 MB (models loading)
Peak:         400-600 MB (should NOT exceed 700MB)
After test:   ~500 MB (models stay in memory - good)

✅ If peak < 700MB: Lazy-loading is working!
❌ If peak > 900MB: Original memory leak still present
```

---

## 📋 Step 5: Analyze Stress Test Report

After test completes, examine the report:

```powershell
type tests/stress_test_report_v2.json | head -100
```

**Look for:**
```json
{
  "summary": {
    "total_requests": 30,
    "successful": 28,           ← Should be ≥24 (80%)
    "failed": 2,
    "start_ram_mb": 52.5,
    "peak_ram_mb": 520.3,       ← Should be <700MB
    "memory_increase_mb": 467.8 ← Should be <650MB
  }
}
```

**Success criteria:**
- ✅ successful >= 24 (80% success rate)
- ✅ peak_ram_mb < 700
- ✅ memory_increase_mb < 650

---

## 🧬 Step 6: Verify Lazy-Loading Logs

Check backend logs for "[Lazy-Load]" messages:

```powershell
# If backend outputs to console, you should see:
# [Lazy-Load] Loading Reasoner (FAISS + embeddings)...
# [Lazy-Load] Reasoner loaded in 18.50s

# These indicate models loading on-demand (not upfront)
```

---

## ⚠️ Troubleshooting

### Issue: Success rate still 0%
**Diagnosis:**
```powershell
# 1. Check if backend is running
curl http://localhost:8000/health

# 2. Check RAM usage - if >900MB, old process still running
tasklist | findstr python

# 3. Kill old processes and restart
taskkill /F /IM python.exe
rm .pid
powershell -File 'scripts/namo_start_backend.ps1'
```

### Issue: Response time not improving
**Diagnosis:**
- First request should be ~20s (model loading trigger)
- If ALL requests are 20s+, lazy-loading didn't apply
- Verify `orchestrator.py` changes were saved correctly
  ```powershell
  Select-String "@property" backend/namo_core/services/orchestrator.py
  # Should find 3 @property decorators
  ```

### Issue: RAM still > 900MB
**Diagnosis:**
- Multiple Python processes running old code
- Kill all: `taskkill /F /IM python.exe`
- Start fresh: `powershell -File 'scripts/namo_start_backend.ps1'`
- Wait 30 seconds before stress test

---

## ✅ Final Verification Checklist

After completing all steps:

- [ ] Lazy-loading code applied to orchestrator.py
- [ ] Backend starts instantly (no upfront model loading)
- [ ] `/health` responds <0.5s
- [ ] Stress test success rate ≥80%
- [ ] First request ~20-25s (model loading)
- [ ] Subsequent requests 1.5-4s (cached)
- [ ] RAM peak <700MB
- [ ] No connection errors
- [ ] Logs show "[Lazy-Load]" messages
- [ ] Report saved to `stress_test_report_v2.json`

---

## 🎯 Production Readiness

Once ALL checkboxes are checked:

✅ **System is production-ready for:**
- Watchdog deployment
- OneDrive + 403 fix deployment
- Cloudflare Tunnel deployment
- Live classroom usage

**Next phase:** Final deployment to production

---

## 📞 Quick Command Reference

```powershell
# Start fresh
rm .pid; powershell -File 'scripts/namo_start_backend.ps1'

# Test health
curl http://localhost:8000/health

# Run stress test V1 (standard)
powershell -File 'scripts/run_stress_test.ps1' -Workers 5 -Requests 30

# Run stress test V2 (with TTFB tracking)
python tests/test_orchestrator_stress_v2.py 5 30

# View results
type tests/stress_test_report_v2.json

# Monitor RAM during test (separate PowerShell)
while($true) { tasklist | findstr python; Start-Sleep -Seconds 5 }

# View watchdog logs
type logs/watchdog.log
```

---

**Expected Duration:** 5-10 minutes per test run

**Success Probability:** 95% (if lazy-loading applied correctly)

**Estimated time to production-ready:** 15-30 minutes (test + verification)

---

*Verification Guide v1.0 | 2026-04-21*
