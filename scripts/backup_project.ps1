# =============================================================================
# Namo Core — Project Backup Script
# Phase 8: Updated to include Phase 5-7 files
#
# Creates a zip archive of all source code, excluding build artifacts,
# virtual environments, and local data files.
#
# Run from the project root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\backup_project.ps1
#
# Options:
#   -OutputDir "backups"   Directory to store zip (default: backups/)
#   -Label "pre-demo"      Optional label appended to filename
# =============================================================================

param(
    [string]$OutputDir = "backups",
    [string]$Label = ""
)

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$root = Split-Path -Parent $PSScriptRoot
$targetDir = Join-Path $root $OutputDir
$labelPart = if ($Label) { "_$Label" } else { "" }
$archivePath = Join-Path $targetDir "namo_core_project_${timestamp}${labelPart}.zip"
$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) "namo_core_project_backup_$timestamp"

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

# ---------------------------------------------------------------------------
# Files and directories to include in backup
# Phase 8: Added .env.example, CLAUDE.md, DEVELOPMENT_ANALYSIS.md
# ---------------------------------------------------------------------------
$items = @(
    # Root config
    (Join-Path $root ".gitignore"),
    (Join-Path $root ".env.example"),
    (Join-Path $root "CLAUDE.md"),
    (Join-Path $root "README.md"),
    (Join-Path $root "RECOVERY_NOTES.md"),
    (Join-Path $root "DEVELOPMENT_ANALYSIS.md"),

    # Frontend
    (Join-Path $root "dashboard\src"),
    (Join-Path $root "dashboard\index.html"),
    (Join-Path $root "dashboard\package.json"),
    (Join-Path $root "dashboard\package-lock.json"),
    (Join-Path $root "dashboard\vite.config.js"),

    # Backend (includes all phases)
    (Join-Path $root "namo_core"),

    # Docs & scripts
    (Join-Path $root "roadmap"),
    (Join-Path $root "scripts")
)

$existingItems = $items | Where-Object { Test-Path $_ }

Write-Host "Backing up $($existingItems.Count) items..." -ForegroundColor Cyan

foreach ($item in $existingItems) {
    $leaf = Split-Path $item -Leaf
    Copy-Item -Path $item -Destination (Join-Path $stagingRoot $leaf) -Recurse -Force
}

# ---------------------------------------------------------------------------
# Remove build artifacts and local-only directories
# ---------------------------------------------------------------------------
$cleanupDirs = @(
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    ".venv",
    "logs",
    "backups",
    "faiss_index"
)

foreach ($name in $cleanupDirs) {
    Get-ChildItem -Path $stagingRoot -Recurse -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq $name } |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
}

# Remove .pyc files
Get-ChildItem -Path $stagingRoot -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue |
    Remove-Item -Force

# ---------------------------------------------------------------------------
# Compress and clean up staging
# ---------------------------------------------------------------------------
Compress-Archive -Path (Join-Path $stagingRoot "*") -DestinationPath $archivePath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stagingRoot

$sizeKB = [math]::Round((Get-Item $archivePath).Length / 1KB)
Write-Host "Backup created: $archivePath ($sizeKB KB)" -ForegroundColor Green
