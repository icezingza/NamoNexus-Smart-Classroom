# =============================================================
# start_tunnel.ps1 — Phase 9: Named Cloudflare Tunnel (namo-core)
# URL คงที่: https://api.namonexus.com → localhost:8000
# =============================================================
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start_tunnel.ps1
# =============================================================

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir     = Split-Path -Parent $ScriptDir
$Cloudflared = Join-Path $ScriptDir "cloudflared.exe"
$PidFile     = Join-Path $RootDir ".tunnel.pid"
$LogFile     = Join-Path $RootDir ".tunnel.log"

# ── ตรวจสอบ cloudflared ──────────────────────────────────────
if (-not (Test-Path $Cloudflared)) {
    Write-Host "[ERROR] ไม่พบ cloudflared.exe ใน scripts/" -ForegroundColor Red
    exit 1
}

# ── ตรวจสอบ API server ──────────────────────────────────────
Write-Host "[INFO] ตรวจสอบ NRE API ที่ localhost:8000 ..." -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 5 -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Write-Host "[OK]   API พร้อมแล้ว" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] API ยังไม่พร้อม — กรุณารัน start_windows.ps1 ก่อน" -ForegroundColor Yellow
    $confirm = Read-Host "ต้องการเปิด Tunnel ต่อไหม? (y/N)"
    if ($confirm -ne "y") { exit 1 }
}

# ── เปิด Named Tunnel ───────────────────────────────────────
Write-Host "[INFO] กำลังเปิด Named Tunnel: namo-core ..." -ForegroundColor Cyan

$proc = Start-Process -FilePath $Cloudflared `
    -ArgumentList "tunnel run namo-core" `
    -RedirectStandardError $LogFile `
    -PassThru -WindowStyle Hidden

$proc.Id | Out-File $PidFile -Encoding ascii

# ── รอให้เชื่อมต่อ ───────────────────────────────────────────
Write-Host "[INFO] รอการเชื่อมต่อ ..." -ForegroundColor Cyan
$connected = $false
$timeout = 15
$elapsed = 0

while ($elapsed -lt $timeout) {
    Start-Sleep -Seconds 1
    $elapsed++
    if (Test-Path $LogFile) {
        $content = Get-Content $LogFile -Raw -ErrorAction SilentlyContinue
        if ($content -match "Registered tunnel connection") {
            $connected = $true
            break
        }
    }
}

if ($connected) {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  Named Tunnel พร้อมใช้งาน!                       ║" -ForegroundColor Green
    Write-Host "║                                                  ║" -ForegroundColor Green
    Write-Host "║  Public URL: https://api.namonexus.com           ║" -ForegroundColor Yellow
    Write-Host "║  WebSocket:  wss://api.namonexus.com/ws          ║" -ForegroundColor Cyan
    Write-Host "║                                                  ║" -ForegroundColor Green
    Write-Host "║  URL นี้คงที่ — ไม่เปลี่ยนทุกครั้งที่รัน        ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    # บันทึก URL คงที่
    "TUNNEL_URL=https://api.namonexus.com" | Out-File (Join-Path $RootDir ".env.tunnel") -Encoding ascii
    Write-Host "[OK] บันทึก URL ไปที่ .env.tunnel แล้ว" -ForegroundColor Green
} else {
    Write-Host "[ERROR] ไม่สามารถเชื่อมต่อได้ใน $timeout วินาที" -ForegroundColor Red
    Write-Host "        ตรวจสอบ log: $LogFile" -ForegroundColor Yellow
}
