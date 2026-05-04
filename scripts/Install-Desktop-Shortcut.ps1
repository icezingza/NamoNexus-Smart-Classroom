# ============================================================
# NamoNexus -- Install Desktop Shortcut
#
# Creates (or replaces) a Desktop .lnk file that:
#   - Launches Run_NamoNexus.bat with a hidden console
#   - Uses the NamoNexus purple-lightning icon
#   - Runs from the project root directory
#
# Usage (run once, no Admin required):
#   powershell -ExecutionPolicy Bypass -File .\scripts\Install-Desktop-Shortcut.ps1
# ============================================================

$ErrorActionPreference = "Stop"

$Root       = Split-Path -Parent $PSScriptRoot
$BatFile    = Join-Path $Root    "scripts\Run_NamoNexus.bat"
$IconFile   = Join-Path $Root    "scripts\namo_icon.ico"
$VenvPython = Join-Path $Root    ".venv\Scripts\python.exe"
$GenIcon    = Join-Path $Root    "scripts\generate_namo_icon.py"
$Desktop    = [System.Environment]::GetFolderPath("Desktop")
$Shortcut   = Join-Path $Desktop "NamoNexus.lnk"

Write-Host ""
Write-Host "  NamoNexus -- Desktop Shortcut Installer" -ForegroundColor Cyan
Write-Host ""

# ---- Ensure ICO exists -------------------------------------------------------
if (-not (Test-Path $IconFile)) {
    Write-Host "  [Icon] Generating namo_icon.ico..." -ForegroundColor Yellow
    & $VenvPython $GenIcon
    if (-not (Test-Path $IconFile)) {
        Write-Host "  [WARN] Icon generation failed -- using default icon." -ForegroundColor Yellow
        $IconFile = ""
    }
}

# ---- Create the .lnk via WScript.Shell ---------------------------------------
$Shell = New-Object -ComObject WScript.Shell
$Link  = $Shell.CreateShortcut($Shortcut)

$Link.TargetPath       = "cmd.exe"
# /c closes the cmd window after the bat finishes; /min minimises the launcher flash
$Link.Arguments        = "/min /c `"$BatFile`""
$Link.WorkingDirectory = $Root
$Link.WindowStyle      = 7   # 7 = minimised (so the console briefly flashes then hides)
$Link.Description      = "NamoNexus Smart Classroom -- One-Click Start"

if ($IconFile -and (Test-Path $IconFile)) {
    $Link.IconLocation = "$IconFile,0"
} else {
    # Fallback: use a system icon (magnifying glass / blue circle)
    $Link.IconLocation = "shell32.dll,13"
}

$Link.Save()

Write-Host "  [OK]  Shortcut created: $Shortcut" -ForegroundColor Green
Write-Host "        Target : $BatFile"            -ForegroundColor Gray
Write-Host "        Icon   : $($Link.IconLocation)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Double-click NamoNexus on your Desktop to start the classroom." -ForegroundColor White
Write-Host ""
