$CONN_NAME  = "namo-classroom:asia-southeast1:namo-classroom-db"
$PROXY_URL  = "https://github.com/GoogleCloudPlatform/cloud-sql-proxy/releases/download/v2.13.0/cloud-sql-proxy.windows.amd64.exe"
$PROXY_EXE  = "$env:TEMP\cloud-sql-proxy.exe"
$BACKEND    = "C:\Users\icezi\NamoNexus-Smart-Classroom\backend\namo_core"
$PYTHONPATH = "C:\Users\icezi\NamoNexus-Smart-Classroom\backend"

# Step 1: Set PYTHONPATH so alembic can find namo_core
$env:PYTHONPATH = $PYTHONPATH
Write-Host "Step 1: PYTHONPATH = $env:PYTHONPATH" -ForegroundColor Cyan

# Step 2: Install deps
Write-Host "Step 2: Installing alembic + psycopg2..." -ForegroundColor Cyan
pip install alembic psycopg2-binary pydantic-settings python-dotenv --quiet

# Step 3: Download proxy using curl.exe (built-in Windows 10+)
if (-Not (Test-Path $PROXY_EXE)) {
    Write-Host "Step 3: Downloading Cloud SQL Auth Proxy via curl..." -ForegroundColor Cyan
    curl.exe -L -o $PROXY_EXE $PROXY_URL
    Write-Host "Download OK" -ForegroundColor Green
} else {
    Write-Host "Step 3: Proxy cached" -ForegroundColor Green
}

# Step 4: Start proxy
Write-Host "Step 4: Starting proxy on 127.0.0.1:5432..." -ForegroundColor Cyan
$proxy = Start-Process -FilePath $PROXY_EXE -ArgumentList "$CONN_NAME --port=5432" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5
Write-Host "Proxy PID: $($proxy.Id)" -ForegroundColor Yellow

# Step 5: Run alembic
Write-Host "Step 5: Running alembic upgrade head..." -ForegroundColor Cyan
Set-Location $BACKEND
python -m alembic upgrade head
$exit_code = $LASTEXITCODE

# Step 6: Stop proxy
if ($proxy -and $proxy.Id) {
    Stop-Process -Id $proxy.Id -Force -ErrorAction SilentlyContinue
}

if ($exit_code -eq 0) {
    Write-Host "=== Migration complete! ===" -ForegroundColor Green
} else {
    Write-Host "=== Migration FAILED (exit code: $exit_code) ===" -ForegroundColor Red
}
