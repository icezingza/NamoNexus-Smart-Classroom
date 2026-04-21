# =============================================================
# stop_tunnel.ps1 — หยุด Cloudflare Tunnel
# =============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir   = Split-Path -Parent $ScriptDir
$PidFile   = Join-Path $RootDir ".tunnel.pid"

if (Test-Path $PidFile) {
    $pid = Get-Content $PidFile -Raw
    try {
        Stop-Process -Id $pid -Force
        Write-Host "[OK] หยุด Tunnel (PID: $pid) แล้ว" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] ไม่พบ Process PID $pid (อาจหยุดไปแล้ว)" -ForegroundColor Yellow
    }
    Remove-Item $PidFile -Force
} else {
    Write-Host "[INFO] ไม่มี Tunnel กำลังทำงานอยู่" -ForegroundColor Gray
}

# ลบ log และ env.tunnel
Remove-Item (Join-Path $RootDir ".tunnel.log") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $RootDir ".env.tunnel") -Force -ErrorAction SilentlyContinue
Write-Host "[OK] ล้าง Tunnel files แล้ว" -ForegroundColor Green
