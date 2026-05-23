# 🎯 Watchdog Auto-Restart Test Plan
**วันที่:** 2026-04-21 | **สถานะ:** เตรียมทดสอบ

---

## 📋 What We Did
1. ✅ สร้าง Watchdog Script (`scripts/register_watchdog_startup.ps1`)
2. ✅ สร้าง Stress Test (`tests/test_orchestrator_stress.py`)
3. ✅ **Kill Backend Process (PID 9616)** ← Just executed
4. ⏳ **Waiting:** Monitor if Watchdog auto-restarts within 2 minutes

---

## 🔴 Current Status: Backend KILLED

```
PID: 9616
Status: TERMINATED (killed at 10:03:49)
RAM was: 949 MB (memory leak detected)
```

---

## ⏱️ Watchdog Test Timeline

| Time | Action | Expected |
|------|--------|----------|
| 10:03:49 | Backend killed manually | - |
| 10:04:00 | Watchdog checks PID (cycle 1) | Detects crash |
| 10:04:05 | Watchdog triggers restart | Backend starts |
| 10:05:49 | Watchdog checks PID (cycle 2) | Backend running ✅ |

**Watchdog Interval:** Every 2 minutes (configurable in Task Scheduler)

---

## 🛡️ How to Monitor

### 1. Check Watchdog Logs
```powershell
# Watch real-time logs (in separate PowerShell window):
Get-Content logs\watchdog.log -Wait
```

### 2. Check Backend Status
```powershell
# Is backend running?
netstat -ano | findstr ":8000"

# Is PID file present?
Get-Content .pid
```

### 3. Verify via HTTP
```powershell
# Test backend health:
curl http://localhost:8000/health
```

---

## 📊 Expected Watchdog Behavior

### ✅ Success Case
```
[2026-04-21 10:04:05] WARN Backend crashed! PID=9616 not found. Restarting...
[2026-04-21 10:04:06] OK Backend restart command issued
[2026-04-21 10:05:49] OK Backend running (PID=XXXX, RAM=52.3MB)
```

### ❌ Failure Case
```
[2026-04-21 10:04:05] WARN Backend crashed! PID=9616 not found. Restarting...
[2026-04-21 10:04:06] ERROR Failed to restart backend: <error>
[2026-04-21 10:05:49] WARN PID file not found
```

---

## 🔧 Manual Restart (if needed)
```powershell
# Start backend manually:
cd 'C:\Users\icezi\Downloads\Github repo\namo_core_project'
powershell -File 'scripts/namo_start_backend.ps1'
```

---

## 📌 Key Files

| File | Purpose |
|------|---------|
| `scripts/register_watchdog_startup.ps1` | Register watchdog in Task Scheduler |
| `scripts/namo_watchdog.ps1` | Watchdog monitor (auto-generated) |
| `scripts/namo_start_backend.ps1` | Backend launcher with PID tracking |
| `logs/watchdog.log` | Watchdog activity log |
| `.pid` | Current backend process ID |

---

## 🚀 Admin Registration (Needed)

**To fully activate watchdog in Task Scheduler:**
```powershell
# Run as Administrator:
powershell -ExecutionPolicy Bypass -File 'C:\Users\icezi\Downloads\Github repo\namo_core_project\scripts\register_watchdog_startup.ps1'
```

This registers:
- Task Name: "Namo Core Watchdog"
- Interval: Every 2 minutes
- Auto-restart: Yes

---

## 📌 Next Steps

1. Wait ~2-3 minutes to see if watchdog auto-restarts backend
2. Check logs: `type logs\watchdog.log`
3. Test endpoint: `curl http://localhost:8000/health`
4. Report results for OneDrive readiness decision

---

**Status:** ⏳ Waiting for Watchdog cycle...
