@echo off
title NamoNexus Firewall Repair
echo ------------------------------------------
echo    NAMO NEXUS - FIREWALL REPAIR TOOL
echo ------------------------------------------
echo.
echo Asking for Administrator privileges...
echo.

:: Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Admin rights detected. Opening ports...
    netsh advfirewall firewall add rule name="NamoNexus Dashboard" dir=in action=allow protocol=TCP localport=5173
    netsh advfirewall firewall add rule name="NamoNexus API" dir=in action=allow protocol=TCP localport=8000
    echo.
    echo ------------------------------------------
    echo SUCCESS! Ports 5173 and 8000 are now OPEN.
    echo Your Tablet should now be able to connect.
    echo ------------------------------------------
) else (
    echo [ERROR] PLEASE RIGHT-CLICK THIS FILE AND CHOOSE:
    echo         "RUN AS ADMINISTRATOR"
    echo.
)
echo.
pause
